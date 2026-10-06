# AETHER-CL M6R — Effect-Aligned Lower-to-Release Transition

Date: 2026-10-06 (Asia/Shanghai).

Status: implementation frozen at `9ac5439e003f2ed65ecf2ea02f59a6186c7b6714`.
Archived known-M6 checks and [native known16 commissioning audit](AETHER_CL_M6R_Known16_Native.md)
pass. Fresh-seed execution remains pending; no confirmatory M6R outcome has been
observed. The evidence documentation commit is not a new measurement revision.

Authority: [02's M6 review](AETHER_CL_M6_02_Research_Review_v0.1.md), DEC-0005,
accepted at `33918f5f2da97c355a0c2d7cda60b448f77bb2a6`.
02 accepts [M6's negative evidence](AETHER_CL_M6_Results.md). Prototype A stays
open; PR #1 stays draft/unmerged. This is a repair experiment, not M7.

## One-factor question and implementation

With identical motion primitives, does changing the recovery lower-to-release
contract permit useful released-placement recovery?

| System | Implementation |
| --- | --- |
| Baseline | Frozen M6 `FixedPlacement`, no verifier or retry |
| V1 | Same frozen nominal policy plus M6 passive verifier |
| V2-old | Original, unchanged M6 `PlacementRecovery`, including the 3 mm Z gate |
| V2R | Subclass inheriting all action, target-refresh, settings, snapshot and terminal methods; one lower predicate changes |

For the recovery **lower** phase only, replace:

```python
abs(tcp_z - target_z) <= 0.003
```

with:

```python
supported_geometry and horizontal_error_m <= 0.025
```

Retain minimum three motion actions, general TCP distance at most 20 mm,
rotation error at most 0.15 rad, and the existing attachment-loss monitoring.
Geometric support keeps M6's oriented cube extent, bottom-to-table tolerance
of 4 mm and designated square workspace bounds. It is a privileged geometry
proxy, not a contact-force measurement. No contact-force, `is_grasped`, evaluator
reference, environment success or disturbance label enters the recovery.

There is no new Z threshold, motion command, refreshed target rule, lower
duration, retry, verifier or task score. The original settings object remains
identical; its 3 mm setting is explicitly marked unused by V2R's lower gate.
The new controller's observation method is text-identical to M6 apart from
this one predicate. A regression check enforces that identity; all action
methods are the same inherited function objects.

New `m6r_*` files isolate execution, logging, analysis, CLI and viewer labels.
Every M0–M6 execution source and historical machine protocol remains unchanged.
M6R preflight runs the complete M6 preflight chain and checks its new source hashes.
The old failed M6 results and meaning of V2 are preserved.

## Frozen task, motion and disturbance

Reuse [M6's endpoint and motion protocol](AETHER_CL_M6_Placement.md) unchanged:

- Actual prior contact grasp and lift at least 5 cm, release command, current
  non-grasp/open geometry, table contact plus support geometry, XY error at most
  25 mm, vertical and Euclidean gripper clearance at least 8 cm, five stable frames.
- Nominal durations 60/40/25/45/60/40/25/35/30; fixed original servo.
- Recovery durations 35/60/35/25/35/80/40/25/35/30, at most one attempt and 400
  retry actions within the identical 800-action episode budget.
- At step 296, attempt one synthetic positive-world-Y cube pose relocation
  after nominal release; zero velocities. Invalid release preconditions remain
  recorded missed injections, without retiming, exclusions or replacement.
- CPU physics, one fresh Python interpreter/native simulator per selected slot,
  no rendering during measurement; frozen native dependencies unchanged.
- Completed/aborted retries repeat their last absolute command through the
  episode deadline. Controller completion and independent task success stay separate.

## Development evidence versus fresh evaluation

Archived M6 traces are already observed. The
[known-trace development check](evidence/AETHER_CL_M6R_Known_Trace_Commission.json)
replays all 120 V2 slots and **86,400 actions** with the unchanged V2-old class.
V2R exactly shares the recorded actions/decisions/states through its first differing
lower transition in all 62 attempted recoveries. These differences occur at steps
429–498; on those common states, the retained gates and replacement support/XY
predicate pass while the old Z predicate fails.

The check stops V2R at divergence. Old post-divergence observations are never used
as a repaired rollout or success claim. The 46 non-attempted eligible and 12
excluded old slots have no difference. This is development evidence, not fresh
evaluation, and does not establish native V2R release/retraction or stability.

Native commissioning runs **16 separate development slots** on already-observed
seeds 100/101, normal and 8 cm, all four systems. It uses its own output directory,
archive root `m6r-commission`, scope and `confirmatory: false` flag. It generates
no confirmatory curve or paired success-effect estimate. All 14 comparisons,
raw replay, source identity, healthy nominal placement, actual post-release
injection and at least one valid lower-contract divergence must pass. **V2R final
success is not a gate.** Downstream failure is retained and diagnosed.

Fresh evaluation uses preselected seeds **120–139**, the same six conditions
and four systems: **480 selected slots, 24 cells**, before retained exclusions.
Repository protocols cover seeds only through 119; available previous native
evidence contains no observed 120–139 scenes. The native runner additionally
scans recorded resets under the prototype's `runs` directory before creating a
fresh study and stops if any selected seed is already observed. This provenance
check cannot detect unreported or deleted external runs; do not introduce such
observations before evaluation. Fixture states are synthetic, not native scenes.

A new native fresh study requires `--commission-report` from the validated known
16 report at the same source/software revision. Raw file lists and all child
replays/comparisons are checked again; changing the implementation requires new
commissioning before fresh evaluation.

The first **24 fresh slots** are normal/1 cm/8 cm × seeds 120/121 × four systems.
They stay in the 480-slot dataset. Pause for the preregistered viability/evidence
gate, then resume only the remaining 456 in point/seed/system order. No V2R success
criterion is used; no seed, failed attempt or missed injection is replaced.
The first 24 are confirmatory selected slots, unlike the known-seed development
commissioning. No tuning after inspecting them is authorized.

## Strict causal comparisons

| Comparison | Count | Required equality |
| --- | ---: | --- |
| Baseline/V1 | 120 | Full physical trace and reset |
| V1/V2-old | 120 | Physical/verifier prefix through the common trigger observation |
| V2-old/V2R | 120 | Full equality if no divergence; otherwise common recovery through first lower state divergence |
| Normal/disturbed Baseline | 100 | Reset and physical trace through step 295 |
| Total | 460 | Exact physical values; original 3e-7 action replay tolerance |

At step `t`, the action computed from the common preceding state, resulting
observation, contact reference and verifier verdict must still be identical.
Only the **post-observation recovery state** may first differ, and only because
the lower readiness predicates disagree. Recovery state is identical before `t`;
the first permitted action divergence is `t + 1`. Independently reconstructed
distance, orientation, old Z and replacement geometry/XY predicates justify the
boundary, using the grasp rotation cached at the original attempt start.
No-attempt or equally gated attempts require full equality.

Source identity, exact software/reset/injection matching, verifier/trigger
equality, manifest/result/event replay and full action budgets remain guarded.
Zero-action exclusions are compared and retained. Invalid comparisons or source
drift produce null scientific rates/effects, not claimed improvements.

## Required outcomes and interpretation

The native result and suite separately record final placed success, recovery
attempt success, lower-transition step, lower timeouts, release reached versus
executed, retraction reached versus executed, support/stability, final XY error,
controller completion, retry actions and TCP paths. Paired summaries compare
V2R/V2-old and each recovery system against V1; healthy-control unnecessary
attempts and regressions are measured against Baseline. Costs retain failed and
zero-attempt cases. Equal total budgets make retry actions work within the 800
steps, not additional episode steps.

- V2R rescues failures: bounded support for effect-aligned phase completion.
- V2R releases but fails later: one bottleneck removed, downstream limit exposed.
- V2R never releases: replacement readiness or another retained gate is insufficient.
- Healthy regressions: the changed transition must be reconsidered by 02.

All outcomes return to 02. No post-hoc threshold tuning or lower-duration increase
is authorized. This is one cube/task, privileged state, synthetic relocation and
20 common seed scenes—not sensor verification or physical-force robustness.

## Evidence discipline and execution

The [machine preregistration](evidence/AETHER_CL_M6R_Placement_Protocol.json)
freezes all parameters and source identities. Parent reports use the existing
NumPy scalar converter before strict JSON persistence, preserving true/false
and rejecting non-finite values; the M6 report serialization failure is covered.
No external reporting monkeypatch is needed for M6R.

Study locking, clean native Git revision, native packages/Python, startup
environment hash, source/protocol identity, prior raw hashes and replay are
enforced on continuation. Administrative SSH variables are normalized as in
M6; `XDG_SESSION_ID` remains guarded. Prefer a single detached parent process
for the future first24/check/resume sequence so reconnection does not alter its
startup environment. Separate development and confirmatory studies may start
under different sessions; an existing study cannot silently change environment.

See [native execution instructions](AETHER_CL_M6R_Execution.md).
No simulator is available in the analysis workspace; native evidence must be
generated on the existing A100 server and returned for independent audit.
The batch is unrendered. `python -m aether_cl.m6r --live ...` is a separately
labelled demonstration using already-observed seeds, with the same paused preview
and retained final image. Do not run it concurrently with measurement.

## Validation and return boundary

Local validation includes the exact single-factor source comparison, all
retained gate requirements, attachment loss, local timeout/global retry cap,
one-attempt terminal hold, contact-constrained old-fails/repaired-releases fixture,
input-label isolation, zero-action exclusion, prefix/verdict tamper rejection,
480 unique slots, first24 pause/continuation, 460 comparisons, independent known16
commissioning, source/environment/hash/lock guards and strict JSON scalar/NaN tests.
Fixtures do not establish native physics performance. All **136 local tests
passed in 288.791 seconds**, including 12 M6R tests and the original M0–M6/report
repair regressions. Python 3.10 syntax, CLI help, frozen source/protocol agreement,
viewer labels/final-frame retention and zero-action preview cancellation pass.
The detached fresh launch script passes Bash syntax validation.

After fresh M6R execution and independent audit, **return to 02 before any further
implementation**. No insertion, force-disturbance claims, camera verification,
motion redesign, memory/world models, Prototype B/C/D or 02W. Scientific closure
remains 02's decision; PR #1 stays draft/unmerged and main unchanged.
