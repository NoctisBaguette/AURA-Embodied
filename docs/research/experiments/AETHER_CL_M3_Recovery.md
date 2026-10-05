# AETHER-CL M3 Bounded Recovery Candidate

Date: 2026-10-05 (Asia/Shanghai)

Status: initial native behavior audited; original suite failed on a harness
FPS mismatch. Corrected native acceptance and paused live inspection remain
pending. This is Prototype A's next intervention, not full AETHER.

## Evidence motivating the intervention

The [audited frozen M2 screening](AETHER_CL_M2_Frozen_Screening.md) completed
120 episodes across 20 unique fresh seeds. Normal success was 20/20 per system;
shift/drop success was 0/20. Passive V1 identified all first failures with
two-step delay, but its action traces exactly matched the policy baseline.
Recovery must change action selection while retaining this comparison.

## Matched experiment

| System | Nominal policy | Verification | Recovery | Episode budget |
| --- | --- | --- | --- | --- |
| Baseline | Frozen FixedPickCube | Disabled | Disabled | 360 |
| V1 | Frozen FixedPickCube | Frozen StateVerifier | Disabled | 360 |
| V2 | Frozen FixedPickCube | Frozen StateVerifier | One bounded retry | 360 |

All use the same reset eligibility, held-cube lift/grasp/goal/static task,
CPU physics, and scripted 0.12 m relocations before steps 81 or 181. The
original `policies.py`, `verification.py`, `disturbances.py`, and `runtime.py`
remain byte-identical to M2 screening. A separate M3 runner adds action
selection and recovery evidence; tests compare its full passive traces to
frozen M2 execution and require unchanged V2 normal traces and pre-trigger
disturbed prefixes. The existing isolated process helper gains an optional
entry module, preserving its default M2 command/environment behavior.

## Controller contract

A confirmed `GRASP_FAILURE` or `OBJECT_LOST` in the preceding fresh verifier
verdict can trigger one attempt on the next action. Simulator reference
labels, contact flags, environment success flags, and disturbance identity
are never recovery-controller inputs. Retry targets are cached from the
current observed cube, goal, TCP, and robot base pose. Subsequent motion uses
the same FixedPickCube servo, including 0.012 m translation and 0.08 rad
rotation command bounds. Recovery changes target refresh and phase selection;
the nominal policy and its schedule remain fixed.

| Retry phase | Motion primitive | Maximum phase actions | Advance condition |
| --- | --- | ---: | --- |
| Retract/reopen | Approach servo, vertical clearance target | 35 | Arrival and aperture at least 0.06 m |
| Approach | Approach servo at cached current cube | 60 | Arrival |
| Descend | Descend servo | 35 | Arrival |
| Close | Close servo | 25 | At least 10 actions and three geometry candidates |
| Lift | Lift servo | 35 | Arrival, three candidates, at least 0.05 m attempt lift |
| Transport | Transport servo | 80 | Arrival; monitor attachment |
| Lower | Lower servo | 30 | Arrival; monitor attachment |
| Hold | Hold servo | 10 | Ten observations; final shared task scored separately |

Arrival uses TCP distance at most 0.02 m and orientation error at most 0.15 rad,
with at least three actions in a motion phase. Geometry candidates reuse the
frozen verifier's distance/aperture/persistence thresholds. They are proxy
observations, not proof of physical contact. Native M2 logs show approximately
25 steps for a 0.12 m lift; this motivates observed-arrival transitions rather
than a shorter fixed-clock retry. Phase timeouts are upper bounds, not a fixed
schedule whose durations must all elapse.

The attempt is capped at `min(230, remaining_episode_actions)`. A remaining
budget below 40 declines the attempt; 40 is an admission floor, not a claim
that recovery can finish in 40 actions. At the seed-0 drop diagnosis, the first
retry action is 184 and at most 177 actions remain. Budget exhaustion,
unreached phase targets, invalid state, goal change, failed grasp, or three
missing geometry candidates during transport/lower/hold abort the attempt.
Aborted/completed attempts repeat their last absolute command and never
restart the nominal transport sequence. This holds the selected command;
it is not a hardware emergency-stop interface.

