# AURA-Embodied Experiment Log

This document records reproductions, implementations, modifications, evaluations, and experimental findings.

Experiments should preserve not only results, but also reasoning and failure analysis.

---

# EXP-0001 Preparation

Date: 2026-10-04

AETHER-CL Prototype A asks whether explicit verification and bounded recovery
improve manipulation autonomy under disturbances with a fixed policy.

Milestone 0 prepares an isolated simulator environment, finite random-action
smoke tests, episode logging, and a browser viewer for the A100 server. This is
infrastructure preparation; it does not yet produce manipulation-policy or
verification/recovery results. Initial server validation is recorded below.

See [the milestone plan](docs/research/experiments/AETHER_CL_M0_Environment_Plan.md)
and [implementation instructions](aura-sim/prototype_aether_cl/README.md).

Deployment update (2026-10-05, project timezone): direct server retrieval was
replaced by laptop downloads and SSH transfer. User-provided output confirms the
repository arrived via Git bundle and `aether-cl` was copied offline from
`robotwin-sim`. The copied package inventory guides an incremental Linux/Python
3.10 wheel set; it does not establish successful simulator execution. Installation,
native imports, physics, and rendering remained server acceptance steps at that point.

## Server rendering and browser evidence

Date: 2026-10-05 (Asia/Shanghai; run timestamps use UTC).

User-provided output confirms successful offline installation and `pip check`,
Python 3.10.22, PyTorch 2.4.1+cu121, OpenCV 4.11.0, CUDA availability, and successful
SAPIEN/ManiSkill imports. The rendering smoke at
`runs/glvnd-smoke/20261004T215207Z-667f7f38` completed five steps with
`state: finished`. The implementation validates and saves a nonconstant RGB
frame during this path. Its task success flag was false, as expected for random
actions; this is not a manipulation-policy success-rate measurement.

Three browser screenshots show changing Panda poses and counters at episodes
1/2/3, steps 68/49/12, through loopback port 8765. The displayed run directory is
`runs/live-viewer/20261004T220709Z-55ffe904`. This establishes basic CPU physics,
GPU camera capture, browser display, and SSH forwarding on the A100 server.
The live run's final result and raw log artifacts have not been retrieved for
independent inspection. A separate camera-disabled run has not been confirmed.

Native-library issue: standard OpenCV initially failed with
`libGL.so.1: undefined symbol: _glapi_tls_Current`. Removing library environment
variables and preloading system Mesa glapi did not help. A private extracted set
of Ubuntu Jammy `libgl1`, `libglx0`, and `libglvnd0`, all version `1.4.0-1` for
amd64, resolved imports and the rendering smoke when its library directory was
selected through process-scoped `LD_LIBRARY_PATH`. No system driver replacement
was needed. This is evidence of a successful workaround, not a complete audit of
the server's system graphics installation. SAPIEN's builtin Vulkan fallback and
PyTorch's all-device RNG warning remained nonfatal; the latter does initialize
CUDA contexts on all visible devices and merits isolation before larger runs.

Scene interpretation, checked against the installed ManiSkill 3.0.1 wheel:
the red cube is the manipulated object; the green sphere is a noncolliding goal
marker. Its position is sampled on episode reset, including a height above the
table. It is fixed within each episode. Camera projection can overlap it with
the arm. PickCube success requires cube-to-goal distance at most 0.025 m and a
static robot, and does not require release onto a support surface.

At this checkpoint the runtime sampled actions randomly and had no task
controller, verification, or recovery. The next step was a fixed controller,
prepared in EXP-0002 below; it must be accepted and frozen before intervention
comparisons. Define actual placement/release criteria separately from this
initial PickCube infrastructure task.

---

# EXP-0002 Fixed PickCube Controller Preparation

Date: 2026-10-05 (Asia/Shanghai)

A fixed state-based controller candidate now replaces random actions when
`--controller fixed_pick_cube` is selected. It caches initial cube/goal poses,
uses TCP feedback with Panda's absolute `pd_ee_pose` interface, and follows a
320-step approach/descend/close/lift/transport/lower/hold schedule without
verification or recovery. Default baseline evaluation allows 360 steps.

Sixteen local policy/runtime tests, CLI checks, and Python compilation passed.
Fixtures validate coordinate/action contracts, information boundaries, logging,
and aggregate metrics; they are not native contact/grasp simulations. No native
controller success rate is claimed. Inspect a live A100 episode and measure
fixed-seed batches before freezing the candidate for intervention comparisons.

See [the M1 protocol](docs/research/experiments/AETHER_CL_M1_Fixed_Controller.md).

## A100 acceptance attempt and action-shape correction

