# M6R return to 02 — audited fresh native evidence

Date: 2026-10-06 (Asia/Shanghai).

Request independent research review of M6R under DEC-0005. The frozen experiment
and independent raw audit are complete. No follow-up implementation is started.

Repository: `NoctisBaguette/AURA-Embodied`, branch `06-01/aether-cl-m0`, PR #1
draft/open/unmerged. Native measurement revision:
`9ac5439e003f2ed65ecf2ea02f59a6186c7b6714` (clean).
Authority: [02's accepted M6 review](AETHER_CL_M6_02_Research_Review_v0.1.md)
at `33918f5f2da97c355a0c2d7cda60b448f77bb2a6`, DEC-0005. The later evidence
documentation commit does not change the measurement sources or protocol.

## Authorized single change

V2-old is original M6 V2. V2R changes only the recovery lower completion
predicate: replace dedicated 3 mm absolute TCP-Z attainment with controller
geometric support and frozen 25 mm goal XY. Retain minimum motion actions,
20 mm TCP distance, 0.15 rad rotation, attachment monitoring, all motions/targets/
settings/durations, one-attempt/400-retry/800-total budgets, verifier and contact
task score. Evaluator/contact/grasp/success and disturbance labels never enter
recovery. Baseline/V1/V2-old and all historical M0–M6 evidence stay frozen.

## Returned evidence

The previously audited known16 commissioning is development-only and separate.
Fresh native matrix: seeds 120–139, six conditions, four systems, 480 selected
records. Seed 132 is initially inside target XY and remains excluded with zero
actions in all 24 cells. Thus 19 eligible common seed scenes, 456 eligible
records / 364,800 actions, with all exclusions retained. Prior native history
checked 2,235 event files and found no observed 120–139 resets. First24 was
retained, its viability/evidence gate passed, immutable pilot bytes are preserved
in final, and only the other 456 were launched under one environment.

| Condition | Baseline / V1 / V2-old, each | V2R |
| --- | ---: | ---: |
| Normal | 19/19 | 19/19 |
| 1 cm | 19/19 | 19/19 |
| 4 cm | 6/19 | 19/19 |
| 8 / 12 / 20 cm, each | 0/19 | 19/19 |

Both old and repaired recovery attempt the same 70 failed placements. All old
attempts time out after 40 lower actions, never release/retract and remain held.
All repaired attempts execute release/retraction and finish independently scored
released, supported, stable and retracted, with final XY error 0.437–4.116 mm.
There are 70 paired rescues, zero old-only successes, and zero unnecessary
attempts or regressions in the 44 Baseline-success condition/seed pairs.

All 480 raw replays, direct endpoint reconstructions and 460 strict comparisons
pass. Action replay error is exactly zero. Every old/R attempted pair is exact
through its common boundary action/observation/contact/reference/verdict at
steps 426–497. Only post-observation lower readiness then differs, justified by
independent old/repaired predicates; actual action differences start at t+1.
44 eligible no-attempt pairs have full 800-step equality, and six excluded pairs
have equal zero-action records. The replacement gates pass while old Z misses.

V2R averages 18.286 extra retry actions and 123.075 mm extra total TCP travel
over old across the 70 attempted pairs. Every eligible episode still has 800
actions; all attempts stay within 400. All failed/zero-attempt costs are retained.
21 locally derived orientation diagnostics differ by at most 2.46e-13 rad;
only this diagnostic has a 1e-12 replay bound. All physical/controller/verifier
fields and gate booleans are exact. Source/protocol/native-source identity,
pilot file hashes and aggregate CSV reconstruction pass.

## Review material and archive identity

- [Full results, methods, costs and limitations](AETHER_CL_M6R_Results.md)
- [Preregistered protocol](AETHER_CL_M6R_Placement.md) and
  [machine freeze](evidence/AETHER_CL_M6R_Placement_Protocol.json)
- [Machine native audit](evidence/AETHER_CL_M6R_Native_Audit.json),
  [episode CSV](evidence/AETHER_CL_M6R_Episode_Outcomes.csv),
  [curve CSV](evidence/AETHER_CL_M6R_Native_Curve.csv) and
  [paired outcome CSV](evidence/AETHER_CL_M6R_Paired_Outcomes.csv)
- [Known16 development audit](AETHER_CL_M6R_Known16_Native.md)
- [Read-only full auditor](../../../tools/audit_m6r_return.py) and
  [evidence generator](../../../tools/m6r_publish_evidence.py)

Final archive SHA-256:
`d3427dbdd9759ee018ad82182273462c6481869f54234e9d1523f4934857a391`.
First24 pilot SHA-256:
`dc388e5bb6b96f4de838bab4494384de86cd38265327b6fb78e0ba80e149cbc0`.
Known16 archive SHA-256:
`779b8cc01ab2f0c47ff4d7a407750c20a17fd46f98bf93fc3726bf38eb912bb1`.

## Claim and decision requested

Assess whether the strict common-prefix intervention and released-placement
rescues support the narrow effect-aligned phase-completion claim in this task,
and accept or reject the returned evidence independently. Determine the next
research step separately. No success gate, controller tuning, duration increase,
replacement seed or post-hoc motion redesign was introduced.

Limitations: one task/cube, privileged state, synthetic relocation and 19 common
eligible fresh scenes reused across six conditions. The 70 rescues are not 70
independent scenes. There is no claim of learning, physical-force/sensor
robustness, insertion, general embodiment transfer or population-wide success.
Prototype A stays open; main unchanged. No M7, insertion, force/sensor work,
memory/world models, B/C/D or 02W proceeds without new research authorization.
