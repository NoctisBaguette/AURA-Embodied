# M6R native execution

Use the published M6R implementation commit supplied with the command block.
Keep the existing native `aether-cl` environment. The completed M6 study stays
retained; no previous evidence is removed, restarted or overwritten.

## Deployment

The server is offline. Fetch the published `06-01/aether-cl-m0` branch on the
laptop, make a new Git bundle, transfer it using the established SSH connection,
then fetch that bundle on the server and detach at the pinned implementation
commit. Check the worktree is clean before and after checkout. No dependency
installation is needed.

In the server's prototype directory, initialize the existing environment:

```bash
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
```

Do not run from base Conda. Do not set `XDG_SESSION_ID=876` as an M6R requirement:
that value belonged to the old M6 study. A new study records its actual startup
environment; any continuation must preserve that recorded environment.
Use a subshell for fail-fast setup checks so an error does not close the SSH shell.

## First operation: known-seed commissioning only

Run the focused M6R regression suite on the server before native simulation:

```bash
python -m unittest discover -s tests -p test_m6r.py -v
```

Then launch the 16 known-seed development slots detached from SSH:

```bash
nohup python -u -m aether_cl.m6r_sweep \
  --commission-known \
  --output runs/m6r-known-commission \
  --archive /home/jiangle/aura-work/aether-cl-m6r-known-commission.tar.gz \
  > /home/jiangle/aura-work/m6r-known-commission.log 2>&1 < /dev/null &
echo "M6R commissioning PID: $!"
tail -f /home/jiangle/aura-work/m6r-known-commission.log
```

Output and archive must be new. This runs only seeds 100/101, normal and 8 cm,
all four systems. It does **not** start seeds 120–139. Ctrl+C stops `tail`, not
the detached runner. SSH disconnection does not stop the measurement parent.

When the log finishes, inspect without launching another trial:

```bash
python -m aether_cl.m6r_sweep \
  --output runs/m6r-known-commission \
  --archive /home/jiangle/aura-work/aether-cl-m6r-known-commission.tar.gz \
  --check-commission
```

Expected evidence sentinel: `M6R_KNOWN16_VALID`. This validates engineering
evidence and exercises the semantic boundary; V2R final success is not required.
Upload `aether-cl-m6r-known-commission.tar.gz` and the log for independent review
of native behavior before launching fresh evaluation. If execution/evidence
fails, retain the archive and logs; do not overwrite directories or rerun slots.

## Fresh evaluation after commissioning review

The authorized fresh study remains the frozen 480-slot matrix on 120–139.
Use the same implementation revision and environment. The runner requires and
replays the known16 report, checks for prior recorded native resets of selected
seeds, and stops before the fresh study if either guard fails.

The [single-parent launch script](../../../aura-sim/prototype_aether_cl/scripts/run_m6r_fresh.sh)
runs first24, checks the evidence/viability pilot, copies its immutable archive,
then resumes only the remaining 456. All calls inherit one environment, avoiding
the M6 reconnect/session mismatch. It stops on any pilot failure and preserves
the partial archive. It does not gate on V2R success or tune from pilot outcomes.

After review, set `M6R_COMMIT` to the exact published frozen implementation SHA:

```bash
test "$(git rev-parse HEAD)" = "$M6R_COMMIT"
test -z "$(git status --porcelain)"
nohup bash scripts/run_m6r_fresh.sh "$M6R_COMMIT" \
  > /home/jiangle/aura-work/m6r-placement-seeds120-139.log 2>&1 < /dev/null &
echo "M6R fresh study PID: $!"
tail -f /home/jiangle/aura-work/m6r-placement-seeds120-139.log
```

On completion return final archive, copied first24 pilot archive, known16
commissioning archive and logs. Native runner `state: passed` means valid
evidence, not successful recovery. Independent replay/audit comes next, followed
by return to 02. No next task or motion correction starts automatically.
