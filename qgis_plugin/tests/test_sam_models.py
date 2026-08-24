import hashlib
import io
import sys
import types

import pytest

from geoai.core import sam_models


def _model_for(payload: bytes) -> sam_models.PublicModel:
    return sam_models.PublicModel(
        model_id="test/public-model",
        revision="abc123",
        filename="model.safetensors",
        url="https://models.example/model.safetensors",
        size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        license_url="https://models.example/license",
    )


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_public_model_download_needs_no_auth_and_verifies_hash(tmp_path, monkeypatch):
    payload = b"safe public checkpoint"
    model = _model_for(payload)
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return _Response(payload)

    monkeypatch.setattr(sam_models, "urlopen", fake_urlopen)
    target = tmp_path / model.filename

    result = sam_models.download_public_model(target, model=model)

    assert result == target
    assert target.read_bytes() == payload
    assert requests[0][0].get_header("Authorization") is None
    assert not target.with_name(target.name + ".part").exists()
    assert sam_models.validate_checkpoint(target, model, verify_hash=True)[0] is True


def test_public_model_download_rejects_invalid_existing_file(tmp_path):
    payload = b"expected"
    model = _model_for(payload)
    target = tmp_path / model.filename
    target.write_bytes(b"wrong")

    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        sam_models.download_public_model(target, model=model)


def test_default_checkpoint_can_be_preprovisioned(monkeypatch, tmp_path):
    checkpoint = tmp_path / "approved" / "sam31.safetensors"
    monkeypatch.setenv("GEOAI_SAM31_CHECKPOINT", str(checkpoint))

    assert sam_models.default_sam31_checkpoint_path() == checkpoint


def test_safetensors_loader_maps_detector_and_tracker_keys(monkeypatch, tmp_path):
    checkpoint = tmp_path / "model.safetensors"
    checkpoint.touch()
    state = {
        "detector.backbone.weight": "detector-value",
        "tracker.decoder.weight": "tracker-value",
    }

    safetensors_module = types.ModuleType("safetensors")
    safetensors_module.__path__ = []
    safetensors_torch = types.ModuleType("safetensors.torch")
    safetensors_torch.load_file = lambda _path, device: state
    safetensors_module.torch = safetensors_torch

    model_builder = types.ModuleType("sam3.model_builder")
    model_builder._load_checkpoint = lambda _model, _path: None
    sam3_module = types.ModuleType("sam3")
    sam3_module.__path__ = []
    sam3_module.model_builder = model_builder

    monkeypatch.setitem(sys.modules, "safetensors", safetensors_module)
    monkeypatch.setitem(sys.modules, "safetensors.torch", safetensors_torch)
    monkeypatch.setitem(sys.modules, "sam3", sam3_module)
    monkeypatch.setitem(sys.modules, "sam3.model_builder", model_builder)

    loaded = {}

    class FakeModel:
        inst_interactive_predictor = object()

        def load_state_dict(self, values, strict):
            loaded.update(values)
            assert strict is False

    sam_models.enable_safetensors_checkpoint(checkpoint)
    model_builder._load_checkpoint(FakeModel(), checkpoint)

    assert loaded == {
        "backbone.weight": "detector-value",
        "inst_interactive_predictor.model.decoder.weight": "tracker-value",
    }