Confirmed unsupported failure categories decline recovery and hold the last
command. `UNCERTAIN` does not initiate a retry; the nominal policy continues
while fresh observations and the verifier are collected. This first candidate
does not implement search, state-mismatch correction, or uncertainty recovery.

The global verifier and reference retain their original episode clocks and
first-failure records throughout recovery. Reopening can therefore legitimately
continue to report a missing grasp. Recovery's local grasp/lift gate prevents
transport without replacing or retuning the shared verifier. Final task scoring
requires fresh simulator grasp contact and five static goal observations.

## Evidence and cost

Each action logs observation, selected decision, reference, verifier, and
recovery state. Transition events record trigger/start/phase/abort/completion.
Attempt snapshots include cached target poses, candidate persistence, maximum
attempt lift, allocated/used action budget, and observed TCP path length.
Recovery success is final shared task success among attempted eligible
episodes; completing a retry sequence alone is not success. Action cost/path
include unsuccessful attempts and exclude subsequent command holding. Total
episode actions remain 360 for every eligible system. Incomplete or zero-attempt
rates are null; exclusions remain recorded without replacement.

## Native development and next live inspection

`python -m aether_cl.m3_acceptance` runs nine isolated seed-0 cells, retaining
identical captured startup environments, raw logs, errors, hashes, and an
exclusive evidence archive. Three baseline/V1 pairs and the normal V1/V2 pair
must have exact canonical traces and matching software/policy/task contracts.
V2 must share initial state and injection, preserve the nominal action/state
prefix, trigger from its first diagnosis, and respect its transport gate and
remaining action budget.

A passed development suite means valid matched evidence and controller
contracts. Shift/drop recovery success, timeout, or abort remains a measured
outcome. The first browser run then shows V2 shift recovery on the A100 using
port 8765; drop follows. Inspect returned logs before freezing parameters and
choosing fresh seeds for the larger paired evaluation. These are development
checks, not held-out recovery robustness results. No new packages are required.

Local validation covers 75 tests, including all previous M2 tests, frozen-source
hashes, passive/full-prefix equality, positive and failed retries, motion lag,
timeouts, lost attachment, evaluator-input poisoning, budget exhaustion,
exclusions, interruption/error reporting, isolated subprocess arguments, and
nine-cell hashed archives. Fixture success is not native physics validation.

The live display shows recovery state, action budget, controller phase, diagnosis,
and the separate shared task outcome. Browser access is read-only. A100 rendering
already works for M0-M2. Corrected M3 seed-0 acceptance is now complete and
audited; live results and fresh-seed recovery evaluation remain pending.


## First native suite: useful behavior, rejected configuration

The uploaded `aether-cl-m3-evidence.tar.gz`, SHA-256
`864497126cc991ca3d1af724c60436b79f14acbea73680149bd17a166a121727`,
contains nine clean `380648c` episodes and 3,240 actions. All 47 unique regular
members and 46 indexed size/hash records match. Action/decision, reference,
verifier, and recovery-state replay, independent task/metric calculations,
child stdout/results, four full paired traces, and disturbed V2 prefixes agree.
See the [native audit](evidence/AETHER_CL_M3_Native_Audit.json).

Normal baseline/V1/V2 all succeed. Shift/drop baseline/V1 fail; V2 succeeds
in both single-seed cases. Shift detects at 127, starts retry at 128, spends
170 of 230 allocated actions, and first satisfies the strict task at 287.
Drop detects at 183, starts at 184, spends 156 of 177 actions, and first
satisfies the task at 329. These are development cases, not robustness rates.

