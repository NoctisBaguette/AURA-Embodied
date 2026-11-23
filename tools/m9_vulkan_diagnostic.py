"""Read-only Vulkan inventory; never imports or constructs the simulator."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ENVIRONMENT_KEYS = (
    "CONDA_DEFAULT_ENV", "CONDA_PREFIX", "LD_LIBRARY_PATH", "LD_PRELOAD",
    "CUDA_VISIBLE_DEVICES", "VK_ICD_FILENAMES", "VK_DRIVER_FILES",
    "VK_ADD_DRIVER_FILES", "VK_LOADER_DRIVERS_SELECT", "VK_LOADER_DRIVERS_DISABLE",
    "VK_LAYER_PATH", "VK_ADD_LAYER_PATH", "VK_LOADER_DEBUG", "DISPLAY",
    "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_DATA_DIRS",
)


def command(arguments, timeout=15):
    executable = shutil.which(arguments[0])
    if executable is None:
        return {"command": arguments, "state": "not_installed"}
    try:
        result = subprocess.run([executable, *arguments[1:]], capture_output=True,
                                text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"command": arguments, "state": "timeout", "timeout_s": timeout}
    except OSError as error:
        return {"command": arguments, "state": "error", "error": str(error)}
    return {"command": arguments, "state": "completed", "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def read_file(path):
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        return {"path": str(path), "state": "unreadable", "error": str(error)}
    return {"path": str(path), "state": "read", "sha256": hashlib.sha256(raw).hexdigest(),
            "text": raw.decode("utf-8", errors="replace")}


def manifest_files(environment, home, prefix):
    directories = [Path("/etc/vulkan/icd.d"), Path("/usr/share/vulkan/icd.d"),
                   Path("/usr/local/share/vulkan/icd.d"),
                   Path(environment.get("XDG_CONFIG_HOME") or home / ".config") / "vulkan/icd.d",
                   Path(environment.get("XDG_DATA_HOME") or home / ".local/share") / "vulkan/icd.d",
                   prefix / "share/vulkan/icd.d"]
    for directory in (environment.get("XDG_DATA_DIRS") or "").split(os.pathsep):
        if directory:
            directories.append(Path(directory) / "vulkan/icd.d")
    found = set()
    for directory in directories:
        try:
            found.update(directory.glob("*.json"))
        except OSError:
            pass
    for key in ("VK_DRIVER_FILES", "VK_ICD_FILENAMES", "VK_ADD_DRIVER_FILES"):
        for value in (environment.get(key) or "").split(os.pathsep):
            if not value:
                continue
            path = Path(value)
            if path.is_dir():
                found.update(path.glob("*.json"))
            else:
                found.add(path)
    return sorted(found, key=str)


def inspect():
    environment = {key: os.environ.get(key) for key in ENVIRONMENT_KEYS}
    report = {"schema": "m9_vulkan_inventory_v1",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "inventory_only_no_simulator_import_reset_action_or_driver_change",
              "python": sys.version, "executable": sys.executable, "environment": environment,
              "packages": {}, "manifests": [], "loader_files": []}
    for name in ("sapien", "mani_skill", "gymnasium", "torch", "numpy"):
        try:
            report["packages"][name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            report["packages"][name] = None
    report["nvidia_smi"] = command(["nvidia-smi", "--query-gpu=index,name,driver_version",
                                    "--format=csv,noheader"])
    report["kernel_driver"] = read_file("/proc/driver/nvidia/version")
    cache = command(["ldconfig", "-p"])
    if cache.get("state") == "completed":
        cache["stdout"] = "\n".join(line for line in cache["stdout"].splitlines()
            if any(token in line.lower() for token in ("vulkan", "glx_nvidia", "glvkspirv")))
    report["library_cache"] = cache
    for path in manifest_files(os.environ, Path.home(), Path(sys.prefix)):
        entry = read_file(path)
        if entry["state"] == "read":
            try:
                parsed = json.loads(entry["text"])
                icd = parsed.get("ICD", {}) if isinstance(parsed, dict) else {}
                library = icd.get("library_path") if isinstance(icd, dict) else None
                entry["library_path"] = library
                if isinstance(library, str) and ("/" in library or "\\" in library):
                    candidate = Path(library)
                    if not candidate.is_absolute():
                        candidate = path.parent / candidate
                    entry["explicit_library_exists"] = candidate.is_file()
            except (ValueError, TypeError) as error:
                entry["parse_error"] = str(error)
        report["manifests"].append(entry)
    try:
        package = Path(metadata.distribution("sapien").locate_file("sapien"))
        report["sapien_vulkan_tricks"] = read_file(package / "_vulkan_tricks.py")
        loader_paths = sorted(package.rglob("*vulkan*.so*"), key=str)
    except (metadata.PackageNotFoundError, OSError) as error:
        report["sapien_source_error"] = str(error)
        loader_paths = []
    for path in loader_paths:
        if path.is_file():
            report["loader_files"].append({"path": str(path),
                "dynamic_dependencies": command(["readelf", "-d", str(path)])})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Retain existing diagnostic; use a new output path: " + str(args.output))
    report = inspect()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    print(encoded, end="")
    print("Diagnostic:", args.output)
    print("SHA-256:", hashlib.sha256(encoded.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
