# AETHER-CL M2 Passive Verification

Date: 2026-10-05 (Asia/Shanghai)

Status: M2 seed-0 native development acceptance is complete. Normal/shift/drop
outcomes, paired traces, and identical process-isolated startup environments
were audited. Frozen fresh-seed screening is prepared, with results pending.

## Purpose

Add explicit outcome checks to the fixed PickCube baseline and create controlled
failure cases. This increment supplies V1: verification with no recovery. The
policy file and all controller settings remain unchanged from M1. Actions cannot
depend on verification, simulator reference labels, or disturbance identity.
No policy learning, task planner, experience memory, or model training is added.

Passive verification alone cannot increase manipulation success under identical
actions and task rules. Its measured contribution is detection and diagnosis.
Recovery in M3 will provide the action intervention needed to test autonomy gains.
Prototype A remains the instrument for the 02 research hypothesis.

## Shared task contract

Baseline and V1 both opt into `--protocol m2` and use CPU physics, Panda,
privileged state observations, the same fixed controller, and a 360-action budget.
Intermediate environment `terminated` flags remain logged but do not end the M2
run; the configured time limit/full action budget does. M1 default behavior is
preserved for historical reproduction. No auto-reset wrapper is added.

| Rule | M2 value |
| --- | --- |
| Reset eligibility | initial cube-goal distance strictly above 0.025 m |
| Lift evidence | cube reached at least 0.05 m above its initial centre |
| Goal tolerance | 0.025 m |
| Grasp for task reference | fresh post-action simulator contact flag |
| Robot static threshold | Panda arm joint speed at most 0.2 in the environment reference |
| Final stability | five consecutive eligible, grasped, lifted, static goal observations |
| Release/support surface | not required; this remains a held-cube target task |
| Default budget | 360; M2 CLI rejects fewer than 325 actions |

Already-solved resets are recorded with zero actions and an exclusion reason.
They are not replaced with newly sampled seeds. `task_success_rate_at_end` uses
eligible episodes only; if all are excluded or the run is incomplete, it is null.
Old raw environment rates remain supplemental and may include excluded resets.
State `finished` means execution completion, not task success.

The rules were selected during development after inspecting M1 seeds 0–19.
Those seeds remain acceptance/calibration data; use new seeds (starting at 20)
for matched screening once native acceptance passes. This contract is stricter
than M1's proximity/static success and requires a fresh baseline run. Historical
M1 20/20 results are not a baseline comparison for M2. Final benchmark task
selection and physical pick-and-place release criteria remain separate work.

## Verifier observation boundary

The verifier caches reset cube/goal geometry only. It ignores reset grasp flags,
`extra.is_grasped`, all `info`, simulator-reference outputs, and disturbance names.
Fresh inputs are cube/goal/TCP poses, nine Panda joint positions/velocities, and
post-action step number. Joint feedback already belongs to simulator state; no
new sensor or dependency is required.

The grasp proxy combines cube-to-TCP distance at most 0.04 m with total gripper
aperture between 0.01 and 0.06 m during the close/lift sequence. Three consecutive
proxy observations plus 0.01 m lift establish observed attachment history. This
is a geometric proxy, not measured grasp force. It can disagree with real contact
and must be evaluated against the separate reference. Task success additionally
requires the shared 0.05 m lift, goal tolerance, arm static threshold, and five
consecutive fresh observations. Missing/invalid required verifier sensors and
repeated step numbers produce `UNCERTAIN`; skipped steps break persistence.
Invalid native task state or failed simulator mutation remains an execution error.

| Check | Earliest deadline/evidence | Diagnosis |
| --- | --- | --- |
| Grasp absent | close deadline, step 125 | GRASP_FAILURE |
| Attachment subsequently lost | after confirmed lifted attachment | OBJECT_LOST |
| Expected lift not demonstrated | lift deadline, step 170 | STATE_MISMATCH |
| Goal differs from reset expectation | observed goal geometry | STATE_MISMATCH |
| Target not reached | scheduled-sequence deadline, step 320 | TARGET_NOT_REACHED |
| Final stability/task condition missing | final action/time limit | STATE_MISMATCH, unless a more specific failure applies |
| No usable fresh verification observation | sensor/step checks | UNCERTAIN |

