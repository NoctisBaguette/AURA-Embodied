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

# EXP-0011 Native M3 Pairing Failure and Episode Isolation

Date: 2026-10-05 (Asia/Shanghai)

Audit the original seed-40–59 archive, SHA-256
`c8c73ef11f91c9ea55d519701660c89456b55cbd5fc1e283fbd5fa2a1257fb74`:
all 47 indexed hashes, 180 original resets/171 eligible episodes, and 61,560
actions verify on clean `3284b504`. Seed 58 is excluded identically in each
cell, with zero actions. Policy/recovery replay, reference/verifier/metric
replay and individual outcomes agree. Normal reports 19/19 success per system;
shift/drop report 0/19 baseline/V1 and 19/19 V2. All passive pairs match.
These disturbed outcomes are not accepted paired recovery evidence.

The native comparison remains failed. Reused reset observation grasp flags
differ for seeds 41–59 after previous recovery. Drop seeds 48, 50, 54 and 59
also physically differ before recovery, beginning at steps 101/102. The exact
internal engine mechanism is not established. Do not waive reset fields or
numeric differences. Preserve the original failed archive/protocol and
implement a separate correction: fresh Python interpreter/simulator for every
condition/system/seed, 180 one-episode children, unchanged settings and nine
frozen source hashes. Strict reset/prefix checks remain. The original selected
seeds are now seen, so this is correction replication, not a new held-out sample.

The supplied live drop screenshot shows finished step 360, task success,
156/177 retry actions and 1.4 cm displayed goal distance. Operator observes
slow staged approach and raised transport. Fixed 60/40-step approach/descent
and 6 cm goal clearance explain that behavior; 2 cm recovery arrival/2.5 cm
task tolerances permit the final offset. Marker size follows the upstream
5 cm sphere diameter beside a 4 cm cube. Future movement/precision changes
need separate frozen comparisons.

Local regressions reproduce stale reset carryover in the reused fixture,
retain strict rejection, and run all 180 independent one-episode calls with
the same captured startup environment, original seed order, exclusion 58,
60 passive pairs, 60 causal pairs, exclusive archives and all file hashes.
Failure/interruption retains partial evidence and null incomplete rates.
Corrected native execution remains pending. See the
[audit and correction](docs/research/experiments/AETHER_CL_M3_Isolated_Screening.md).

---

# EXP-0012 — M3 Isolated Native Replication Accepted

Date: 2026-10-05 (Asia/Shanghai)

The new isolated seed-40–59 archive is fully audited on clean `c4a9b304`.
SHA-256: `87d1ada67b827e6a6c8b5b074d0654fbf3b03176d62c7b01714bd05584cc1421`.
All 902 indexed hashes, 180 selected resets, 171 eligible episodes and
61,560 actions verify. Seed 58 stays excluded with zero actions in all nine
cells. Raw native episode indices remain zero; no data is rewritten or seed
resampled. All 180 native trial contracts, 60 passive full traces and 60
recovery reset/causal-prefix/injection pairs pass without comparison waivers.
The nine original first-seed traces and verifier/recovery sequences reproduce
exactly. Policies, task, verifier, recovery, disturbance and budget remain frozen.

| Condition | Baseline success | Passive V1 success | Recovery V2 success |
| --- | --- | --- | --- |
| Normal | 19/19 | 19/19 | 19/19 |
| Shift 0.12 m | 0/19 | 0/19 | 19/19 |
| Drop + shift 0.12 m | 0/19 | 0/19 | 19/19 |

V2 rescues all 19 matched failures in each disturbed condition without normal
regressions or normal retries. All first disturbed diagnoses retain two-step
latency and the correct first label. Mean attempt costs are 155.84 actions /
0.66289 m TCP path for shift, 137.16 / 0.56263 m for drop. Normal conditional
recovery rates/costs remain null. All raw action, diagnosis, task stability,
recovery gate/budget/snapshot/cost and aggregate metric replay checks pass.
Explicit ordered binary64 accumulation exactly reproduces the native Python
3.10 path mean; the audit host Python 3.12 builtin sum differs by one ULP for
one cell, without any per-episode data or strict pair tolerance change.

