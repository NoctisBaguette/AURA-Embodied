# AETHER-CL M6 — Support Placement and Release

Date: 2026-10-06 (Asia/Shanghai).

Status: implementation, native commissioning, full execution and independent
archive audit are complete. The original preregistered method below is retained.
See [audited native results](AETHER_CL_M6_Results.md): V2 rescues none of 62
failed placements; all attempts abort at lower before release.
[Return to 02](AETHER_CL_M6_Return_to_02.md) for review before further work.

Authority: [02's M5 acceptance and M6 scope](AETHER_CL_M5_02_Research_Review_v0.1.md)
and DEC-0004, accepted at `03b9b2dc77c33dc1aa47edd67dcb20238ad8b0bb`.
M5 is accepted within scope. This reactivates 06-01 for **M6 only**; Prototype A
remains scientifically open. PR #1 stays draft and unmerged.

## Question and matched systems

Does verification-gated bounded recovery improve manipulation when the desired
endpoint is a released, independently supported object rather than a held cube?

| System | Nominal controller | Verification | Recovery |
| --- | --- | --- | --- |
| Baseline | New frozen placement schedule | Disabled | Disabled |
| V1 | Identical placement schedule | Passive geometry/velocity checks | Disabled |
| V2 | Identical placement schedule until intervention | Same verifier | One bounded replacement attempt |

V3 is retained historically for M5 and is absent from this matrix. The new task
requires a new nominal baseline; do not compare its success rates directly to
M0–M5 as if task semantics and action budgets were unchanged. No old scientific
execution module or protocol is modified.

## Designated support and goal

Reuse PickCube-v1's Panda, 4 cm cube and existing collision-bearing
`table-workspace` actor. No new asset or package is needed. The designated
support is its horizontal top at world z=0, restricted to a world-XY square
[-0.4, 0.4] on both axes, safely inside the installed table collision geometry.
The randomly sampled goal XY is retained; its Z is projected to the cube centre
at 0.02 m. The original sampled goal, projected reset state, table pose, cube
geometry and robot base pose are recorded. The visible green goal sphere has
no collision and is not a support surface.

The native adapter rejects GPU physics, a different cube size or table pose/
orientation. It records hashes of five installed ManiSkill source modules.
Those hashes must agree across the entire matrix, in addition to the existing
software/version, own-source and startup guards.

Upstream implementation references, checked while designing this adapter:

- [ManiSkill v3.0.1 table builder](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/mani_skill/utils/scene_builder/table/scene_builder.py).
- [ManiSkill pairwise contact-force API](https://maniskill.readthedocs.io/en/latest/user_guide/tutorials/custom_tasks/advanced.html#pair-wise-contact-forces).

The frozen child requires the existing Python 3.10, ManiSkill 3.0.1, SAPIEN
3.0.3 and NumPy 1.26.4 environment. All other software and native startup
settings are captured unchanged. No dependency installation is part of M6.

## Physical success contract

Final task success requires every condition for **five consecutive fresh
post-action observations**:

- Eligible reset, historical contact grasp and at least 5 cm achieved lift.
- An actual release command has occurred, fresh contact reference says the
  cube is not grasped, and gripper aperture is at least 6 cm.
- Cube bottom is within 4 mm of the table top, its complete oriented footprint
  is inside the designated support region, and the cube/table pair has at
  least 0.01 N absolute vertical contact force.
- Horizontal cube-centre error is at most **2.5 cm** and the goal is unchanged.
- TCP is at least 8 cm above and at least 8 cm away from the cube centre.
- Cube linear speed is at most 0.01 m/s, angular speed at most 0.2 rad/s,
  inter-frame translation at most 1 mm and rotation at most 0.02 rad.

The reference contact query targets the table actor specifically; floor contact
or proximity alone cannot establish independent support. Absolute vertical
force is used to avoid actor-order sign conventions; bottom/footprint geometry
also remains mandatory. Opening at the goal while the gripper supports the
cube is insufficient. The built-in environment success flag is logged but
never used as the M6 success criterion or controller input.

Release, independent support/stability, retraction, horizontal error, controller
completion and final task success are reported separately. Support/stability
has its own consecutive counter independent of target-region satisfaction.
Success seen earlier does not override final failure.

Initially within the 2.5 cm horizontal target region means excluded zero-action
evidence. These seeds remain in their selected slots and are not replaced;
eligibility must agree across paired systems.

## Nominal schedule and task-specific extension

| Phase | Actions | Cumulative endpoint |
| --- | ---: | ---: |
| Approach | 60 | 60 |
| Descend to cube | 40 | 100 |
| Close | 25 | 125 |
| Lift | 45 | 170 |
| Transport | 60 | 230 |
| Lower to placement | 40 | 270 |
| Release | 25 | 295 |
| Retract | 35 | 330 |
| Settle/observe | 30 | 360 |

Subsequent nominal actions retain the open retracted pose. Every eligible
trial runs the same **800-action global budget**, including stationary tail
observations. The longer budget accommodates real release/retraction and one
replacement attempt; it is frozen before fresh native evaluation.

The first six phase durations and all Cartesian coordinate/rotation/bounded
servo calculations reuse the unchanged FixedPickCube primitives. Goal Z and
lower/release targets change for the support task. Release holds TCP 2 mm above
the desired cube centre, opens, and retracts to the original 12 cm clearance.
Nominal phase transitions are clock-only; no contact, verifier, object update,
success or disturbance identity changes nominal actions after reset.

These extensions implement the authorized new task; they are not an old-task
motion/precision optimization.

## Post-release disturbance and controls

At action **296**, after nominal release and before final stability verification,
compute the ordinary next action first and then attempt one synthetic positive
world-Y translation of the cube. Preserve quaternion, X and Z; zero linear and
angular velocity; let the following CPU physics step propagate the relocated
state. This is a pose intervention, not a force/impulse experiment.

The preceding observation must be ungrasped, geometrically open/released and
supported, and the selected current phase must be nominal retract. If earlier
failure or recovery prevents that post-release state, log the failed injection
precondition, retain the episode and do not exclude it, relocate it at another
time, grant an additional recovery or replace its seed. Report actual injection
coverage separately from selected condition counts.

| Point | Magnitude | Purpose |
| --- | ---: | --- |
| Normal | None | Healthy placement/no unnecessary intervention |
| Release shift | 1 cm | Within-tolerance control without forcing recovery |
| Release shift | 4/8/12/20 cm | Placement-phase target failures and replacement costs |

A 1 cm shift is an intended easy control, not a guarantee of success for every
native seed: prior placement error and geometry can still matter. All outcomes
are retained.

## Verifier and one recovery episode

The verifier reads simulator object pose/velocities, TCP, gripper joints and
controller phase clocks. It uses bottom/footprint geometry as a support proxy;
it does not read contact grasp, table forces, environment success, the reference
or disturbance labels. This remains privileged-state verification and does
not satisfy the future non-privileged sensor-verifier closure dimension.

Three consecutive matching failures confirm the invocation verdict. Failure
categories are grasp failure, object lost, lift not achieved, placement target
not reached, release not achieved, unsupported placement, retraction not
achieved, post-release instability, state mismatch and uncertain observation.
Intentional release is not classified as object loss. The settle phase has a
fixed ten-observation grace before endpoint diagnosis. Agreement counts are
against the separate contact reference; geometry shared between mechanisms
limits their independence.

V2 consumes the preceding confirmed verdict, refreshes cube/goal once, and may
perform one bounded sequence: safe retraction, approach, descend, close, lift,
transport, lower, release, retract and settle. It reuses the original motion
servo and observed arrival/attachment/lift ideas. The placement-specific lower
gate also requires vertical arrival within 3 mm; release/retraction/stability
get their own gates. There is no second retry after completion or abort.

Attempt action budget is min(400, remaining global actions); fewer than 100
remaining actions declines an attempt. Phase caps are 35/60/35/25/35/80/40/
25/35/30. On abort or completion, repeat the last absolute command, with no
nominal resumption. Endpoint contact scoring stays independent of controller
completion or local geometric success.

## Frozen matrix and execution order

Fresh preselected seeds **100–119**, six conditions and three systems:
**360 isolated one-episode children, 18 cells, at most 288,000 actions**.
Twenty common initial seeds are reused across conditions; these are not 360
independent scenes. No outcome-based replacement or retiming.

First 18 slots: normal, 1 cm shift, 8 cm shift; seeds 100 and 101; Baseline,
V1, V2. They remain in the final dataset. Remaining slots follow normal then
ascending magnitudes, ascending seed, Baseline/V1/V2, omitting those 18 slots.

The first-18 commissioning gate requires complete valid replays and exact
pairs, consistent native sources, at least one eligible healthy baseline
placement, and applied post-release shifts on eligible Baseline/V1 sentinels.
It does **not** require V2 recovery success. If the new task/intervention cannot
be commissioned, keep the study paused and upload its preserved pilot archive
before launching the rest. Failed pilot outcomes are never dropped or rerun;
this is a preregistered viability pause, not a final-study success filter.

After commissioning, resume only the remaining 342 slots under nohup. A study
lock, normalized startup-environment hash, source/protocol/software identity,
raw hashes and replay checks protect continuation. Errors/interrupted slots
remain recorded and are not silently rerun. An abrupt kill leaving an unfinished
slot stops automatic continuation; do not manually remove it to force a rerun.
Partial archives are immutable; the final archive is exclusively created.

## Required evidence and comparisons

The [machine protocol](evidence/AETHER_CL_M6_Placement_Protocol.json) freezes
source hashes and all semantics above. The previous M0–M5 preflight chain stays
intact. Every child retains manifest, raw action/observation events, result and
stdout/stderr. Parent evidence indexes all files with exact sizes and SHA-256.

Each trial reconstructs every action (existing 3e-7 tolerance), decision,
reference state, verifier verdict, recovery snapshot, total/attempt path,
injection geometry/order, terminal summary and verification metric. Physical
pair comparisons are exact; no tolerance is relaxed.

- **120 Baseline/V1** full physical pairs, including reset contact information.
- **120 V1/V2** exact reset and causal-prefix pairs through the preceding
  failure verdict, or the entire trace if there is no intervention.
- **100 normal/disturbed Baseline** exact pre-injection controls through 295.

Rates/effects are null for incomplete or invalid comparisons. An installed
upstream-source drift invalidates all scientific rates. Both successful and
failed/aborted attempts contribute to cost summaries. Unnecessary recovery is
an attempt where the paired baseline succeeds; regression is paired baseline
success followed by V2 final failure. Denominators remain eligible matched
episodes. Ordered float accumulation permits exact Python 3.10/3.12 aggregate
reproduction without widening equality checks.

## Live inspection

`python -m aether_cl.m6 --live ...` has a dedicated **M6** page with correct
Baseline/V1/V2 names, released/support/stability/retraction status and current
phase. It binds loopback port 8765, shows the first frame, waits for Enter in
the server terminal, then preserves the final frame until Ctrl+C. Rendering
uses local cuda:0 under CUDA_VISIBLE_DEVICES=1. One full demonstration is
approximately 80 seconds at 10 FPS because the budget includes stationary
tail observations.

Native measurement remains unrendered/unpaced with CPU physics and the existing
A100 selection. The measured archive contains no video. Separate live runs
have separate directories and do not replace or stand in for measured evidence.
Choose a useful case after the native audit.

## Validation and native completion

Local fixtures test actual endpoint semantics, reused servo input boundaries,
intentional release handling, replacement and release, one-attempt preservation,
uncertain/stale frames, native-adapter wiring, exact matched/control traces,
zero-action exclusions, interrupted cleanup, raw replay/tamper rejection,
360-slot continuation, hashes, installed-source drift, null invalid rates and
M6 viewer labels/preview/final-frame retention. Fixtures do not establish native
contact/physics performance. Python 3.10 parsing and CLI help are checked.

All **121 local tests passed in 211.364 seconds**, including 16 M6 tests.
The targeted M6 suite separately passed in 22.705 seconds. Documentation
links and frozen source/protocol agreement were checked before publication.

Native commissioning, all 360 retained trials and independent archive audit
are complete. All 259,200 actions, 340 strict comparisons and endpoint scoring
replay; pilot/final JSON and CSV reproduce exactly. The
[audited results](AETHER_CL_M6_Results.md) retain all exclusions and failures.

The first native launch encountered a parent JSON serialization failure after
its completed first child. The separate
[reporting repair](AETHER_CL_M6_Reporting_Repair.md) continued the retained study
on the original scientific checkout, preserving the first child and pilot bytes
without reruns. The reporting exception and recovery failures are distinct.

## Return boundary

After M6 native execution and independent audit, **return to 02 before any
further implementation**. M6 does not authorize insertion, physically applied
disturbance research, camera verification, memory, learned experience, world
models, Prototype B/C/D, foundation-model integration or 02W. Prototype A
scientific closure remains 02's decision.
