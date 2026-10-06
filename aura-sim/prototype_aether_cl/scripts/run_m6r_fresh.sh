#!/usr/bin/env bash
# Start only after the returned known-seed commissioning archive is reviewed.
# All three sweep calls inherit one parent environment; SSH reconnect is irrelevant.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: bash scripts/run_m6r_fresh.sh EXPECTED_FROZEN_GIT_COMMIT" >&2
    exit 2
fi
test "$(git rev-parse HEAD)" = "$1"
test -z "$(git status --porcelain)"

m6r_output="runs/m6r-placement-seeds120-139"
m6r_archive="/home/jiangle/aura-work/aether-cl-m6r-placement-seeds120-139.tar.gz"
m6r_pilot="/home/jiangle/aura-work/aether-cl-m6r-placement-seeds120-139-pilot.tar.gz"
test ! -e "$m6r_output"
test ! -e "$m6r_archive"
test ! -e "$m6r_pilot"

python -u -m aether_cl.m6r_sweep \
    --commission-report runs/m6r-known-commission/suite.json \
    --output "$m6r_output" --archive "$m6r_archive" --stop-after 24

python -m aether_cl.m6r_sweep \
    --output "$m6r_output" --archive "$m6r_archive" --check-pilot

python - <<'PY'
import json
import shutil
from pathlib import Path
report = json.loads(Path("runs/m6r-placement-seeds120-139/suite.json").read_text())
source = Path(report["saved_archive"])
target = Path("/home/jiangle/aura-work/aether-cl-m6r-placement-seeds120-139-pilot.tar.gz")
with source.open("rb") as incoming, target.open("xb") as outgoing:
    shutil.copyfileobj(incoming, outgoing)
print("Immutable M6R pilot:", target, flush=True)
PY

python -u -m aether_cl.m6r_sweep \
    --output "$m6r_output" --archive "$m6r_archive" --resume