This fixes experimental comparability through fresh per-episode native
processes. The internal engine-history mechanism remains unproven. The
original failed archive/protocol stay rejected and preserved. These are the
same original selected seeds, now observed, not a new independent held-out
sample. Result scope: one privileged-state held-cube task and synthetic
relocations, not release/support placement, physical-force robustness or
camera perception. M3 is accepted within this scope; Prototype A remains open.

Final recovery goal-distance medians are 1.201 cm (shift) and 1.375 cm (drop),
versus 0.0498 cm nominal; current success does not establish fine precision.
Next preregister a magnitude robustness curve on new seeds with the current
controller still fixed. Later motion/precision variants need separate evidence.
The existing 92 local tests remain valid; this update changes only evidence
and documentation. No new server execution is requested.

See the [accepted result and limitations](docs/research/experiments/AETHER_CL_M3_Isolated_Screening.md#corrected-native-results)
and [machine audit](docs/research/experiments/evidence/AETHER_CL_M3_Isolated_Screening_Audit.json).

---

# EXP-0013 — M4 Magnitude Robustness Preregistered

Date: 2026-10-05 (Asia/Shanghai)

Status: prepared; native execution/results pending.

After the accepted M3 isolation replication, freeze a new magnitude curve
without changing the controller, verifier, physics, task scoring or budgets.
Preselected seeds 60–79 are new to native evaluation. Normal control and
2/4/8/12/20 cm shift/drop points give 660 requested one-episode children,
33 cells, 220 passive pairs, 220 causal recovery pairs and 200 normal-baseline
pre-injection controls. The existing 2–20 cm runtime validation stays intact.
Drop changes height as well as horizontal position; normal is a separate
no-injection control, not a zero-magnitude drop.

Every trial launches a fresh interpreter/simulator using the accepted M3 CLI.
Ten accepted source hashes, the new runner hash and exact committed protocols
are guarded before output/launch and each new trial. Full reset/prefix checks
are retained. The new cross-magnitude check requires baseline resets and
pre-injection trajectories to match each seed's normal control exactly.
All systems share the same preselected seeds; frames/conditions are correlated.

The parent writes raw trial manifests/logs/results, checkpoint file hashes,
cell/reference-agreement metrics, paired rescues/regressions and curve.csv.
Failures, aborts, unsupported diagnoses, exclusions and zero attempts stay
measured; incomplete or invalid comparison curve estimates remain null.
Graceful pauses make new exclusive partial archives. Continuation replays
recorded checks, verifies hashes/protocol/software/startup environment and
continues unstarted slots only, retaining all failures. An OS-held study lock
prevents competing writers. Final and partial archives remain separate.
Long server runs use nohup so SSH disconnection does not terminate the batch.

All 98 local tests pass, including the 660-slot continuation/archive fixture,
strict small/large-magnitude runtime pairs, control-prefix tamper rejection,
source/protocol/environment/raw-hash guards, competing-writer rejection and
dense metric aggregation with uncertainty. Python 3.10 syntax, CLI help and
documentation links verify. Fixture results do not establish native physics.
Validation is recorded in the [M4 protocol and implementation note](docs/research/experiments/AETHER_CL_M4_Robustness.md).
No new native result or robustness claim is made. Continue using the A100;
no packages/4090 are required. Live observation remains a separate paused-viewer
launch after selecting useful cases from the audited curve. Precision/speed
changes or richer perception/physics tasks require subsequent protocols.

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


# EXP-0014 — M4 Native Magnitude Robustness Audited

Date: 2026-10-05 (UTC)

Status: accepted finite native evidence; Prototype A remains in progress.

The preregistered seed-60–79 archive from clean source
`67a44d13b5363b615b5214ff543c34224e6af745` passes independent replay.
Archive SHA-256:
`a183e1357d6aba771fa193ae358dbcd1af30d11325eb3898ec4e93cf2a0f0bbd`.
All 3,304 indexed files, 660 trials, 237,600 actions, 220 passive pairs,
220 recovery pairs and 200 normal pre-injection controls validate. Aggregate
JSON and CSV match exactly; strict tolerances, source and scoring are unchanged.
All 660 selected episodes are eligible; there are no exclusions.

Normal and 2 cm shift succeed 20/20 per system without retries. Baseline/V1
have 0/20 success at shifts 4/8/12/20 cm and every 2/4/8/12/20 cm drop. V2 succeeds
20/20 at every point: 180 paired rescues, 40 both-success pairs, no regressions.
Retry action/path costs rise with magnitude. This does not locate an eventual
final-task failure threshold or demonstrate real-force/camera robustness.

Of 180 attempted retries, 178 finish their phases and two budget-abort.
At 20 cm drop seeds 69/76, shared task success begins at steps 352/353,
recovery hold begins at 353/354, and abort occurs at step 360. They meet the
task before their ten-action hold phase exhausts the remaining 177 actions.
Final task success and controller completion are separately recorded; no
post-deadline success or silently redefined outcome is counted. All attempted
costs, including both aborts, remain included.

First detected retry failures retain two-step latency and the expected
GRASP_FAILURE/OBJECT_LOST labels. Dense later agreement remains reported
separately and shares privileged geometry with the reference. Median recovered
goal errors across retry cells are 1.11–1.34 cm, versus 0.459 mm normal.
The same 20 seeds are reused across conditions; frames and points are correlated.

See the [native result report and paused live commands](docs/research/experiments/AETHER_CL_M4_Robustness.md#audited-native-results),
[machine audit](docs/research/experiments/evidence/AETHER_CL_M4_Native_Audit.json),
and [robustness figure](docs/research/experiments/evidence/AETHER_CL_M4_Robustness.svg).
This publication changes documentation and derived evidence only. Future
motion/precision, release/support, physical disturbance and perception variants
need separate protocols. Findings return to 02; this is not AETHER v1.0.


# EXP-0015 — 06-01 Engineering Round Closed; Return to 02

Date: 2026-10-05 (Asia/Shanghai)

Status: current held-cube engineering round complete; return to 02 for research
review. Broader Prototype A scope remains open, particularly placement/release
and insertion. This closure does not waive the original handoff requirements.

The operator reports seeing the full live process following the M4 handoff.
This is qualitative observation; no additional raw live-log audit or numerical
measurement is claimed. Accepted M2/M3/M4 results and all rejected evidence
remain preserved. No policy, verifier, recovery, task definition, protocol,
source hash, tolerance or raw evidence changes accompany this closure.

The [return-to-02 handoff](docs/research/experiments/AETHER_CL_06_01_Return_to_02.md)
reconciles delivered components with original scope, provides accepted archive
and GitHub provenance, and returns the finite findings and remaining decisions.
The root README's obsolete runtime-pending statement is updated. Implementation
is on `06-01/aether-cl-m0`; PR #1 stays open, draft and unmerged. No additional
native run is needed to deliver this round's findings. Next scope belongs to 02;
no Prototype B/C/D, 02W, memory, world model or motion variant is activated here.


# EXP-0016 — 02 Reopens 06-01 for M5 Verification-Gating Attribution

Date: 2026-10-05 (Asia/Shanghai)

Authority: DEC-0003 and the 02 review at
`3c919ecca401a73fe04a676c019c33b8a85b440a`.
Status: implementation/preregistration prepared; native results pending.
The earlier closure was the M0–M4 engineering round, not Prototype A completion.

Add V3: one scheduled retry using the same recovery motion/observe methods,
target-refresh startup and limits, without constructing or consuming a verifier.
First retry actions are frozen at 128 (shift family) and 184 (drop family),
independent of magnitude, failure labels and current success. Both schedules
also run on corresponding normal controls. Invocation is ablated; local
attachment/arrival feedback inside the retry remains the same capability.
Baseline/V1/V2, nominal motion, scoring, disturbances, physics and accepted
comparison tolerances remain unchanged.

Fresh preselected seeds 80–99 across two six-point family curves and four
systems give 960 fresh-process trials, 48 cells and 1,160 strict paired/control
comparisons. First four slots may be paused/checked before background resume;
no observed outcome is used to retime or tune the frozen schedule. Comparison
failure is not a reason to relax tolerances or change the comparator after data.

Metrics separate V2/V3 final outcome, unnecessary attempts against matched
baseline success, regressions, paired costs including no-attempt zeros,
conditional costs, trigger timing, completion/abort state and final goal error.
Performance failures remain evidence; invalid/incomplete comparisons produce
null estimates. Software/environment/raw replay and archive preservation remain
mandatory. Local fixtures do not provide native M5 results.

See the [M5 frozen plan](docs/research/experiments/AETHER_CL_M5_Attribution.md)
and [machine protocol](docs/research/experiments/evidence/AETHER_CL_M5_Attribution_Protocol.json).
After native M5 evidence is uploaded and audited, return to 02 again before
further work. No placement, insertion, visual verification, physical-force
protocol, motion optimization, memory, world model, Prototype B/C/D or 02W
is activated in this round. PR #1 remains draft/unmerged.


M5 validation: all 105 local tests pass in 203.496 seconds, including seven
M5 tests. Python 3.10 syntax, CLI help and documentation links pass. All
previous scientific source blobs/protocols and 02 decision/review files remain
unchanged. No native M5 outcome has been observed; publication precedes data.


# EXP-0017 — M5 Native Attribution Audit and Return to 02

Date: 2026-10-06 (Asia/Shanghai).

Native implementation: `12a9d2626636206e1687fa24df507bbadbc2a37d`, clean.
Archive SHA-256:
`a14d7542fcff8f025f13c72fb209f9c13e8666af0d8571855e3ad7035f6bbcab`.
All 960 selected trials are eligible; all 4,804 indexed file hashes, 345,600
actions, controller/reference/verifier replay, 1,160 strict comparisons and
exact native aggregate JSON/CSV reproduction pass independent archive audit.
No outcome was replaced and no strict tolerance was relaxed.

V2 avoids all 60 unnecessary V3 retries in baseline-success controls. Normal
shift and 2 cm shift retries add cost/error while retaining 20/20 success.
Normal drop-family V3 opens the valid held grasp, loses the cube and fails
20/20; V2 succeeds 20/20 without retry. This supports bounded selective
invocation value. All 180 aligned disturbed V2/V3 pairs have identical full
physical traces, cost and outcomes, with 177 successes. General verification
necessity is not established by these phase-aware aligned schedules.

Fresh 20 cm cases fail for shift seed 99 (transport timeout) and drop seeds
87/99 (remaining budget). Five other drop attempts per system abort at step
360 but meet the shared task by that observation; seeds 88/92 first succeed
exactly at step 360. No post-budget success is counted. All failures and costs
remain in denominators. V2 has 172 completed/eight aborted attempts; V3 has
212 completed/28 aborted, including 20 healthy-control regressions.

The unrendered archive contains no video/images. Its inherited unused
render_device cuda:1 is retained; effective render backend is none and
physics is CPU. Separate live demonstration commands reuse existing runtimes
and preview server, wait for Enter and retain the final image. These are new
rendered runs, not archive playback or replacement measured outcomes.

See [M5 results](docs/research/experiments/AETHER_CL_M5_Attribution.md#audited-native-results),
[machine audit](docs/research/experiments/evidence/AETHER_CL_M5_Native_Audit.json),
[live commands](docs/research/experiments/AETHER_CL_M5_Live_Demonstrations.md) and
[return to 02](docs/research/experiments/AETHER_CL_M5_Return_to_02.md).
M5's engineering round is complete; Prototype A remains scientifically open.
Return to 02 before further implementation. PR #1 stays draft/unmerged;
no new task, motion variant, sensor/force protocol, B/C/D or 02W is activated.


# EXP-0018 — M6 Support Placement/Release Implementation and Preregistration

Date: 2026-10-06 (Asia/Shanghai).

Authority: 02 accepts M5 and authorizes M6 only under DEC-0004 and
`AETHER_CL_M5_02_Research_Review_v0.1.md` at
`03b9b2dc77c33dc1aa47edd67dcb20238ad8b0bb`. The earlier return boundary
is superseded for this bounded new round; Prototype A remains open.

M6 extends the Panda/cube task to real release and independent table support.
Goal XY is retained, Z projected onto table support. New matched Baseline/V1/V2
nominal behavior adds release/retraction; the original motion servo and all
M0–M5 scientific execution modules/protocols stay unchanged. V3 is absent.
Shared success requires historical contact grasp/lift, current non-grasp/open
gripper, designated table contact and geometry, 2.5 cm horizontal tolerance,
retraction and five fresh stable observations. The environment success flag
does not score the task.

At step 296, attempt a one-time synthetic positive-Y displacement following
release. If release preconditions fail, preserve the missed injection and
episode without exclusion/replacement. One bounded recovery episode may
regrasp, replace, release and retract; no second retry after abort/completion.

Fresh preselected seeds 100–119 cover normal plus 1/4/8/12/20 cm shifts:
360 isolated native children, 18 cells and an identical 800-action global
budget. The first 18 normal/easy/8 cm slots on seeds 100/101 stay in the dataset
and pause for preregistered commissioning, with no V2 success requirement.
Then continue only the remaining 342. Exact physical pairing requires 120
passive pairs, 120 causal recovery pairs and 100 pre-injection controls.

Owned source/protocol and unchanged M0–M5 guards, installed upstream source
identity, normalized startup environment, raw hashes, controller/state/metric
replay, a study lock and immutable partial archives protect execution.
All failed costs remain included; invalid/incomplete comparisons yield null
scientific effects. The dedicated M6 viewer has correct names, a paused
initial frame and retained final image; live demonstrations are separate.

See [M6 specification](docs/research/experiments/AETHER_CL_M6_Placement.md)
and [machine preregistration](docs/research/experiments/evidence/AETHER_CL_M6_Placement_Protocol.json).
All 121 local tests passed in 211.364 seconds, including 16 M6 tests. The
targeted M6 suite separately passed in 22.705 seconds. Python 3.10 parsing,
CLI help, documentation links and frozen source/protocol agreement passed.
Native commissioning, full execution and independent archive audit remain
pending. Return to 02 after M6 audit. No insertion, force disturbance, sensor
verifier, memory/world model, B/C/D or 02W is authorized by this round.

# EXP-0019 — M6 Native Parent-Report Serialization Failure and Bounded Repair

Date: 2026-10-06 (Asia/Shanghai).

The uploaded server screenshot shows all 16 M6 tests passing in 23.139 seconds,
then normal / seed 100 / Baseline completing with evidence passed, eligible,
task success true. These are provisional outputs awaiting raw archive audit.
Parent `suite.json` persistence then fails because an audit check is a NumPy
`bool_`. SSH closes under the supplied `set -e` execution block. The first raw
child remains complete; the persisted parent slot remains running.

A separate external reporting launcher converts parent JSON values using the
existing converter and adopts only that finished first slot after full replay.
It exclusively backs up original study bytes and records hashes/provenance.
The scientific checkout remains clean at `7059c713d3b36e3f032aab8d1f87662ed6fdab91`;
all scientific modules and the frozen protocol are unchanged. The child is
never rerun; first-18 commissioning continues only the next 17 slots, then
uses the original viability gate. All ordinary continuation guards remain.

Three focused regressions reproduce NumPy-boolean failure and check preserved
raw/backup bytes, distinct child calls, commissioning, rejection of incomplete
or tampered evidence, identity drift and duplicate repair, and retained NaN
rejection. See [reporting repair](docs/research/experiments/AETHER_CL_M6_Reporting_Repair.md).
Native continuation and independent audit remain pending; scope is still M6.
