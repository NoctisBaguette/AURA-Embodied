# AETHER-CL M3 Episode Isolation Correction

Date: 2026-10-05 (Asia/Shanghai)

Status: original seed-40–59 comparison rejected; per-episode process correction
prepared and locally validated. Corrected native execution remains pending.
No controller, task, verifier, budget or disturbance settings are changed.

## Original native evidence and rejection

The uploaded `aether-cl-m3-screening-seeds40-59.tar.gz` has SHA-256
`c8c73ef11f91c9ea55d519701660c89456b55cbd5fc1e283fbd5fa2a1257fb74`
and size 22,177,033 bytes. All 48 unique regular archive members and all 47
indexed sizes/hashes verify. Clean `3284b504` records 180 original seeded
resets: 171 eligible episodes and nine exclusions of the same seed 58.
All eligible episodes execute 360 actions, giving 61,560 audited actions.
No seed was substituted. All 88 tests also pass in the supplied native output.

Raw policy/recovery action and decision replay, reference/verifier verdicts,
recovery snapshots, task geometry/stability, dense agreement metrics,
relocation timing/geometry, episode summaries and child stdout/results agree.
The maximum action replay error is 2.98e-8 from the known float32 Panda base
pose. All three baseline/V1 full trace pairs agree exactly. Normal V1/V2 also
agrees completely. See the
[failed-batch audit](evidence/AETHER_CL_M3_Failed_Screening_Audit.json).

| Condition | Baseline individual outcomes | V1 individual outcomes | V2 individual outcomes | Recovery comparison |
| --- | --- | --- | --- | --- |
| Normal | 19/19 success | 19/19 success | 19/19 success; no attempt | Valid |
| Shift | 0/19 success | 0/19 success | 19/19 success | Rejected: reset differs |
| Drop | 0/19 success | 0/19 success | 19/19 success | Rejected: reset/prefix/injection differs |

These disturbed outcomes are raw behavior observations, not an accepted paired
recovery effect or robustness rate. Do not relabel the original suite as passed.

For both disturbed conditions, seeds 41–59 (including excluded seed 58) differ
only in reset observation `extra.is_grasped`: passive false versus recovered
true. The preceding recovered episode ends grasping, while the passive episode
ends empty handed. The reset's geometric/joint fields match. This flag does
not enter the policy, verifier or recovery, but the full reset check remains
strict and must not silently omit it.

In drop seeds 48, 50, 54 and 59, preintervention step traces and logged injection
poses also differ. First physical differences occur at steps 101, 102, 101 and
102, all before diagnosis at 183 or the first recovery action at 184. Some
start at float32 scale; seeds 50/59 already show q-velocity differences around
0.0124/0.0119 at their first differing step. Thus this is not merely a harmless
contact-label discrepancy, and numeric tolerances or dropping fields would
not repair the experimental design.

Each original cell reused its native simulator for 20 resets. The observations
are consistent with simulator history persisting across seeded resets after
recovery changes an earlier trajectory. The exact native contact/solver/cache
mechanism is not proven by these logs. Remove environment/process reuse and
test the correction rather than asserting the engine cause.

## Correction and protocol amendment

The [original protocol](AETHER_CL_M3_Frozen_Screening.md) and failed archive
remain preserved. The [amended machine protocol](evidence/AETHER_CL_M3_Isolated_Screening_Protocol.json)
keeps the same seeds, policy/recovery/task/verifier settings, 0.12 m
interventions, and 360-action budgets. Only execution isolation changes:
**one fresh Python interpreter and one fresh simulator per condition/system/seed**.
The order is condition, seed 40–59, then baseline/V1/V2. Every child executes
exactly one reset/episode and closes; the parent does no simulator execution.
The same captured startup environment is passed to all 180 children.

Nine frozen sources are guarded: the eight accepted execution/helper sources
plus the original screening checker. They remain byte-identical. The original
settings protocol and the exact amendment are verified before output or child
launch. A separate entry point uses the unchanged `aether_cl.m3` subprocess
helper and existing integrity/pair checkers.

