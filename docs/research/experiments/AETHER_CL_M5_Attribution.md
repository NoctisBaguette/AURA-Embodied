# AETHER-CL M5 — Verification-Gating Attribution

Date: 2026-10-05 (Asia/Shanghai)

Status: implementation and preregistration prepared; native execution pending.
06-01 is active for M5 only. Prototype A remains scientifically open.

Authority: [02 review](AETHER_CL_02_Research_Review_v0.1.md) and
[DEC-0003](../../../DECISION_LOG.md), accepted at
`3c919ecca401a73fe04a676c019c33b8a85b440a`. The earlier engineering handoff
closed the M0–M4 held-cube round; it did not establish Prototype A completion.
02 has now returned this same chat to implementation for M5.

## Research question and frozen constraints

Does explicit failure-gated recovery provide measurable value over the same
recovery capability invoked without verifier gating?

M4 established the combined intervention's benefit but lacked an ungated
retry control. M5 adds that control without redesigning motions or changing
physics, the reference task, tolerance, action budget, disturbance definitions,
V1/V2 behavior, recovery primitives or strict comparison tolerances.
Baseline/V1/V2 execute the original `aether_cl.m3` child and original source
files. V3 uses a separate child runtime with the same environment/scoring
functions and the existing inherited recovery motion/observation methods.

| System | Invocation | Verification | Recovery capability |
| --- | --- | --- | --- |
| Baseline | Frozen nominal schedule | Disabled | None |
| V1 | Frozen nominal schedule | Passive | None |
| V2 | Preceding confirmed failure | Frozen verifier | Existing one bounded retry |
| V3 | Preregistered elapsed-step checkpoint | Disabled | Same one bounded retry |

V3 is an experimental causal control, not an architecture recommendation.
Its retry still uses the inherited observed-arrival and attachment/lift gates.
We ablate the verifier **invocation gate**, not all feedback within recovery.

## Fairness and schedule

V3's controller accepts only the observation and step. Its family is explicit
preregistered experiment metadata. It accepts no verdict, classifier output,
magnitude, injection event, evaluator success or contact label. No verifier is
constructed in its child runtime. Privileged contact labels remain available
only for the unchanged reference scoring and audit.

The new subclass copies only V2's target-refresh/startup assignments and uses
`SCHEDULED` as provenance, not a fabricated failure verdict. It then invokes
the frozen superclass action path with an empty verdict and inherits its
observe method unchanged. Same-observation, same-start tests require identical
actions, decisions and all recovery state except the reason metadata. Native
aligned-trigger V2/V3 pairs must match their full physical trace exactly.

| Attribution family | V3 trigger boundary | First retry action | Remaining global actions | Attempt budget |
| --- | --- | --- | --- | --- |
| Shift | After step 127 | Step 128 | 233 | min(230, 233) = 230 |
| Drop | After step 183 | Step 184 | 177 | min(230, 177) = 177 |

Timings use already frozen M0–M4 phase clocks and old M4 first-confirmed failure
checkpoints. They are fixed before fresh native seeds 80–99 are observed.
The schedule is the same at every magnitude and its corresponding normal
control. It does not adapt to a new episode's failure timing. The first action
boundary is explicit; trigger-step metadata denotes the preceding observation.
If V2 naturally triggers earlier/later on a new seed, retain and measure that
case. Do not retime V3 to follow it. Unsupported V2 diagnoses, aborts and task
failures remain outcomes, not reasons to exclude/retry a selected seed.

On healthy controls, V3 may reopen an already valid grasp, incur cost, or fail.
That is the intended selective-gating contrast. Do not suppress the scheduled
attempt based on grasp/goal state or improve its targets after opening: that
would change the comparator. Both systems refresh once and use the same
recovery attachment gates, per-phase limits and final holding behavior.

## Frozen matrix

Fresh preselected seeds **80–99**, no adaptive replacement. Fixtures use
synthetic environments and do not observe native simulator resets.

| Family | Points | Systems | Selected native trials |
| --- | --- | --- | --- |
| Shift | Normal; 2/4/8/12/20 cm shift | Baseline/V1/V2/V3 | 480 |
| Drop | Normal; 2/4/8/12/20 cm drop | Baseline/V1/V2/V3 | 480 |

Total: **960 fresh one-episode children**, **48 cells**, at most **345,600
actions** before exclusions/errors. Two normal points are needed because
V3's family schedules differ. Those normal samples and repeated magnitudes
are correlated; there are 20 common seeds, not 960 independent scenes.
Normal keeps the unused 0.12 m config field but actual magnitude is null.
The no-injection control is not a zero-magnitude drop.

Order: shift normal then ascending magnitudes; drop normal then ascending
magnitudes; seed; baseline/V1/V2/V3. CPU physics, state_dict observation,
360 actions, unrendered/unpaced batch, recorded FPS 5 and process-local
GPU 1/cuda:0 are unchanged. Existing installed packages suffice.

The [machine protocol](evidence/AETHER_CL_M5_Attribution_Protocol.json) freezes
the matrix, timing, definitions and six new source hashes. M4/M3/M2 preflights
also guard all accepted execution modules/protocols. Guards run before output
and each native trial. A clean committed checkout and matching software/startup
contract are mandatory. Changing source, timing or protocol after observing
native results is not part of this experiment.

