# AETHER-CL M1 Fixed Controller Candidate

Date: 2026-10-05 (Asia/Shanghai)

Status: native baseline screening and supplied raw-log inspection complete.
The current PickCube baseline reported 20/20 successes; one reset was already
solved and the other 19 episodes grasped and lifted the cube. See the
[screening report](AETHER_CL_M1_Baseline_Screening.md) for task/reset limitations
to address before verification/recovery comparisons.

## Objective and scope

Replace random smoke actions with an inspectable, repeatable PickCube attempt.
This is the first engineering controller baseline. It does not establish the
research hypothesis about verification/recovery and is not a learned VLA policy.
The M0 server evidence establishes that the environment and raster renderer work.
The first M1 native result establishes one successful attempt; it does not
establish reliability across resets or robustness under disturbances.

PickCube-v1 uses a Panda robot, CPU physics, privileged `state_dict` observations,
and GPU offscreen rendering. Success means cube-to-goal distance at most 0.025 m
and a sufficiently static robot according to the environment evaluator. Release
onto a support surface is not required. Actual pick-and-place release/support
criteria remain a separate task-definition requirement.

## Frozen-sequence design

Controller: `fixed_pick_cube`, version `0.1-candidate`.

| Phase | Control steps | Intended motion | Gripper |
| --- | ---: | --- | --- |
| approach | 60 | move above the initial cube and align a top-down grasp | open |
| descend | 40 | move to initial cube centre | open |
| close | 25 | hold that pose | closed |
| lift | 45 | move 0.12 m above the initial cube | closed |
| transport | 60 | move above the goal, maintaining clearance | closed |
| lower | 40 | move to the goal | closed |
| hold | 50, then remaining budget | hold the goal pose | closed |

There are 320 scheduled steps; the acceptance command allows 360. A normalized
gripper command is combined with absolute base-frame position/intrinsic XYZ
Euler angle commands through Panda's `pd_ee_pose` controller. Each servo update
limits TCP translation to 0.012 m and rotation to 0.08 rad. This uses existing
ManiSkill inverse kinematics, not a task planner.

At reset, cache cube pose, target position, initial TCP pose, and robot base
pose. During execution, reread only TCP pose for low-level position/orientation
feedback. The schedule progresses by control-step count even if grasping fails.
The policy never receives evaluator info, grasp flags, success flags, disturbance
labels, or failure classifications. It does not retry or revise its targets.

This privileges simulator state and limits any later research claim to that
observation regime. A learned or visual policy can be evaluated separately after
its inputs/settings are fixed; it must not silently replace the policy between
Baseline/V1/V2 comparisons.

## Logging and interpretation

`manifest.json` records the code revision, runtime versions, controller settings,
input boundaries, control mode, GPU visibility, and native library environment.
It also records the declared action-space shape. Single-environment `(7,)` and
single-batch `(1, 7)` spaces are supported; the runtime adapts the same seven
controller values to the declared shape and validates them before execution.
Each action event records phase, expected target TCP position, commanded TCP
position, action, observation, environment info, and evaluator-only object/goal
distance. These diagnostics do not feed the controller. `result.json` records
episode budgets, final/any-step success, final task distance, grasp/place/static
flags, schedule completion, and final/any-step aggregate success rates.

An interrupted run has no complete aggregate success rate. A runtime exception
remains an execution error and is not converted into a policy failure score.
`state: finished` is run completion and does not imply task success. Viewer FPS
changes wall-clock display pacing, not the phase schedule or simulator steps.

## Validation and next acceptance

Sixteen local tests passed: controller action coordinate conventions, bounded
servo changes, time-only progression, cached target storage, exclusion of
future object/goal/evaluator data from action inputs, config guards, evaluation
denominators, stopped-run handling, and existing logging/render encoding/HTTP
contracts. Controller integration fixtures do not simulate native contacts or
grasp physics. CLI and Python compilation checks passed.

The first native acceptance attempt at commit `1f0b0a2` passed those 16 tests on
Python 3.10.22 and confirmed one visible A100. Its action space was `(7,)`, while
the initial runtime required `(1, 7)`; execution stopped before the first action
or frame. The corrected runtime passed 19 local tests, including full evaluation
and logging with both shapes, preservation of action values, invalid-action
rejection, and cleanup before stepping unsupported spaces. The policy itself
is unchanged. This blocked run is an implementation error and supplies no
native grasp or success-rate evidence.

The corrected seed-0 live episode finished at step 202 during transport, with
cube-to-goal distance 0.023378149725868044 m and environment success/grasp/static
flags true. The screenshot agrees with the supplied
[viewer status JSON](evidence/AETHER_CL_M1_seed0_viewer_status.json).
The environment terminated on success before the 320-step schedule finished;
`schedule_complete: false` is expected for this early successful termination.
This does not test release or subsequent holding. Deployment followed the
instructions for `bfd1446`; the subsequently supplied raw manifest/event logs
confirm that clean revision and the complete 202-step trajectory.
The single-episode 1.0 success rate does not measure general reliability.

The subsequent nonrendered 20-seed batch used the same clean code/settings and
360-step limit. All 4,042 batch step records were audited; seed 0's actions,
observations, and diagnostics match the rendered trajectory exactly. Seed 8
started inside the goal tolerance and terminated without grasping, so 20/20
raw environment successes include one already-solved episode. All 19 initially
unsolved episodes grasped and lifted before success. This post-hoc subset
description does not replace a predeclared benchmark denominator.

Next: retain the current controller as the nominal baseline, resolve shared
reset eligibility/task criteria and fresh verification observations, then
implement M2 verification and controlled disturbances. The current batch is
not the final held-out disturbance benchmark. Reuse the private
OpenGL workaround from M0. Expose the selected physical GPU with
`CUDA_VISIBLE_DEVICES=1` and render with process-local `cuda:0`, following
ManiSkill's documented mapping. No dependency/driver reinstall is needed.

If grasping or transport fails, diagnose and adjust this M1 candidate before
freezing it. After baseline acceptance, fix code/settings/inputs and matched
episode/recovery budgets for Baseline, V1 (verification only), and V2
(verification plus recovery). Disturbance injections and final benchmark
evaluation are not implemented in this increment.

Sources: installed ManiSkill 3.0.1 wheel (`panda.py`, `pd_ee_pose.py`,
`kinematics.py`, `pick_cube.py`) and
[GPU selection documentation](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/quickstart.html#additional-gpu-simulation-rendering-customization).
