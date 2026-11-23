#!/usr/bin/env bash
# Create the dedicated runtime; refuse to install into any existing environment.
set -euo pipefail

prototype_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
conda_base="$(conda info --base)"
source "$conda_base/etc/profile.d/conda.sh"

environments="$(conda env list --json)"
if printf '%s' "$environments" | "$conda_base/bin/python" -c '
import json, pathlib, sys
envs = json.load(sys.stdin)["envs"]
sys.exit(0 if any(pathlib.Path(p).name == "aether-cl" for p in envs) else 1)
'; then
    printf 'Environment aether-cl already exists. Inspect it before reusing it.\n' >&2
    exit 1
fi

conda create -n aether-cl python=3.10 pip -y
conda activate aether-cl
python -c 'import os, sys; assert os.environ.get("CONDA_DEFAULT_ENV") == "aether-cl"; assert sys.version_info[:2] == (3, 10)'
python -m pip install 'torch==2.4.1' --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r "$prototype_dir/requirements.txt"
python -m pip check
mkdir -p "$prototype_dir/runs"
python -m pip freeze > "$prototype_dir/runs/installed-packages.txt"
printf '\nAETHER environment installed. Run the environment smoke tests next.\n'
