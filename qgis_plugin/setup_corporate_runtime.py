#!/usr/bin/env python3
"""Create the GeoAI runtime using only an approved Python and standard pip.

This script intentionally contains no Conda, uv, PowerShell, Git, executable
download, or Hugging Face authentication path.  IT can point it at an internal
package index or a fully offline wheelhouse.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def _site_packages(runtime_dir: Path) -> Path:
    return runtime_dir / "site-packages"


def _run(
    command: list[str], dry_run: bool = False, env: dict[str, str] | None = None
) -> None:
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    if not dry_run:
        subprocess.check_call(command, env=env)


def _validate_python(python_path: Path) -> tuple[int, int]:
    if not python_path.is_file():
        raise RuntimeError(f"Python executable not found: {python_path}")
    output = subprocess.check_output(
        [
            str(python_path),
            "-c",
            "import sys; print(sys.version_info.major, sys.version_info.minor)",
        ],
        text=True,
    ).strip()
    major, minor = (int(part) for part in output.split())
    if (major, minor) < (3, 12):
        raise RuntimeError(
            f"GeoAI requires Python 3.12 or newer; selected Python is {major}.{minor}"
        )
    return major, minor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="IT-approved Python executable matching QGIS's major/minor version",
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        help="Destination runtime directory (defaults to ~/.qgis_geoai/venv_pyX.Y)",
    )
    parser.add_argument(
        "--wheelhouse",
        type=Path,
        help="Offline directory containing all required wheels",
    )
    parser.add_argument("--index-url", help="Approved Python package index")
    parser.add_argument(
        "--extra-index-url",
        help="Optional approved secondary index, such as an internal PyTorch mirror",
    )
    parser.add_argument("--cert", type=Path, help="Corporate CA bundle for pip")
    parser.add_argument(
        "--trusted-host",
        action="append",
        default=[],
        help="Explicit IT-approved host that may bypass TLS validation",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing them"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    python_path = args.python.expanduser().resolve()
    requirements = (
        Path(__file__).parent / "geoai" / "runtime" / "requirements-corporate.txt"
    )

    if args.wheelhouse and (args.index_url or args.extra_index_url):
        raise RuntimeError("Use either --wheelhouse or package index options, not both")
    if args.wheelhouse and not args.wheelhouse.expanduser().is_dir():
        raise RuntimeError(f"Wheelhouse does not exist: {args.wheelhouse}")
    if args.cert and not args.cert.expanduser().is_file():
        raise RuntimeError(f"CA bundle does not exist: {args.cert}")

    major, minor = _validate_python(python_path)
    runtime_dir = (
        (args.runtime_dir or Path.home() / ".qgis_geoai" / f"venv_py{major}.{minor}")
        .expanduser()
        .resolve()
    )
    print(f"Approved Python: {python_path} ({major}.{minor})")
    print(f"Runtime: {runtime_dir}")

    package_root = _site_packages(runtime_dir)
    package_root.mkdir(parents=True, exist_ok=True)
    runtime_environment = os.environ.copy()
    runtime_environment["PYTHONPATH"] = str(package_root)
    runtime_environment["GEOAI_RUNTIME_SITE_PACKAGES"] = str(package_root)
    if os.name == "nt":
        native_paths = [package_root / "torch" / "lib", package_root / "torch" / "bin"]
        existing_path = runtime_environment.get("PATH", "")
        runtime_environment["PATH"] = os.pathsep.join(
            [*(str(path) for path in native_paths), existing_path]
        )

    command = [
        str(python_path),
        "-m",
        "pip",
        "install",
        "--target",
        str(package_root),
        "--upgrade",
        "--disable-pip-version-check",
        "--prefer-binary",
        "--requirement",
        str(requirements),
    ]
    if args.wheelhouse:
        command.extend(
            ["--no-index", "--find-links", str(args.wheelhouse.expanduser().resolve())]
        )
    if args.index_url:
        command.extend(["--index-url", args.index_url])
    if args.extra_index_url:
        command.extend(["--extra-index-url", args.extra_index_url])
    if args.cert:
        command.extend(["--cert", str(args.cert.expanduser().resolve())])
    for host in args.trusted_host:
        command.extend(["--trusted-host", host])

    marker_path = runtime_dir / "geoai-runtime-ready.txt"
    if not args.dry_run:
        marker_path.unlink(missing_ok=True)
    _run(command, args.dry_run, env=runtime_environment)
    if not args.dry_run:
        _run(
            [
                str(python_path),
                "-c",
                (
                    "import torch, torchvision, geoai, samgeo, sam3, safetensors; "
                    "print('GeoAI runtime verified')"
                ),
            ],
            env=runtime_environment,
        )
        marker_path.write_text(
            "approved-python-package-directory\n", encoding="utf-8"
        )

    print("\nSet these variables before starting QGIS:")
    print(f"  GEOAI_RUNTIME_DIR={runtime_dir}")
    print(f"  GEOAI_PYTHON={python_path}")
    if args.wheelhouse:
        print(f"  GEOAI_WHEELHOUSE={args.wheelhouse.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
