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

# EXP-0003 Passive Verification Preparation

Date: 2026-10-05 (Asia/Shanghai)

M2 adds passive state verification with grasp/lift/goal checks and the initial
failure categories, while retaining the exact M1 policy file/settings. Baseline
and V1 share a revised task contract: explicitly exclude already-solved starts,
run the full action budget despite intermediate environment success, and require
lifted grasp plus five static goal observations at the end. This requires fresh
M2 baseline measurements; M1's environment success rate is historical evidence.

Controlled one-time cube shift/drop interventions and their pose/velocity changes
are logged independently from fresh simulator failure references. Verifier inputs
are geometry/joint state only; reset contact flags, evaluator info, disturbance
identity, and reference labels are excluded. No action intervention or recovery
is added. Passive V1 cannot increase success under identical actions/task rules.

Forty local tests passed, including baseline/V1 action equality under all three
conditions, observation freshness, diagnosis/persistence, task denominators,
full-horizon/partial-run behavior, and simulator-error cleanup. CLI, compilation,
and JavaScript update checks passed. Replay of 4,038 eligible M1 normal-state
observations produced no failure/uncertainty alarms, while seed 8 was excluded.
Those old prefixes cannot validate the new full-horizon task contract, and
fixtures do not simulate native contacts. Matched native M2 acceptance remains
pending.

First native V1 shift evidence supplied by the user: seed 0, run
`runs/m2-v1-live/20261005T020329Z-d194299a`, 360 actions, no lift/task success,
final cube-goal distance 0.32238 m. The reference first labeled `GRASP_FAILURE`
at step 125 and V1 confirmed at 127; TP 234, FP 0, FN 2, TN 124 are dense
observations of this single episode. The screenshot agrees with the final
status: empty gripper, cube on the table, diagnosis displayed, unchanged
schedule completed. This supports native detection in this case, not overall
precision/recall or robustness claims. Raw manifest/events are not yet audited.

The user's realism concern identifies an important boundary: `object_shift`
is a scripted 0.12 m pose relocation before action 81, with velocities zeroed.
Its discontinuity is synthetic fault injection, not a calibrated physical
push. Possible additional finger-contact motion cannot be resolved from final
status/screenshot alone. Preserve this condition for controlled attribution;
any continuous force/contact disturbance must be defined and evaluated as a
separate condition. V1 continuing empty-handed is expected because its
verifier cannot alter actions; recovery remains M3.

See [the M2 protocol](docs/research/experiments/AETHER_CL_M2_Verification.md) for
input boundaries, task rules, disturbance timing, metrics, and evidence limits.

---

# EXP-0004 M2 Native Acceptance Harness

Date: 2026-10-05 (Asia/Shanghai)

Prepared a bounded six-cell native acceptance runner: seed 0, normal/shift/drop,
baseline/V1, 360 actions each, no rendering. The underlying policy, verifier,
runtime, thresholds, and disturbance code are unchanged. This is development
acceptance, not a held-out benchmark or a robustness result.

Checks require complete eligible episodes, expected task/failure outcomes,
logged intervention timing/pose changes, clean revision evidence, and exact
paired action/observation/reference traces with matching software, policy, and
task rules. Differences are reported with the first differing field/step.
Reset `info` is omitted; the full reset observation remains compared. The
verifier ignores reset contact flags from either location.
Failed/interrupted trials retain their available raw logs; exclusions cannot
pass and are not resampled. The archive records content hashes and can include
the earlier rendered shift run for independent audit.

All 48 local tests passed, including eight acceptance checks for trace drift,
incorrect outcomes, execution errors, interruption, exclusions, dirty revisions,
archive integrity, and missing evidence. Fixtures do not simulate native contact
physics. The six-cell native results and prior-live raw-log audit remain pending.
See [the acceptance procedure](docs/research/experiments/AETHER_CL_M2_Acceptance.md).

---

# EXP-0005 M2 Native Audit and Trial Process Isolation

Date: 2026-10-05 (Asia/Shanghai)

Audited `aether-cl-m2-evidence.tar.gz` (SHA-256
`d157a2e11268a170515e4f5f36b6be5f8080a001e03b998aac500757d970e306`).
All 23 indexed hashes and 2,520 action records across six batch trials plus the
earlier live trial were checked. Six clean batch manifests record `3ae3099`;
the clean live manifest records `34ce567`. All native trials executed 360 steps
without exclusion or execution/cleanup error. Normal baseline/V1 succeed; shift
and drop fail with the expected V1 diagnoses, each confirmed two steps after
reference onset. All three paired traces match exactly, as does the live versus
nonrendered shift trajectory. Reference/verifier replay, geometry, stability,
policy replay, and dense metric counts match raw records.

