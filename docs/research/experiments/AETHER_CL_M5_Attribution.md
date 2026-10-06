# AETHER-CL M5 — Verification-Gating Attribution

Date: 2026-10-05 (Asia/Shanghai)

Status: M5 native execution and independent archive audit complete (2026-10-06).
Return to 02 before further implementation; Prototype A remains scientifically open.

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
GPU visibility selection are unchanged. Rendering is disabled; the native
manifest retains the unused inherited render_device default (see provenance below). Existing installed packages suffice.

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

## Audited native results

Date: 2026-10-06 (Asia/Shanghai). The native study ran on clean implementation
commit `12a9d2626636206e1687fa24df507bbadbc2a37d`. The uploaded archive is
`aether-cl-m5-attribution-seeds80-99.tar.gz`, 129,811,535 bytes, SHA-256:

`a14d7542fcff8f025f13c72fb209f9c13e8666af0d8571855e3ad7035f6bbcab`

The [independent machine audit](evidence/AETHER_CL_M5_Native_Audit.json)
verified all 4,804 indexed file hashes and exact archive membership; all 960
selected one-episode children are eligible, with no replacement or exclusion.
All 345,600 actions, controller decisions/snapshots and reference/verifier
observations replay. Maximum action reconstruction error is
2.9802322387695312e-08, below the existing 3e-7 action replay tolerance.
Strict physical comparisons retain exact equality; no tolerance was relaxed.

All 240 passive, 240 V1/V2 causal, 240 baseline/V3 scheduled, 240 V2/V3
attribution and 200 normal pre-injection comparisons independently pass.
The 180 V2/V3 pairs with aligned triggers have identical **entire physical
traces**. All 48 cell summaries, 12 paired outcomes and native CSV reproduce
exactly. Python 3.10 ordered binary64 addition is reproduced under audit
Python 3.12 rather than relaxing aggregate equality. All 96 repository blobs
used for the audit matched the implementation Git tree before documentation
updates. This replays logged computations; it does not rerun native physics.

### Final shared task success and paired costs

Each point uses the same 20 preselected seeds. Baseline and V1 agree exactly.
Costs below are V3 minus V2 **per eligible paired episode**, including zero
cost when no retry occurred and all failed/aborted retry costs.

| Point | Baseline / V1 | V2 | V3 | V3 extra retry actions / TCP path vs V2 |
| --- | --- | --- | --- | --- |
| shift-normal | 20/20 | 20/20 | 20/20 | 132.15 / 0.5479 m |
| shift-020mm | 20/20 | 20/20 | 20/20 | 131.70 / 0.5473 m |
| shift-040mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| shift-080mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| shift-120mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| shift-200mm | 0/20 | 19/20 | 19/20 | 0.00 / 0.0000 m |
| drop-normal | 20/20 | 20/20 | 0/20 | 71.70 / 0.2338 m |
| drop-020mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| drop-040mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| drop-080mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| drop-120mm | 0/20 | 20/20 | 20/20 | 0.00 / 0.0000 m |
| drop-200mm | 0/20 | 18/20 | 18/20 | 0.00 / 0.0000 m |

Normal points have no injection; their different labels select the two frozen
V3 schedules. They are correlated repeats of the same 20 initial scenes.
Do not pool this table as independent initial scenes or infer an exact
failure threshold from the finite tested magnitudes.

### What verification gating contributes

All 60 baseline-success point/seed pairs (two healthy controls and 2 cm shift)
complete without a V2 retry. V3 retries unnecessarily in all 60. Its normal
shift and 2 cm shift attempts still succeed but cost 132.15 / 131.70 extra
actions and 0.5479 / 0.5473 m extra TCP travel on average. Median final goal
error worsens from 0.510 mm to 18.378 mm on healthy shift and from 9.651 mm
to 18.414 mm on the 2 cm shift; both remain inside the 25 mm tolerance.

On the healthy **drop-family schedule** control, V2 succeeds 20/20 with no
attempt. V3 retries 20/20, fails 20/20 and aborts with
`retry_grasp_not_established`. The unnecessary-recovery and regression rates
are both 100% of baseline-success pairs; V2's corresponding rates are zero.
Archived step 183 contains a valid grasp. Action 184 begins retry retraction
and opens it; contact grasp is lost in all 20 episodes. The cube falls toward
the table after the controller has cached its elevated pose for that attempt.
The unchanged retry does not refresh again, and cannot establish its new
grasp. This is a specific measured failure mechanism of this scheduled
comparator plus the existing recovery capability, not a universal property
of verifier-free manipulation.

The 180 disturbed cases that need recovery align at trigger 127 for shift
or 183 for drop. V2 and V3 have identical physical traces, costs and outcomes:
177 successes and three final failures in each system. M5 therefore shows
**selective invocation value on controls that do not need recovery**, while
showing **no extra success advantage from gating when this phase-aware
schedule already invokes the same retry at the same time**. It supports
bounded H3 claims about avoiding harmful/costly interventions, not general
necessity of explicit verification for every recovery or real-world task.

### Completion, aborts and new large-disturbance failures

V2 makes 180 attempts: 172 complete and eight abort. V3 makes 240 attempts:
212 complete and 28 abort, including the 20 healthy-control failures.
Five aborted 20 cm drop attempts per system still achieve the shared task;
attempt completion and task success remain distinct.

- **20 cm shift, seed 99:** both V2/V3 fail after
  `retry_transport_target_not_reached`; 19/20 final successes at this point.
- **20 cm drop, seeds 87 and 99:** both V2/V3 exhaust the 177-action remaining
  budget without final task success; 18/20 final successes at this point.
- **20 cm drop, seeds 88/90/92/93/96:** both V2/V3 exhaust the budget but are
  successful by the final scored observation. First shared task success is
  at steps 360/354/360/354/355 respectively. Seeds 88/92 achieve it exactly
  on the last allowed step; no post-deadline action or success is counted.

The original M4 20/20 successes remain valid for seeds 60–79. M5's new
seeds reveal finite-sample limits at 20 cm; the accepted controller was not
tuned and these failures are retained. The per-episode machine audit includes
all terminal snapshots, first-success steps and abort transitions.

### Renderer provenance and live viewing

The measurement manifest carries inherited unused `render_device: cuda:1`
even though CUDA_VISIBLE_DEVICES is 1. All 960 configs have render=false:
`build_env` selects render_backend=none, with CPU physics. No renderer uses
that ordinal; no images/video were archived. The earlier planning prose
describing local cuda:0 applies to explicitly enabled rendering, not this
unused batch config field. The recorded native environment is preserved.

[Separate live demonstration commands](AETHER_CL_M5_Live_Demonstrations.md)
reuse existing runtimes/viewer without tracked source edits, pause before
each new run and retain its final image. They are not playback or a substitute
for the original native evidence; rendered traces are not assumed identical.

### Research return boundary

**M5 implementation, native execution and independent archive audit are
complete. Return to 02 for interpretation and the next scope decision.**
Prototype A remains scientifically open. No release/support placement,
contact-rich insertion, physics-propagated disturbance, non-privileged sensor
verifier, motion redesign, memory, world model, B/C/D or 02W is activated.
The [M5 handoff](AETHER_CL_M5_Return_to_02.md) records the bounded H3/H4 update.
PR #1 remains open, draft and unmerged; 02's research acceptance is pending.