Physical failure diagnoses require three consecutive matching failures; the
final evaluation does not invent extra actions to wait for persistence. Output
contains status, expected outcome, evidence measurements, failure, and
`confidence: null`. Thresholds and input boundaries are in the manifest; no
calibrated probability is claimed. Temporal counters are confined to one episode
and are not learned experience or long-term memory.

## Controlled disturbances

| Condition | Before action | Pose intervention |
| --- | ---: | --- |
| none | — | no mutation |
| object_shift | 81 | add 0.12 m to world y while descending toward the cached cube position |
| object_drop | 181 | add 0.12 m to world y and return cube centre to its reset height after lifting |

Magnitude can be set from 0.02 to 0.2 m, but paired trials must use exactly the
same value. Both interventions are one-time cube pose relocations with preserved
orientation and zero linear/angular velocity. They are synthetic disturbances,
not calibrated push/force models. The actor is changed after action computation
and before the physics step, so action selection cannot see privileged injection
metadata. The fixed policy would ignore later cube poses in any event.

The CPU adapter was checked against the installed ManiSkill 3.0.1 wheel's
`actor.py`, `base.py`, and `pose.py`: `cube.set_pose(Pose.create_from_pq(...))`
and the dynamic actor velocity setters. Backend exceptions propagate through
normal error/cleanup logging. Unsupported GPU physics does not silently skip
the intervention. The current runtime explicitly builds CPU physics.

The disturbance event records planned step, axis/magnitude, before/after pose,
and zeroing of velocities. It does not serve as a failure ground-truth label:
an applied disturbance may have no effect or may be naturally overcome. Fresh
simulator contact/geometry and checkpoint state supply the separate reference.

## Evaluation and logs

Per-action records retain policy actions/decisions, observations, raw environment
flags, separate reference task/failure outputs, and verifier outputs. Episode
records include task success, exclusions, first reference/detected failure, final
verification, achieved lift, and whether the disturbance fired. Latency is
reported only when the first reference and detected physical failure labels
match and detection does not precede reference onset.

Step-level metrics record TP/FP/FN/TN, uncertainty on reference-negative steps,
label confusion counts, detection precision/recall, diagnosis agreement when
failure is detected, and observation coverage. Uncertain positive steps are
missed detections; uncertain negative steps are not silently called true
negatives. Zero denominators and incomplete-run rates are null. These are
privileged-state simulator-reference agreement measures; shared geometric
inputs limit independence and they do not establish visual-perception accuracy.
Episode-level and time-of-first-failure measures should accompany the dense
counts rather than allowing long failure episodes to dominate interpretation.

Schema version 3 distinguishes these records. Browser fields display raw
environment success separately from M2 task success, verification status,
diagnosis, and scheduled/applied disturbance. A detected failure does not stop
or redirect the arm in V1. Keep a visible trial alongside later batch evaluation.

## Validation and native acceptance

All 40 local tests passed. They cover legacy runtime behavior, pose/action
conventions, verifier freshness/input exclusions, persistence, missing sensors,
all failure labels, task/reset denominators, full-budget execution, partial-run
rates, intervention timing/storage, and error cleanup. In state-flow fixtures,
baseline/V1 actions and observations match under normal/shift/drop conditions;
shift and drop respectively diagnose grasp failure and object loss, with a
two-step persistence delay. Fixtures do not model native contacts or physics.
CLI help, compilation, and JavaScript status-update checks passed.

The verifier was replayed over all 4,038 post-action observations from the 19
eligible M1 normal episodes, producing no failure or uncertainty alarms. Seed 8
was excluded by geometry. See the [replay records](evidence/AETHER_CL_M2_M1_Observation_Replay.json).
All old prefixes ended before five stable goal observations or the full M2
budget; their verdicts stayed pending. This checks compatibility with observed
normal prefixes and does not validate native M2 success or failure detection.
Thresholds used development observations, so this is not held-out validation.