## Strict audits

Every completed child retains manifest, events, result and stdout/stderr;
the parent stores hashes of all its files. The unchanged checker verifies
shared reference/verification scoring, full budget, exclusions, injection
geometry/order, summaries, cost contracts and terminal semantics. M5 additionally
replays every nominal/recovery action, decision and snapshot, including V3's
clock, no-verifier contract and full scheduled attempt. Existing action replay
tolerance is 3e-7; strict physical pair checks remain exact.

The complete suite requires:

- 240 baseline/V1 full physical pairs using the existing checker.
- 240 V1/V2 reset/causal-prefix/injection pairs using the existing checker.
- 240 baseline/V3 full-reset and scheduled-prefix/injection pairs.
- 240 V2/V3 capability and full-reset pairs; physical trace equality through
  the earlier trigger; full physical equality whenever triggers align.
- 200 same-family normal-baseline versus disturbed-baseline exact
  pre-injection controls, through step 80 for shift and 180 for drop.

A full reset includes simulator observation contact flags; none are omitted.
Performance is not an audit gate. A failed scheduled attempt is valid evidence
if contracts/replay/pairing pass. A mismatched prefix, source or capability is
invalid evidence and cannot be repaired by tolerance relaxation. If native
comparability fails, preserve it and return to 02 before changing the comparator.

## Outcomes and metric denominators

Task scoring is unchanged: contact grasp, at least 5 cm achieved lift, goal
distance at most 2.5 cm and five consecutive static observations. Release is
not required. Final task success is separate from recovery phase completion.

`curve.csv` has 48 cell rows. `suite.json` additionally records raw comparisons,
per-cell completion/abort counts, trigger steps, precision and paired effects.

- **V2 minus V3 final task effect:** matched eligible-pair success difference,
  with both-success/both-fail/V2-only/V3-only counts.
- **Unnecessary recovery:** an attempt in a matched pair whose baseline
  succeeds. Rate denominator is baseline-success eligible pairs. Also report
  the unnecessary fraction of attempted episodes. This is a counterfactual
  scoring definition, never an input to the controller.
- **Regression:** baseline succeeds and the active system fails. Denominator
  is baseline-success eligible pairs; separately report V2-only/V3-only success.
- **Paired retry costs:** V3 minus V2 actions/TCP path over all eligible pairs,
  including zero for no attempt. All failed/aborted attempts contribute. This
  avoids comparing only different subsets selected for recovery.
- **Conditional attempt costs:** retain per-cell means among attempts as well.
- **Timing/completion/precision:** retain trigger-step lists, attempt-complete
  and abort counts, final goal-distance mean/median/maximum, and paired goal
  error difference. Controller actions are not wall-clock thinking time.
- **Verification metrics:** V1/V2 retain raw reference-agreement counts. V3
  metrics are null because its verifier is disabled, not zero-error scores.

Exclusions remain recorded with zero actions and cannot be replaced. They
must agree across paired systems. Rates/effects are null for incomplete/invalid
comparisons or zero denominators. Descriptive cell task rates never override
failed comparability. Points and dense frames are correlated.

## Execution and evidence preservation

The resumable runner preserves M4's study lock, captured normalized child
environment, software identity, raw hashes and replay checks. Continuation
launches only unstarted slots and retains failed/interrupted records; no slot
is silently rerun. Earlier partial archives remain unchanged. SSH ephemeral
keys alone are normalized; no environment contents or credentials are stored.

Use a new study/output/archive. Run the first four preselected slots with
`--stop-after 4`, covering all four systems in shift-normal seed 80. Their
outcomes are data, not tuning. Check contract validity, not V3 task success.
They remain in the 960-trial sample. Then resume under nohup only if those
four are valid. SSH disconnect does not stop that background batch.
This is an unrendered measurement batch; it does not start a browser session.
Live viewing is separate and is not required to count a measured episode.

Do not edit the repository, library environment or protocol during the batch.
Preserve original partial and final archives. After native completion upload
`aether-cl-m5-attribution-seeds80-99.tar.gz` for independent raw audit.
No native M5 outcome is claimed before that audit.

## Local validation

All **105 tests pass** (203.496 seconds), including seven M5 tests.
Python 3.10 grammar, both CLI help commands and documentation links verify.

Validation covers schedule-only invocation, rejection of verdict arguments,
exact shared recovery capability, normal/small/large shift/drop strict fixtures,
reference contact-label isolation, disabled verifier construction, exclusions,
tamper rejection, V3 subprocess family argument and unchanged M3 dispatch.
The full 960-slot wiring fixture checks all 48 cells/1,160 comparisons,
pause/resume without rerunning, archive hashes, regression/unnecessary-retry
rates, all-episode paired costs and null incomplete/zero-denominator effects.
Startup environment, lock and raw-tamper guards and preregistration-before-output
rejection are checked. All existing tests are retained. These fixtures do not
validate native contacts or supply fresh-seed performance findings.

## Return boundary

**M5 is the only newly authorized engineering work.** Do not redesign nominal
motion or precision, add placement/release, insertion, realistic force
perturbations, visual verification, memory, world models, Prototype B/C/D or 02W.
After M5 is frozen, executed and independently audited, return to 02 again
before further implementation. Prototype A closure is still a research decision.
