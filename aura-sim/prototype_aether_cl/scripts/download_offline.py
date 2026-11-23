"""Download Linux CPython 3.10 wheels on a connected laptop; install nothing."""

import argparse
import email
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


TARGET_PLATFORMS = (
    "manylinux_2_35_x86_64", "manylinux_2_34_x86_64", "manylinux_2_31_x86_64",
    "manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64",
    "manylinux2010_x86_64", "manylinux1_x86_64", "linux_x86_64",
)


def compatible(tag):
    python, abi, platform = tag.split("-")
    if platform not in (*TARGET_PLATFORMS, "any"):
        return False
    if python == "cp310" and abi == "cp310":
        return True
    if abi == "abi3" and re.fullmatch(r"cp3\d+", python):
        return int(python[3:]) <= 10
    if abi == "none":
        return python in {"cp310", "py3", *(f"py3{i}" for i in range(11))}
    return False


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    pins = Path(__file__).resolve().parents[1] / "requirements-offline.txt"
    expected = {}
    for line in pins.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, version = line.split("==", 1)
            expected[normalized(name)] = version
    args.output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pip", "download", "--disable-pip-version-check",
               "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
               "--no-deps", "--python-version", "310", "--implementation", "cp",
               "--abi", "cp310", "--abi", "abi3", "--abi", "none"]
    for platform in TARGET_PLATFORMS:
        command.extend(["--platform", platform])
    command.extend(["--dest", str(args.output), "--requirement", str(pins)])
    subprocess.run(command, check=True)
    found = {}
    for wheel in sorted(args.output.glob("*.whl")):
        with zipfile.ZipFile(wheel) as package:
            metadata_path = next(n for n in package.namelist()
                                 if n.endswith(".dist-info/METADATA"))
            metadata = email.message_from_bytes(package.read(metadata_path))
            wheel_path = next(n for n in package.namelist()
                              if n.endswith(".dist-info/WHEEL"))
            wheel_metadata = email.message_from_bytes(package.read(wheel_path))
            if not any(compatible(tag) for tag in wheel_metadata.get_all("Tag", [])):
                continue
        name = normalized(metadata["Name"])
        if name in expected and metadata["Version"] == expected[name]:
            found[name] = wheel
    missing = sorted(set(expected) - set(found))
    if missing:
        raise RuntimeError(f"Downloaded wheel set is incomplete: {missing}")
    manifest = {wheel.name: hashlib.sha256(wheel.read_bytes()).hexdigest()
                for wheel in found.values()}
    manifest_path = args.output / "SHA256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.archive, "w") as archive:
        for wheel in found.values():
            archive.add(wheel, arcname=wheel.name)
        archive.add(manifest_path, arcname=manifest_path.name)
    print(f"Downloaded {len(found)} Linux/portable wheels; installed nothing.")
    print(f"Transfer archive: {args.archive.resolve()}")


if __name__ == "__main__":
    main()
