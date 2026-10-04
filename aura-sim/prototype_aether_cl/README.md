# AETHER CL Prototype A

This directory implements the first environment milestone for AETHER-CL v0.1.
Its current commands run **seeded random actions**, check CPU physics and
offscreen camera rendering, and record the resulting episode. They do not yet
implement a manipulation policy, verification, diagnosis, or recovery.

Prototype A will test whether explicit verification and bounded recovery improve
manipulation autonomy under disturbances while keeping the manipulation policy
fixed. Its findings return to branch 02 for AETHER architecture research.

## Current milestone

- A single `PickCube-v1` environment, Panda arm, CPU physics, state observations.
- GPU offscreen raster rendering, with the render device chosen explicitly.
- Finite episodes with deterministic reset/action seeds and step limits.
- A read-only browser viewer bound to `127.0.0.1:8765`.
- Run metadata, action/observation events, episode results, and the latest frame.

`PickCube-v1` tests reaching a goal with the cube and a static robot. It does not
require releasing the cube onto a support surface. Use it as an infrastructure
smoke test; the research pick-and-place task needs an explicit placement/release
condition before policy evaluation.

## Isolated server environment

Initial target: Ubuntu 22.04 and the available A100 server. The existing
`robotwin-sim` and `lingbotvla` environments are useful references but have
different dependencies. The following commands create a separate environment.

From an SSH terminal, enter the repository and this directory, then run:

```bash
bash scripts/setup.sh
conda activate aether-cl
```

The setup script stops on failure and refuses to reuse an existing `aether-cl`
environment. It activates and checks the new environment before installing
packages. If `aether-cl` already exists, inspect it before reusing it. SAPIEN 3.0.3 satisfies ManiSkill 3.0.1's Linux
requirement `sapien>=3.0.0`; RoboTwin's SAPIEN 3.0.0b1 does not.

These pin the main runtime packages, not every transitive dependency. Record the
installed environment after successful resolution. The setup script writes
`runs/installed-packages.txt` for that purpose.

## Separate physics and rendering checks

First run a short test without camera capture:

```bash
python -m aether_cl.smoke --no-render --max-steps 5 --output runs/physics
```

Then test offscreen rendering on an available GPU:

```bash
nvidia-smi
python -m aether_cl.smoke --render-device cuda:1 --max-steps 5 --output runs/render
```

`cuda:1` is an explicit example for this server, not a reserved GPU. Check
availability and any local allocation rules before running. Device numbering can
change when `CUDA_VISIBLE_DEVICES` is set. The run log records the selected
SAPIEN render device and visibility setting. This milestone uses CPU physics;
GPU physics and multi-GPU execution are not required.

Success means the command exits successfully and writes `result.json` with
`state: finished`. The rendering test must also produce a nonconstant
`latest.jpg`. Random actions usually do not complete the task; an environment
success flag of false is not a smoke-test failure.

This skips frame capture, not every graphics dependency: ManiSkill's task
construction can create SAPIEN render materials even when camera rendering is
disabled. A failure during scene construction must be distinguished from a
failure while capturing a camera frame.

If stepping works but camera capture fails, preserve the complete traceback and inspect
the Vulkan/renderer configuration before changing simulator or hardware. A
missing `vulkaninfo` utility does not establish whether Vulkan rendering works.
No system driver changes are performed by these commands.

## Live browser viewer

After both smoke tests pass, run in the server terminal:

```bash
python -m aether_cl.viewer --render-device cuda:1 --episodes 3 --fps 5 --port 8765
```

In a separate **local PowerShell** terminal:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -L 127.0.0.1:8765:127.0.0.1:8765 YOUR_SERVER_ALIAS
```

Replace `YOUR_SERVER_ALIAS` with the configured SSH destination, or supply
`-p SSH_PORT USER@HOST`. Open <http://127.0.0.1:8765>. This run uses a separate port from the current
LingBot service on 8000. Check local port availability as well as server port
availability. If needed, choose another port in both commands.

The viewer starts one finite run and remains available with the final frame.
Ctrl+C stops the process. It provides no robot-control endpoints. An occupied
port is detected before creating the simulator. Camera rendering is observational
and introduces no changes to policy behavior; the viewer adds wall-clock pacing
for visibility, which is recorded in the run configuration.

## Output and interpretation

Each invocation creates a new UTC/UUID directory under `runs/` containing:

- `manifest.json`: runtime packages, code commit/dirty state, seeds, backends,
  action/observation modes, and a clear random-action smoke-test label.
- `events.jsonl`: resets, per-step actions and observations, termination flags,
  errors, selected rendering device, and episode boundaries.
- `result.json`: final run state and per-episode outcomes, distinguishing success
  at the final step from success at any earlier step.
- `latest.jpg`: the latest actual simulator frame, when rendering is enabled.

`runs/` is excluded from Git. No benchmark numbers or policy results are claimed
by this milestone. CPU tests of logging and HTTP behavior do not validate GPU
rendering; the server smoke tests provide that evidence.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m aether_cl.smoke --help
python -m aether_cl.viewer --help
```

## Next implementation milestones

1. Reproduce a competent fixed policy and define full task success.
2. Add verification with explicit observation access and checkpoint semantics.
3. Add failure classification and recovery within a fixed total action budget.
4. Compare policy-only, passive verification, verification/recovery, and a
   budget-matched simple retry control on matched disturbance schedules.

Long-term memory, learned experience abstraction, embodiment transfer, a full
planner, world models, and foundation-model training remain outside Prototype A.

## Upstream references

- [ManiSkill 3.0.1 dependency definitions](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/setup.py)
- [ManiSkill installation and Vulkan troubleshooting](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html)
- [PickCube task definition](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pick_cube.py)
