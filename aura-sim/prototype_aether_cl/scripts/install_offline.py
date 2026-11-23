"""Install verified wheels into the copied aether-cl environment, without a network."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("This wheel set targets Linux x86_64.")
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("Activate the Python 3.10 aether-cl environment first.")
    if Path(sys.prefix).name != "aether-cl" or os.environ.get("CONDA_DEFAULT_ENV") != "aether-cl":
        raise RuntimeError("Refusing to modify an environment other than aether-cl.")
    if metadata.version("torch") != "2.4.1+cu121" or metadata.version("numpy") != "1.26.4":
        raise RuntimeError("This incremental wheel set requires torch 2.4.1+cu121 and numpy 1.26.4.")
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((args.wheelhouse / "SHA256.json").read_text(encoding="utf-8"))
    if not manifest:
        raise RuntimeError("Empty wheel manifest.")
    for filename, expected in manifest.items():
        if Path(filename).name != filename or not filename.endswith(".whl"):
            raise RuntimeError(f"Invalid manifest filename: {filename}")
        wheel = args.wheelhouse / filename
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Transfer checksum mismatch: {filename}")
    actual = {p.name for p in args.wheelhouse.glob("*.whl")}
    if actual != set(manifest):
        raise RuntimeError("Wheel directory differs from its manifest; use a clean extraction directory.")
    pip = [sys.executable, "-m", "pip", "--disable-pip-version-check"]
    install = pip + ["install", "--no-index", "--only-binary=:all:",
                     "--find-links", str(args.wheelhouse.resolve()),
                     "--requirement", str(root / "requirements.txt"),
                     "--requirement", str(root / "requirements-offline.txt")]
    # Resolve on the actual Linux interpreter before removing the copied cv2 package.
    subprocess.run(install + ["--dry-run"], check=True)
    subprocess.run(pip + ["uninstall", "-y", "opencv-python-headless"], check=True)
    subprocess.run(install, check=True)
    subprocess.run(pip + ["check"], check=True)
    run_dir = root / "runs"
    run_dir.mkdir(exist_ok=True)
    with (run_dir / "installed-packages.txt").open("w", encoding="utf-8") as handle:
        subprocess.run(pip + ["freeze"], check=True, stdout=handle)
    print("Offline installation and pip check completed. Simulator acceptance is still pending.")


if __name__ == "__main__":
    main()
