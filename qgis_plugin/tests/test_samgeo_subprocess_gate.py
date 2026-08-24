"""Tests for keeping the managed venv's SamGeo out of the QGIS process.

QGIS imports its own NumPy at startup, so the venv's NumPy-2-era SciPy/scikit
stack breaks when imported in-process (issues #688 and #854). These cover the
gate that routes model loading into the venv subprocess instead.
"""

import sys
import types
from pathlib import Path

from geoai.dialogs import samgeo
from geoai.workers import samgeo_worker


def test_use_subprocess_on_windows_without_venv(monkeypatch):
    """Windows needs the subprocess for the PyTorch DLL conflict regardless."""
    monkeypatch.setattr(samgeo.os, "name", "nt")

    assert samgeo._use_samgeo_subprocess() is True


def test_use_subprocess_on_posix_when_runtime_is_ready(monkeypatch):
    """Regression test for issue #854: macOS/Linux must not import in-process."""
    from geoai.core import venv_manager

    monkeypatch.setattr(samgeo.os, "name", "posix")
    monkeypatch.setattr(
        venv_manager, "runtime_is_ready", lambda _venv_dir=None: True
    )

    assert samgeo._use_samgeo_subprocess() is True


def test_in_process_on_posix_without_ready_runtime(monkeypatch):
    """No ready managed runtime means no version skew, so keep in-process."""
    from geoai.core import venv_manager

    monkeypatch.setattr(samgeo.os, "name", "posix")
    monkeypatch.setattr(
        venv_manager, "runtime_is_ready", lambda _venv_dir=None: False
    )

    assert samgeo._use_samgeo_subprocess() is False


def _fake_torch(mps_available=False, cuda_available=False):
    torch = types.ModuleType("torch")
    backends = types.ModuleType("torch.backends")
    mps = types.ModuleType("torch.backends.mps")
    mps.is_available = lambda: mps_available
    backends.mps = mps
    torch.backends = backends
    cuda = types.SimpleNamespace(is_available=lambda: cuda_available)
    torch.cuda = cuda
    return torch


def _install_torch(monkeypatch, torch):
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "torch.backends", torch.backends)


def test_resolve_device_prefers_mps(monkeypatch):
    """The dialog used to pick MPS in auto mode; the worker must keep doing so."""
    _install_torch(monkeypatch, _fake_torch(mps_available=True, cuda_available=True))

    assert samgeo_worker._resolve_device("auto") == "mps"
    assert samgeo_worker._resolve_device(None) == "mps"


def test_resolve_device_falls_back_to_cuda(monkeypatch):
    _install_torch(monkeypatch, _fake_torch(mps_available=False, cuda_available=True))

    assert samgeo_worker._resolve_device("auto") == "cuda"


def test_resolve_device_falls_back_to_cpu(monkeypatch):
    _install_torch(monkeypatch, _fake_torch(mps_available=False, cuda_available=False))

    assert samgeo_worker._resolve_device("auto") == "cpu"


def test_resolve_device_respects_explicit_choice(monkeypatch):
    _install_torch(monkeypatch, _fake_torch(mps_available=True, cuda_available=True))

    assert samgeo_worker._resolve_device("cpu") == "cpu"
    assert samgeo_worker._resolve_device("cuda") == "cuda"


def test_resolve_device_survives_broken_torch(monkeypatch):
    """Detection must not turn an import problem into a device crash."""
    torch = _fake_torch()

    def boom():
        raise RuntimeError("mps probe failed")

    torch.backends.mps.is_available = boom
    torch.cuda.is_available = boom
    _install_torch(monkeypatch, torch)

    assert samgeo_worker._resolve_device("auto") == "cpu"


def test_worker_loads_public_sam31_from_local_checkpoint(monkeypatch, tmp_path):
    from geoai.core import sam_models

    checkpoint = tmp_path / "sam31.safetensors"
    checkpoint.touch()
    captured = {}

    class FakeSamGeo3:
        masks = []

        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_samgeo = types.ModuleType("samgeo")
    fake_samgeo.SamGeo3 = FakeSamGeo3
    monkeypatch.setitem(sys.modules, "samgeo", fake_samgeo)
    monkeypatch.setattr(samgeo_worker, "_ensure_pkg_resources_shim", lambda: False)
    monkeypatch.setattr(samgeo_worker, "_resolve_device", lambda _device: "cpu")

    def load_helper(_module_name, relative_path):
        assert relative_path == str(Path("core") / "sam_models.py")
        return sam_models

    monkeypatch.setattr(samgeo_worker, "_load_plugin_helper", load_helper)
    monkeypatch.setattr(sam_models, "enable_safetensors_checkpoint", lambda _path: None)

    result = samgeo_worker._handle_init(
        {
            "model_version": "SamGeo3.1 (public checkpoint, no login)",
            "backend": "meta",
            "device": "cpu",
            "confidence": 0.5,
            "enable_interactive": True,
            "model_id": "facebook/sam3.1",
            "checkpoint_path": str(checkpoint),
        }
    )

    assert captured["model_id"] == "facebook/sam3.1"
    assert captured["checkpoint_path"] == str(checkpoint)
    assert captured["load_from_HF"] is False
    assert result["model_name"] == "SamGeo3.1 (public checkpoint)"
    samgeo_worker._cleanup()


def test_worker_plugin_helpers_preserve_external_geoai(monkeypatch):
    external_geoai = types.ModuleType("geoai")
    external_geoai.origin = "managed-site-packages"
    monkeypatch.setitem(sys.modules, "geoai", external_geoai)
    monkeypatch.delitem(
        sys.modules, "_geoai_worker_pkg_resources_compat", raising=False
    )
    monkeypatch.delitem(sys.modules, "_geoai_worker_sam_models", raising=False)

    compat = samgeo_worker._load_plugin_helper(
        "_geoai_worker_pkg_resources_compat", "_pkg_resources_compat.py"
    )
    sam_models = samgeo_worker._load_plugin_helper(
        "_geoai_worker_sam_models", str(Path("core") / "sam_models.py")
    )

    assert compat.__file__.endswith("_pkg_resources_compat.py")
    assert sam_models.__file__.endswith(str(Path("core") / "sam_models.py"))
    assert sys.modules["geoai"] is external_geoai
    assert external_geoai.origin == "managed-site-packages"
