# AETHER-CL M1 Fixed Controller Candidate

Date: 2026-10-05 (Asia/Shanghai)

Status: target-server initialization reached the controller action-space check,
which exposed an implementation error before the first action. That check is
corrected; native controller acceptance and success-rate measurement pending.

## Objective and scope

Replace random smoke actions with an inspectable, repeatable PickCube attempt.
This is the first engineering controller baseline. It does not establish the
research hypothesis about verification/recovery and is not a learned VLA policy.
The M0 server evidence establishes that the environment and raster renderer work;
it does not establish that this new controller grasps successfully.

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

Next on the A100: inspect seed 0 for one 360-step episode with the live viewer,
then run fixed-seed batches and inspect saved episode results. Reuse the private
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