The target server deployed commit `1f0b0a2890ecc1f1c33816fb3fc38b3a8920b51f`.
All 16 tests passed under Python 3.10.22, and Torch confirmed one visible
A100 with physical GPU 1 selected. Native environment initialization/reset
succeeded, but the runtime stopped before its first action or rendered frame:
`Unexpected Panda pd_ee_pose action shape: (7,)`.
The failed run is `runs/baseline-live/20261005T003332Z-8adcbe5d`.

The runtime incorrectly required a batched `(1, 7)` action space. The installed
ManiSkill 3.0.1 source accepts unbatched single-environment actions and batches
them internally. The correction accepts `(7,)` or `(1, 7)`, adapts the fixed
controller command to the declared space, retains Box validation, and records
the declared shape and actual executed action. Policy values, inputs, schedule,
and settings are unchanged.

All 19 local tests passed after the correction, including complete logging runs
with both action shapes, invalid-action rejection, and unsupported-space cleanup.
These fixtures do not simulate contacts. At this correction checkpoint the native
A100 rerun was pending; the blocked attempt is an implementation error, not grasp-failure data
or evidence for/against verification and recovery. No environment reinstall is
required for this correction.

## First successful native fixed-controller episode

The user supplied viewer status JSON and a matching rendered browser screenshot
for `runs/baseline-live/20261005T004231Z-59ee234d`, following deployment instructions
for correction commit `bfd144646187bb4985e5d6678320651e3b94b022`. The raw manifest
and event log were not yet retrieved at that checkpoint. The later archive audit
below confirms the recorded clean revision and trajectory. The [supplied status JSON](docs/research/experiments/evidence/AETHER_CL_M1_seed0_viewer_status.json)
is preserved as reported evidence.

Seed 0 finished successfully at step 202, during transport, with final cube-to-goal
distance 0.023378149725868044 m. The environment reported grasped, object placed,
and robot static, with `terminated: true`, `truncated: false`, and no interruption.
The screenshot shows the cube held near the green goal marker and displays the
same step, phase, and success result.

The schedule was incomplete because the task terminated on success before lower
and hold. This is expected under the current runtime termination contract; it
does not establish sustained holding or release onto a support surface. The
reported 1.0 success rate has denominator one and is not a robustness estimate.
No verification or recovery was active. This is initial native manipulation
evidence, not a result for the Prototype A research intervention.

Next acceptance check: keep controller code/settings unchanged at `bfd1446`, run
seeds 0 through 19 with a 360-step limit and rendering disabled, and retrieve
manifest/result/event logs. Repeating seed 0 checks agreement with the rendered
episode; the remaining seeds probe ordinary reset variation. This is candidate
baseline screening, not the final disturbance benchmark or held-out evaluation.

## Native 20-seed batch audit

The supplied `aether-cl-m1-evidence.tar.gz` archive contains both live and batch
manifests/results plus complete event logs. Both manifests record clean
`bfd144646187bb4985e5d6678320651e3b94b022`. Audited 4,042 batch action records,
20 resets/results, and 202 live actions. Seed 0's actions, observations, info,
decisions, and evaluator records match exactly between live and nonrendered runs.
No execution/cleanup errors were recorded; aggregates, step counts, distances,
phases, action shape/gripper schedule, and terminal records are consistent.

All 20 episodes reported environment success, but seed 8 started already inside
the goal tolerance (0.01482 m) and ended after four open-gripper approach steps
without grasping/lifting. The other 19 episodes grasped at step 102 and lifted
before success. This is a post-hoc subset description, not a changed benchmark
denominator. The batch episode execution times sum to 16.95 s excluding startup
and resets; rendering/browser pacing was disabled.

Eighteen reset grasp flags were true then false on the first action. Potential
stale reset/contact information requires validation before verifier use; it
does not enter the fixed policy. Seed 2's nearby goal also permits success after
only 0.01153 m lift. Current success does not establish release or sustained hold.

Accept this as nominal engineering baseline evidence, retain controller code and
settings, and address shared task/reset criteria and fresh verification evidence
before M2/comparison runs. Disturbance performance and verification/recovery
benefits remain untested. See the [complete audit and saved source records](docs/research/experiments/AETHER_CL_M1_Baseline_Screening.md).

---

# Experiment Template

## Experiment ID

Example: EXP-0001

## Date

YYYY-MM-DD

## Research Question

What are we trying to understand?

## Hypothesis

What do we expect?

## Background

Existing system, paper, or baseline.

## Method

Implementation and experimental approach.

## Environment

Hardware:

Software:

Dataset:

Simulation:

## Baseline

What are we comparing against?

## Metrics

How is success measured?

## Results

## Failure Analysis

What failed?
Why did it fail?

## Lessons Learned

## Next Direction