All 20 preselected seeds remain present in each cell. A single excluded reset
is valid zero-action episode evidence; the eligible-evidence requirement moves
to the complete 20-seed cell. It is not waived for the cell, and no seed is
resampled. Native episode indices stay at zero for these one-episode children;
`requested_seed_index` identifies the seed's position in the original list.
No raw files or indices are rewritten to fabricate a 20-episode native run.

Each seed gets a strict baseline/V1 full comparison and V1/V2 reset/causal-prefix
comparison: 60 passive pairs and 60 recovery pairs. Normal episodes may still
fail naturally; failed attempts, false alarms, uncertainty, unsupported/late
diagnoses and exclusions remain measured outcomes. Cell denominators and
conditional attempt costs include failures. Incomplete cell rates and invalid
paired effect estimates remain null. Errors/interruption retain all available
raw evidence and process logs in a new exclusive archive.

The same seeds have now been seen. This rerun is a correction replication of
the original preselected batch, not 20 additional unseen seeds or a tuning
opportunity. A failure again must be audited rather than relaxed. Only after
valid comparison evidence should subsequent controller variants receive a new
protocol and new seeds.

## Live motion and precision observations

The supplied screenshot shows the live seed-0 drop run
`runs/m3-v2-drop-live/20261005T072914Z-84a4c6cf` finished at step 360 with
`attempt_complete`, task success true, 156/177 retry actions and a displayed
cube–goal distance of 1.4 cm. The operator saw reacquisition and goal transport.
This is screenshot/operator evidence; no live raw logs accompany this batch
archive.

The baseline is a timed sequence: approach 60 steps, descend 40. At five-FPS
viewer pacing these consume about 20 wall-clock seconds. Timing is intentional
and not reasoning/model latency. Changing FPS affects wall-clock viewing speed,
not the simulated controller schedule or physics timestep.

Transport targets `max(cube_z + 0.12, goal_z + 0.06)` before lowering to the
goal. The raised path is a conservative fixed waypoint, not obstacle-aware
planning. Recovery's arrival tolerance is 2 cm, versus task tolerance 2.5 cm.
After attempt completion it holds the last absolute command; therefore a
nonzero final offset such as the displayed 1.4 cm can legitimately pass.
This is coarse target-reaching, not demonstrated insertion precision.

ManiSkill 3.0.1's [Panda settings](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pick_cube_cfgs.py)
use a 4 cm cube and 2.5 cm goal threshold. The
[task source](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pick_cube.py)
renders a sphere of that radius, 5 cm across, with no collision geometry.
It can visually obscure the cube/gripper and is not an object to grasp.
A future smaller visual marker should be separate from task tolerance.

Later experiments can assess observed-arrival nominal phases, continuous
fine correction near the goal, tighter tolerances, and shorter transfer paths.
Freeze this current comparison first; those changes alter intervention/policy
or scoring and need separate evidence. Camera perception, physical force
perturbations, richer scenes and other tasks likewise require explicit protocols.

## Running

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.m3_isolated_screening \
    --output runs/m3-screening-isolated-seeds40-59 \
    --archive /home/jiangle/aura-work/aether-cl-m3-screening-isolated-seeds40-59.tar.gz
```

This is a measurement-only batch and may take longer because every episode
starts a native process. Progress prints each of the 180 trials. Do not chain
live viewing behind the batch exit status; launch the paused viewer separately
when needed. No additional packages, driver changes or 4090 are required.

## Validation

All 92 local tests pass, including four new regressions that reproduce stale
reset carryover under reuse, preserve strict pair rejection, verify 180
one-episode calls with the same captured environment and all archive hashes,
retain excluded seed 58 without resampling, guard frozen execution/settings,
and retain error/interruption evidence with null incomplete rates. Python 3.10
syntax, CLI help, and documentation links verify. These fixtures validate the
process/data contract; the new native replication remains pending.
