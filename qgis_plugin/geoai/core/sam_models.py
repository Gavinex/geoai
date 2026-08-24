"""Public, authentication-free SAM model support for the QGIS plugin.

The corporate build deliberately avoids Hugging Face login state.  Model files
are either provisioned by IT or downloaded from a pinned public repository.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PublicModel:
    """Immutable metadata for a publicly downloadable checkpoint."""

    model_id: str
    revision: str
    filename: str
    url: str
    size: int
    sha256: str
    license_url: str


PUBLIC_SAM31 = PublicModel(
    model_id="Comfy-Org/sam3.1",
    revision="f38cd62b71494b53ac2b56ca36e24f3c8d565581",
    filename="sam3.1_multiplex_fp16.safetensors",
    url=(
        "https://huggingface.co/Comfy-Org/sam3.1/resolve/"
        "f38cd62b71494b53ac2b56ca36e24f3c8d565581/"
        "checkpoints/sam3.1_multiplex_fp16.safetensors"
    ),
    size=1_745_546_848,
    sha256="9ba99c92703c2e8b4f47de2d34a539bb8e18923049e238b780d70dbe6368eb03",
    license_url="https://huggingface.co/Comfy-Org/sam3.1/blob/main/LICENSE",
)


def model_cache_dir() -> Path:
    """Return the model cache without relying on Hugging Face credentials."""

    configured = os.environ.get("GEOAI_MODEL_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    cache_root = os.environ.get("GEOAI_CACHE_DIR", "").strip()
    if cache_root:
        return Path(cache_root).expanduser().resolve() / "models"
    return Path.home() / ".qgis_geoai" / "models"


def default_sam31_checkpoint_path() -> Path:
    """Return the default local location for the public SAM 3.1 checkpoint."""

    configured = os.environ.get("GEOAI_SAM31_CHECKPOINT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return model_cache_dir() / PUBLIC_SAM31.filename


def validate_checkpoint(
    path: os.PathLike | str,
    model: PublicModel = PUBLIC_SAM31,
    verify_hash: bool = False,
) -> Tuple[bool, str]:
    """Validate checkpoint presence, size, and optionally its SHA-256 digest."""

    checkpoint = Path(path).expanduser()
    if not checkpoint.is_file():
        return False, f"Checkpoint not found: {checkpoint}"
    size = checkpoint.stat().st_size
    if size != model.size:
        return False, f"Checkpoint size is {size} bytes; expected {model.size}"
    if verify_hash:
        digest = hashlib.sha256()
        with checkpoint.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != model.sha256.lower():
            return False, "Checkpoint SHA-256 does not match the pinned model"
    return True, "Checkpoint is ready"


def download_public_model(
    destination: os.PathLike | str,
    model: PublicModel = PUBLIC_SAM31,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Path:
    """Stream a public model to disk, verify it, and atomically publish it.

    No token, cookie, Git client, Conda executable, or Hugging Face CLI is used.
    A ``.part`` file is never treated as a valid model.
    """

    target = Path(destination).expanduser().resolve()
    ready, _ = validate_checkpoint(target, model=model, verify_hash=False)
    if ready:
        return target
    if target.exists():
        raise RuntimeError(
            f"Refusing to overwrite an invalid checkpoint: {target}. "
            "Remove or relocate it, then retry."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    if partial.exists():
        partial.unlink()

    if urlsplit(model.url).scheme.lower() != "https":
        raise RuntimeError("Public model URL must use HTTPS")
    request = Request(
        model.url,
        headers={"User-Agent": "GeoAI-QGIS-Corporate/1.0"},
    )
    digest = hashlib.sha256()
    received = 0
    try:
        # The URL scheme is validated immediately before Request construction.
        with (
            urlopen(request, timeout=120) as response,  # nosec B310
            partial.open("wb") as stream,
        ):
            while True:
                if cancel_check and cancel_check():
                    raise InterruptedError("Model download cancelled")
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if progress_callback:
                    percent = min(int(received * 100 / model.size), 99)
                    progress_callback(
                        percent,
                        "Downloading SAM 3.1: {:.1f} / {:.1f} MiB".format(
                            received / 1024 / 1024,
                            model.size / 1024 / 1024,
                        ),
                    )

        if received != model.size:
            raise RuntimeError(
                f"Downloaded {received} bytes; expected {model.size} bytes"
            )
        if digest.hexdigest().lower() != model.sha256.lower():
            raise RuntimeError("Downloaded checkpoint failed SHA-256 verification")
        os.replace(partial, target)
        if progress_callback:
            progress_callback(100, "SAM 3.1 checkpoint downloaded and verified")
        return target
    except Exception:
        try:
            partial.unlink()
        except OSError:
            pass
        raise


def enable_safetensors_checkpoint(checkpoint_path: os.PathLike | str) -> None:
    """Teach Meta's SAM loader to read the public safetensors checkpoint.

    Meta's image builder currently calls ``torch.load`` even when the state
    dictionary is stored in safetensors format.  The public Comfy-Org file uses
    the same detector/tracker key layout, so only the serialization reader
    needs adapting; model code and inference remain Meta SAM.
    """

    checkpoint = Path(checkpoint_path)
    if checkpoint.suffix.lower() != ".safetensors":
        return

    from safetensors.torch import load_file
    import sam3.model_builder as model_builder

    original_loader = getattr(model_builder, "_geoai_original_load_checkpoint", None)
    if original_loader is None:
        original_loader = model_builder._load_checkpoint
        model_builder._geoai_original_load_checkpoint = original_loader

    def _load_checkpoint(model, path):
        if Path(path).suffix.lower() != ".safetensors":
            return original_loader(model, path)

        checkpoint_state = load_file(str(path), device="cpu")
        image_state = {
            key.replace("detector.", ""): value
            for key, value in checkpoint_state.items()
            if "detector" in key
        }
        if getattr(model, "inst_interactive_predictor", None) is not None:
            image_state.update(
                {
                    key.replace("tracker.", "inst_interactive_predictor.model."): value
                    for key, value in checkpoint_state.items()
                    if "tracker" in key
                }
            )
        if not image_state:
            raise RuntimeError(
                "The selected safetensors file contains no SAM detector weights"
            )
        model.load_state_dict(image_state, strict=False)

    model_builder._load_checkpoint = _load_checkpoint