The first user-reported native A100 V1 object-shift trial completed on seed 0:
`runs/m2-v1-live/20261005T020329Z-d194299a`. The supplied
[viewer status](evidence/AETHER_CL_M2_seed0_shift_viewer_status.json) and matching
final browser screenshot show 360 actions, no task success or achieved lift,
an empty gripper, and a final cube-goal distance of 0.32238 m. The separate
reference first reported `GRASP_FAILURE` at step 125; the verifier confirmed it
at step 127, consistent with three-observation persistence. V1 continued its
unchanged schedule through transport/hold because recovery is inactive.

Dense counts were TP 234, FP 0, FN 2, TN 124, with no uncertain observations.
The two missed frames precede confirmation. These are correlated frames from
one failure episode, not 234 independent tests or evidence of general 99%
detection accuracy. The result supports this native shifted-grasp detection
case; normal full-horizon success, object-loss detection, and matched baseline/V1
native acceptance were still pending at initial receipt. The run manifest and
raw events had not yet been retrieved, so revision, exact injection trajectory,
and contact motion had not been independently audited. The later native audit
below resolves those checks against raw logs.

The user observed a sudden sideways jump and possible finger contact. The
configured `object_shift` deliberately relocates the cube by 0.12 m before
action 81; that discontinuity is not a physical push. The final screenshot
cannot establish whether contact caused additional movement. This trial must
be described as synthetic state perturbation, not realistic disturbance
physics. A continuous force/contact disturbance needs a separately specified
and logged condition with matched baseline/V1 runs.

The initial next step was to retrieve the live manifest/events and accept
normal/shift/drop baseline/V1 pairs under the same task rules. The subsequent
audit below records those findings and the remaining corrected-runner rerun.
No wheel, environment, driver, or 4090 change is required for this increment.
The [acceptance runner](AETHER_CL_M2_Acceptance.md) automates these six development
trials, paired trace checks, and evidence archiving without changing any M2
policy/runtime/verifier/intervention code. Its first eight additional tests
brought the local suite to 48; the subsequent process-isolation correction and
native results are recorded below.

After acceptance, run matched seed-20+ batches and freeze settings/budgets before
M3 rule-based recovery. Results and limitations return to 02 after Prototype A;
motion-policy optimization remains a separate experiment from the verification/
recovery intervention.

## Native raw-log audit update

The uploaded six-cell archive and earlier rendered run were audited: all 23
indexed file hashes, seven clean revision manifests, and 2,520 action records
were checked. Normal baseline/V1 both succeed; shifted grasps fail with V1
confirmation at 127 versus reference 125; dropped objects fail with V1
confirmation at 183 versus reference 181. All three canonical paired traces
match exactly. The rendered shift run matches the nonrendered V1 trace and all
360 verdicts. The prior viewer status matches its raw result. The cube's maximum
movement after the scripted shift was 1.262 micrometres, supporting relocation
as the explanation for the observed jump in this recorded trial.

The original suite nevertheless reports `failed`: only the normal pair's software
comparison fails because OpenCV prepended its bundled library path after the
first manifest. The runner reused one process. Do not relabel that original
result. The corrected runner uses fresh interpreters with identical captured
startup environments, preserves stdout/stderr, and keeps equality strict.
At correction time all 52 local tests passed and native rerun was pending;
the completion update follows below. See the
[screening report](AETHER_CL_M2_Native_Screening.md) and
[audit records](evidence/AETHER_CL_M2_Native_Audit.json). These seed-0 development
checks do not establish held-out robustness or perception accuracy.

## Isolated acceptance completion

The process-isolated rerun on clean `3e07c58` passes all six trial checks and all
three pair checks, including strict software equality. All 35 indexed hashes
and seven episodes/2,520 actions (including the prior live case) were audited.
All six child stdout results match their raw results; no Python tracebacks
appear in stderr. Pair trace hashes reproduce the original suite exactly.
The original failed archive remains unchanged. See the
[isolated audit](evidence/AETHER_CL_M2_Isolated_Audit.json).

Native seed-0 acceptance is complete. The next [frozen screening](AETHER_CL_M2_Frozen_Screening.md)
uses seeds 20-39 and measures outcomes without requiring seed-0 performance.
The policy, verifier, runtime, disturbance implementation, thresholds, and task
budget remain fixed. Screening integrity checks and CLI support bring local
validation to 58 tests; target-server screening remains pending.