The original suite state is still `failed`: its normal-pair software comparison
differs only in the recorded `LD_LIBRARY_PATH`. OpenCV's reviewed wheel loader
prepends a bundled path during import, while the runner reused the same process
for the next manifest. Do not rewrite the original outcome or relax the guard.

Corrected the acceptance runner to execute every native trial in a fresh Python
interpreter from the same suite-start environment. Child stdout/stderr are
archived, and Ctrl+C signals/joins the child before collection. Policy, verifier,
runtime, disturbances, packages, and settings are unchanged. All 52 local tests
passed, including four subprocess/environment regressions. Corrected native
rerun remains pending with a new archive filename. These are seed-0 development
checks, not held-out robustness results. See [the native audit report](docs/research/experiments/AETHER_CL_M2_Native_Screening.md).

---

# EXP-0006 M2 Acceptance Complete and Frozen Fresh-Seed Screening

Date: 2026-10-05 (Asia/Shanghai)

Audited `aether-cl-m2-evidence-isolated.tar.gz` (SHA-256
`6e6c513ab126db079730351917a09e2bb481291ce68ded930121892d27ebae6e`).
All 35 indexed file hashes, seven episodes/2,520 actions, six clean batch
manifests at `3e07c58`, and child stdout/results agree. All six native behavior
checks and three exact paired traces pass, including strict startup software
equality. Outcomes/detection steps and trace hashes reproduce the original
native suite. The original failed archive is preserved. M2 seed-0 development
acceptance is complete; broad robustness remains unmeasured.

Prepared a frozen screening mode for seeds 20-39: 20 episodes per cell,
normal/shift/drop baseline/V1, 360 actions per eligible episode, 0.12 m
interventions, 120 requested episodes and 20 unique reset seeds. Four frozen
source-file hashes and settings are preregistered. No policy, verifier, runtime,
disturbance, or threshold changes accompany screening. Exclusions are retained
without replacement. Performance is measured rather than forced to match
seed-0 outcomes; only completeness, denominators, and paired evidence are gated.

Clarified comparator metadata: reset `info` is omitted, while complete reset
observations (including raw `extra.is_grasped`) are compared. The old generic
metadata label was imprecise; canonical traces and verifier inputs are unchanged.
All 58 local tests passed, including frozen seed coverage, natural task failure,
exclusions, denominator errors, and metadata boundaries. Fresh native screening
results are pending before M3 recovery. See [the frozen plan](docs/research/experiments/AETHER_CL_M2_Frozen_Screening.md).

---

# EXP-0007 Fresh-Seed M2 Results and M3 Recovery Candidate

Date: 2026-10-05 (Asia/Shanghai)

Audited all 120 native episodes/43,200 actions from the frozen seeds 20-39
batch on clean revision `472dfbaf`. Archive SHA-256:
`182d9728cea439b84e6f7517a7dd829db91fc7687f940f00c998d867b8f16f16`.
All 31 indexed hashes, frozen sources, raw reference/verifier replay, episode
summaries, and exact paired traces pass. Normal final task success is 20/20
for each system; shift and drop are 0/20 for each. V1 diagnoses all 20 grasp
failures and all 20 object losses with two-step first-detection latency and
no false alarms or uncertainty. Drop seed 33's temporary raw environment
success never satisfies the strict task. See [the results](docs/research/experiments/AETHER_CL_M2_Frozen_Screening.md).

This confirms passive verification identifies the chosen disturbances but
cannot improve autonomy without an action intervention. Prepared M3 V2 with
one observed-state retry: reopen/retract, approach current cube, descend,
close, lift, transport, lower, hold. Motion primitives and nominal targets are
unchanged; retry targets are cached at the trigger. Arrival and fresh geometry
candidate evidence advance retry phases, each with a timeout. Confirmed
candidate persistence and 0.05 m attempt lift gate transport. Failure stops
retry actions and repeats the last absolute command, without resuming nominal
transport. The remaining episode budget caps the attempt; all systems retain
360 steps. Reference contact truth and disturbance identity do not trigger
recovery. UNCERTAIN observations do not trigger a retry; two confirmed failure
categories are supported initially.

All 75 local tests passed. A separate M3 runner preserves all four frozen M2 source files. Matched normal
traces and disturbed prefixes are tested against frozen execution. Nine
process-isolated seed-0 development cells archive successes, aborted retries,
errors, and action costs. Passing the evidence checks does not require disturbed
recovery to succeed. Native M3 physics and browser behavior remain untested at
publication; the next checkpoint is the server development suite and live V2
shift/drop inspection. See [the recovery protocol](docs/research/experiments/AETHER_CL_M3_Recovery.md).

---

# EXP-0008 Native M3 Audit, FPS Forwarding, and Live Preview Pause