The original suite remains `failed`: every trial requests FPS 5 but records
10. The shared subprocess helper omitted `--fps`, exposing M3 CLI's different
default. No other configuration field differs. The nonrendered runner has no
FPS pacing, so these outcomes remain useful evidence, but exact configuration
matching is not waived. Fix the forwarded argument and rerun into a distinct
archive. This change does not alter policy, recovery, verifier, task, or physics.
The launch script used `set -e`; suite exit 2 prevented the viewer command
from running. The observed SSH connection-refused messages are consistent with
no HTTP listener, not a missed live episode.

M3 live now publishes the initial frame with `ready_to_start`, serves HTTP,
and waits for Enter in the server terminal before any task action. The browser
can remain on the preview indefinitely. Ctrl+C or EOF cancels the wait, releases
the worker, and closes the environment. After completion, the final frame stays
available until Ctrl+C. This is a presentation change, not policy feedback.

All 78 local tests pass. Added tests round-trip every configuration field through
the actual child parser with both default and nondefault FPS, require an explicit
preview release, and establish zero actions/environment cleanup when cancelled.
The original failed archive and its requested settings remain preserved.

## Corrected native acceptance: passed

The corrected `aether-cl-m3-evidence-fps-fixed.tar.gz` (SHA-256
`22871e65df0d946abb53382a86e4299d17ebbc028ce2505ee55758d1fdd182aa`,
1,202,382 bytes) records clean revision `2d1c063`. All 47 unique regular
members and 46 indexed size/hash records verify. All nine trial configurations
match exactly, including requested/recorded FPS 5. Every episode is eligible
and executes its full 360-action budget without execution/cleanup errors.

Recomputing all nine trial checks and four pair checks from the raw files
reproduces the suite's `passed` result. Replay of all 3,240 actions, decisions,
reference/verifier verdicts, and recovery snapshots agrees, with maximum action
error 2.98e-8 from float32 base-pose arithmetic. Independent task geometry,
stability and detection metrics agree. All nine canonical traces, verifier and
recovery sequences, and evaluations exactly reproduce the original failed
archive. Thus the FPS correction changes recorded configuration and evidence
acceptance, without changing the scientific behavior. The original rejected
archive and audit remain preserved. See the
[corrected raw audit](evidence/AETHER_CL_M3_Corrected_Native_Audit.json).

| Condition (seed 0) | Baseline | V1 verification | V2 verification + recovery |
| --- | --- | --- | --- |
| Normal | Success | Success | Success, no retry |
| Object shift | Failure | Failure | Success, 170/230 retry actions |
| Object drop | Failure | Failure | Success, 156/177 retry actions |

The two V2 retries begin at steps 128/184, immediately after the first confirmed
diagnoses at 127/183; strict task success first occurs at 287/329. Final success
requires contact grasp, lift, goal distance and static persistence; retry
completion alone does not qualify. All systems retain the same total episode
budget. Normal V2 remains exactly identical to V1, and disturbed V2 prefixes
remain identical through diagnosis.

This is a single-seed development check with privileged observations and
synthetic pose relocation. It establishes functioning bounded recovery in these
two cases, not a recovery robustness rate or physical disturbance realism.
This archive contains no rendered/live runs, so it cannot certify the preview
pause or browser behavior. Next inspect live shift/drop, then freeze recovery
parameters and preregister a fresh-seed paired evaluation before running it.

## Operator shift observation and frozen screening

The operator subsequently reports seeing the live shift run reacquire the cube,
grasp it and move it to the green goal. They noted slow staged motions and an
unnecessary initial empty grasp. This is recorded as an operator observation;
no live raw-log archive was supplied for this checkpoint. Camera perception,
physical force disturbances and policy optimization remain separate changes.

The next [frozen screening protocol](AETHER_CL_M3_Frozen_Screening.md) uses
fresh seeds 40–59 across all nine system/condition cells: 180 requested
episodes. It retains the accepted scientific files and shared budget, and
measures failures and aborts without imposing successful recovery as an
acceptance gate. Native screening results and rendered drop inspection remain
pending.
