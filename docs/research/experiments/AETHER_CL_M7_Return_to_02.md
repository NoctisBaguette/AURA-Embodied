# 06-01 → 02: M7 frozen evidence return

M7 — contact-rich insertion is complete and independently audited under DEC-0006. This is an evidence return; 02 acceptance and any later scope remain pending. No model training occurred.

Native measurement is `a51e5d2073c4033141b26e956804d593aa45d6df`. The full archive SHA-256 is `ec96345ff23e44583e6e3d58f0e847625add225b02af77485970d090c70fbf75`. Installed ManiSkill 3.0.1 `PegInsertionSide-v1` uses a rigid square peg/channel and one arm, privileged state, and frozen synthetic target-local lateral waypoint bias. Independent scoring uses acquired object-target depth/orientation/channel fit and a complete pose-stability window; built-in success does not drive control. Final verification retains grasp, so no release claim is made.

All 360 frozen episodes remain: 20 common fresh scenes, seeds 140–159, six conditions and matched Baseline/V1/V2. No exclusion, replacement or outcome-based rerun.

| Nominal offset | Baseline | V1 | V2 | V2 attempts / successful recovery episodes |
| --- | --- | --- | --- | --- |
| 0 mm | 18/20 | 18/20 | 18/20 | 2 / 0 |
| 1.5 mm | 18/20 | 18/20 | 18/20 | 3 / 1 |
| 3 mm | 0/20 | 0/20 | 18/20 | 20 / 18 |
| 6 mm | 0/20 | 0/20 | 18/20 | 20 / 18 |
| 12 mm | 0/20 | 0/20 | 18/20 | 20 / 18 |
| 24 mm | 0/20 | 0/20 | 18/20 | 20 / 18 |

V2 produces 72 paired rescues among 84 Baseline-failed scene-condition pairs and no final regressions among 36 Baseline-success pairs. Its 73 successful recovery episodes include one unnecessary easy-case attempt: seed 150's Baseline first succeeds at 657, while V2 reacts to transient instability at 642, starts at 643 and first succeeds at 871 after 229 recovery actions. Strict first-onset diagnosis records one mismatch (depth failure becomes instability). Normal seed 152 has a one-step reference fault filtered by persistence, counted as a missed onset by the frozen metric.

The two persistent failed scenes must remain explicit. Seed 143 never acquires the peg, consumes the single episode and misses injection readiness. Seed 155 acquires, backs out, refreshes and realigns, then stalls at the channel entrance and exhausts the 140-action reinsertion stage in every condition, including normal. V2 therefore succeeds at 18/20, not 20/20 or a primary 18/18 rate. The trace does not isolate a unique physical cause.

Across 85 attempted V2 episodes, 79 finish backout/refresh/realign and 73 finish reinsert/verify; six acquisition aborts and six reinsertion aborts remain. Harder-condition rescues use 136–170 recovery actions, within the one-episode 420-action cap. All-outcome mean added total TCP path is 102.250 mm across 120 matched V2/V1 episodes; failed and zero-attempt cases stay included.

Audit verifies all three transfer-part hashes, the reconstructed archive, all 1,821 final indexed files, 111 pilot indexed files and all 106 immutable retained pilot child/source/protocol files. All 15 source/guard snapshot Git blobs and installed identities match. All 360 replays pass with 432,000 zero-error actions, 432,000 independently reconstructed endpoints and 2,160,000 external physics samples. All 340 exact comparisons pass: 120 passive, 120 recovery/full-prefix and 100 pre-injection controls. Aggregate JSON and three CSVs regenerate exactly; all 342 resume-log start/end pairs match the retained trials. No scoring or tolerance adjustment follows native outcomes.

Suggested narrow claim for 02 to assess: **a verification-gated, one-episode retreat/refresh/realign/reinsert pattern extended a fixed controller's success across this contact-rich insertion misalignment family, with two persistent scene failures, one unnecessary intervention and no observed final healthy-case regression.** The same 20 scenes repeat across conditions; 72 rescues are 18 common scenes times four harder levels. M7 tests the whole pattern and does not independently ablate task-effect phase semantics.

Review [full results](AETHER_CL_M7_Results.md), [machine audit](evidence/AETHER_CL_M7_Native_Audit.json), [episode CSV](evidence/AETHER_CL_M7_Episode_Outcomes.csv), [cell CSV](evidence/AETHER_CL_M7_Cell_Outcomes.csv), [paired costs](evidence/AETHER_CL_M7_Paired_Outcomes.csv) and [failure/timing traces](evidence/AETHER_CL_M7_Diagnostics.json).

Request 02's acceptance within the preregistered scope, its bounded H1/H4 interpretation, and the next authorized Prototype A scope. No next round is started. Physics-propagated disturbances, sensor verification, memory/world models, B/C/D, foundation models and 02W remain deferred. PR #1 remains open/draft/unmerged; main is unchanged. This document is prepared for handoff and has not been sent as a message.