Date: 2026-10-05 (Asia/Shanghai)

Audited the original failed native M3 archive (SHA-256
`864497126cc991ca3d1af724c60436b79f14acbea73680149bd17a166a121727`):
all 46 indexed hashes, nine clean `380648c` episodes/3,240 actions, raw policy
and recovery replay, task/verifier/reference agreement, four exact paired
traces, and unchanged disturbed prefixes pass. Normal succeeds for all three
systems; shift/drop fail for baseline/V1 and succeed for V2. V2 uses 170/230
allocated retry actions after shift and 156/177 after drop. This is seed-0
native development evidence, not held-out recovery robustness.

Every trial fails only `config_matches`: the parent requested FPS 5 and the
child recorded its CLI default 10. The process helper omitted that argument.
Nonrendered trials have no FPS pacing, but strict matching must remain. The
original failed suite/archive is preserved; forward FPS explicitly and rerun
to a new archive. No policy, recovery, verifier, task, physics, or frozen M2
source changes accompany this correction.

Because the suite returned exit 2 under `set -e`, the live viewer never started.
M3 live now serves an initial rendered preview and waits for Enter before task
actions. Cancellation releases the worker and closes the environment; final
frames remain available after completion. All 78 local tests pass, including
actual child-parser full-config round-trips, explicit preview release, and
zero-action cancellation cleanup. Corrected native acceptance and live viewing
are the next checkpoints. See [the audit](docs/research/experiments/AETHER_CL_M3_Recovery.md).

---

# EXP-0009 Corrected Native M3 Acceptance

Date: 2026-10-05 (Asia/Shanghai)

The corrected archive `aether-cl-m3-evidence-fps-fixed.tar.gz` (SHA-256
`22871e65df0d946abb53382a86e4299d17ebbc028ce2505ee55758d1fdd182aa`)
passes all nine trial and four paired checks on clean `2d1c063`. All 46 indexed
hashes, exact configurations (FPS 5), nine eligible episodes/3,240 actions,
policy/recovery replay, reference/verifier agreement, task/metric calculations,
and raw stdout/results verify. Recomputed checks reproduce the suite result.
All nine original canonical traces, verdict/recovery sequences and evaluations
reproduce exactly: the forwarding correction changes metadata acceptance, not
the scientific behavior. The original failed archive remains preserved.

Normal succeeds for baseline/V1/V2; shifted/drop cases fail for baseline/V1 and
succeed for V2. Shift retry starts at 128, uses 170/230 allocated actions, and
first meets the strict task at 287. Drop starts at 184, uses 156/177, and first
meets it at 329. Normal V2 makes no retry, and disturbed prefixes remain equal
through diagnosis. Total episode budget is 360 for every system.

This completes native seed-0 M3 development acceptance, not held-out robustness.
The archive contains batch runs only; live browser inspection remains pending.
Next inspect live shift/drop, freeze parameters and preregister the fresh-seed
paired evaluation. See the
[protocol](docs/research/experiments/AETHER_CL_M3_Recovery.md) and
[raw audit](docs/research/experiments/evidence/AETHER_CL_M3_Corrected_Native_Audit.json).

---

# EXP-0010 Live Shift Observation and Frozen M3 Fresh-Seed Protocol

Date: 2026-10-05 (Asia/Shanghai)

The operator reports observing live shifted-cube reacquisition, regrasp and
goal transport, with slow staged movement and an initial empty grasp. This is
operator evidence; no new live raw-log archive was supplied. Preserve the
fixed nominal sequence for causal comparison. Five-FPS browser pacing is not
model reasoning latency; the present controller is rule based.

Freeze seeds 40–59 and all accepted settings before native execution: nine
baseline/V1/V2 × normal/shift/drop cells, 180 requested episodes, shared
360-action budgets and unchanged 0.12 m interventions. A new runner enforces
eight accepted source hashes and the committed protocol before output,
isolates cell processes, retains exclusions/failures/abort/uncertainty, replays
reference/verifier metrics and recovery costs, and checks full passive traces
and recovery causal prefixes. Paired episode counts include normal-condition
regressions. Conditional recovery success includes all attempted eligible
episodes; failed attempts remain in costs. All available evidence is archived
on failure/interruption, without replacing earlier archives.

Local validation: previous 78 tests plus ten screening regressions pass (87
full-suite tests and one subsequently added missing-TCP check). A 180-episode
fixture exercises the matrix and hashed archive. Final checks also accept all
nine existing native pilot cells and three causal pairs. Native fresh-seed
results and rendered drop inspection remain pending; no new policy or physics
claim follows from these fixtures. See the
[frozen protocol](docs/research/experiments/AETHER_CL_M3_Frozen_Screening.md).

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
