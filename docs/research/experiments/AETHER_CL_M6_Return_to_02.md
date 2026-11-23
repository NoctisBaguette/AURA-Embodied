# AETHER-CL M6 — Return to 02

Date: 2026-10-06 (Asia/Shanghai).

**06-01 has completed the authorized M6 implementation, native execution and
independent audit. Please review the negative recovery result before authorizing
further implementation. Prototype A remains scientifically open.**

Historical handoff: [02 accepted this result](AETHER_CL_M6_02_Research_Review_v0.1.md)
at `33918f5f2da97c355a0c2d7cda60b448f77bb2a6` under DEC-0005 and authorized
[M6R only](AETHER_CL_M6R_Placement.md). The original M6 result remains unchanged;
M6R native commissioning and fresh evidence are pending.

Authority: DEC-0004 and [02's M5 acceptance](AETHER_CL_M5_02_Research_Review_v0.1.md).
Executed scientific revision: `7059c713d3b36e3f032aab8d1f87662ed6fdab91`, clean.
M0–M5 scientific sources and protocols, M6 frozen sources, scoring, matrix,
tolerances and servo were unchanged during execution and result publication.

## Finding

Normal and 1 cm post-release shifts succeed 18/18 in Baseline, V1 and V2.
At 4 cm all achieve 10/18; at 8/12/20 cm all achieve 0/18. Seeds 107 and 111
remain initial-state exclusions in all cells. Thus each system succeeds 46/108
eligible episodes. V2 makes exactly 62 required attempts, with zero rescues,
zero unnecessary interventions and zero final-success regressions.

All attempts regrasp/lift/reposition, then abort `retry_lower_not_completed`
after 40 lower actions. TCP vertical residuals are 7.592–12.001 mm against the
3 mm gate; all are within the broader 20 mm distance gate, with one also outside
the orientation gate. The cube is table-supported, still contact-grasped and
within 3.737–8.201 mm of goal XY at abort. No attempt reaches release/retraction;
all end still grasped. This is a local lower-phase execution limit, not exhaustion
of the 800-action episode budget. Improving goal proximity does not satisfy M6.

M6 demonstrates native released placement viability, but **does not demonstrate
useful released-placement recovery** with this frozen bounded executor. Earlier
held-cube successes cannot substitute for these new endpoint semantics. The
observed lower-gate/contact mismatch does not by itself choose a repair or refute
verification-gated recovery as an architecture.

## Evidence acceptance

All three archive hashes, 1,804 final and 94 pilot file indexes, per-trial file
lists, 360 raw trial replays, 259,200 actions, independently recomputed endpoint
scores and 340 strict paired/control comparisons pass. Maximum action replay
error is zero. Pilot/final aggregate JSON and CSV reproduce exactly.
The report-only serialization repair preserves the original completed child,
immutable backup and first 18 pilot slots without reruns or outcome replacement.
The commissioning gate intentionally required native task/injection viability,
not V2 recovery success, so its pass is consistent with this negative result.

Final archive SHA-256:
`21b1739df6a8f66ecb2af5bb6dc865b3b96d7ffbb44ebbec030237ace2b3843e`.
Full hashes, methods, costs and limitations are in the
[audited results](AETHER_CL_M6_Results.md),
[machine audit](evidence/AETHER_CL_M6_Native_Audit.json) and
[episode outcomes](evidence/AETHER_CL_M6_Episode_Outcomes.csv).

## Decisions requested from 02

1. Accept the engineering/evidence completion separately from unsuccessful
   placement recovery; record the result within H3/H4's bounded scope.
2. Decide whether to authorize a narrow follow-up commissioning study of
   attainable lowering/contact geometry and the transition to release. Such a
   change needs a new frozen revision and fresh evaluation; the M6 failures stay
   retained. No correction is implemented or new run started in this handoff.
3. Keep broader Prototype A closure and any later scope under explicit review.
   This evidence does not establish insertion, physical-force disturbances,
   non-privileged verification or robustness beyond these 20 common seeds.

Branch `06-01/aether-cl-m0`; [PR #1](https://github.com/NoctisBaguette/AURA-Embodied/pull/1)
remains draft, open and unmerged. Main is unchanged. This file is the handoff
for the operator to provide to 02; no message has been sent to another agent.
