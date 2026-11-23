# AETHER-CL M8 — independent first18 review

Reviewed 2026-10-08 UTC. **The frozen first18 integrity gate passes. Resume the 342 unstarted slots at the unchanged measurement revision. M8 is not complete or accepted by 02.** This publication adds review evidence only; it changes no controller, scorer, verifier, force, seed, threshold, budget, runtime or history guard.

## Pilot result

The 18 requested episodes cover two fresh common scenes (160/161), three frozen force conditions and Baseline/V1/V2. All 18 are retained and will remain in the final 360. They form six matched scene-condition pairs, not 18 independent scenes. No initial-goal exclusion or missed force precondition occurs.

| Frozen condition | Commanded +Y force | Baseline | Passive V1 | Recovery V2 |
| --- | --- | --- | --- | --- |
| normal | 0 N | 2/2 | 2/2 | 2/2 |
| force-easy-v1 | 0.41868388652801514 N | 2/2 | 2/2 | 2/2 |
| force-probe-2 | 2.322110652923584 N | 1/2 | 1/2 | 2/2 |

Total pilot success is 5/6 per Baseline/V1 and 6/6 for V2. V2 makes one attempt, rescues one matched failure, and has zero unnecessary attempts or final regressions relative to Baseline. The pilot contains only three of six force conditions; complete 20-scene cell rates remain null. These partial counts do not establish the complete robustness curve.

For force-probe-2, seed 161, the reference reports `PLACEMENT_TARGET_NOT_REACHED` at 340; V1/V2 confirm it at 342. V2's first recovery action is 343. The unchanged effect-aligned recovery uses 153 actions, reaches lower readiness at 458, releases at 459, retracts at 469, and first satisfies the task at 489. Final horizontal error is 4.121 mm with release, stable support and retraction all independently satisfied. The matched Baseline fails and V1 preserves that outcome. Seed 160 succeeds under this condition without recovery and remains retained.

The pulse is an engine force, not cube pose/velocity relocation. Before intervention, seed 161's recorded pulse displacement is approximately (−6.713,+27.968,+1.133) mm; pulse velocity change is approximately (−0.377,+0.471,+0.067) m/s. Its pre-intervention peak horizontal displacement is 107.410 mm and peak speed 1.000 m/s, with sampled support loss. These are recorded physical responses, not commanded displacement targets. Whole-episode response can include recovery and remains separately labeled.

## Independent integrity review

Pilot archive: `aether-cl-m8-placement-seeds 160-179-pilot.tar.gz`, 9,560,357 bytes, SHA-256 `535218e74854326946a157f8aa620aa1ca41db78351097074074702cd49d295c`.

Measurement revision: `e8184217dc4b3c205666787441b87b13ba8a489c`. Protocol SHA-256: `3e67b43747b4d52b73b39c64d2b1f159a855f91cde012b8a5ceffbaf6c40a031`. Review publication must not replace the server's detached measurement head.

Safe extraction verifies unique regular-file/directory members, complete membership and all 221 indexed file sizes/hashes. All 21 source/protocol/review/history-guard snapshots match the authoritative Git blobs at the measurement revision. Native source/library/binary/software identities match the accepted commissioning record apart from the explicitly changed wrapper commit. Parent/child configurations, original absolute output paths, frozen 360-slot plan, nonvolatile environment digest and all 18 ordered log start/end records match. No environment values are republished.

All 18 accepted-runner replays reconstruct task reference, verifier, recovery, controller decisions, path and terminal summaries: **14,400 actions, zero maximum action error**. All 18 physical and instrumentation audits regenerate exactly: **72,000 external physics samples, 60 engine-force calls, 14,400 matched online controller-gate actions**. The fixed 296th-action pulse remains five 100 Hz substeps on a released, supported cube during active nominal retract. No motor action comes from the instrumentation replay.

All 16 strict comparisons regenerate and pass: six complete passive pairs, six recovery common-prefix/full healthy pairs, and four pre-force controls. The physical diagnostics, aggregate JSON, pilot gate and original CSV byte stream regenerate exactly. The integrity gate has **no task-success criterion**; failed task outcomes remain evidence.

The recorded entry guard scanned 3,216 native event files and 5,719 reset records, reports no retained-history overlap for selected seeds 160–179, and retains fingerprint `f330e9f28c1398fbe4e552ffef96048075b1647a1e959af9995f122b8fc6b586`. The uploaded pilot includes this guard record, not the complete remote historical event corpus; the independent reviewer verifies the record and provenance, while native resume rechecks the actual retained corpus. The recorded 36-episode commissioning prerequisite matches the previously independently audited archive/report/review hashes.

Read-only replay uses Python 3.10.21, NumPy 1.26.4 and SciPy 1.10.1 against native Python 3.10.22 with the same NumPy/SciPy versions. No simulator was constructed locally, no tolerance widened and no episode rerun. Evidence: [machine receipt](evidence/AETHER_CL_M8_First18_Review.json) and [executed review source](evidence/AETHER_CL_M8_First18_Executed_Review.py).

## Completion path and time

Resume only the unchanged `paused_first18` checkpoint, using the reviewed pilot SHA and native measurement head `e8184217dc4b3c205666787441b87b13ba8a489c`. The frozen runner validates the pilot, replays the 36 commissioning episodes, rechecks retained history, then executes exactly 342 unstarted slots. No source transfer, new commissioning, new force search, seed replacement or tuning is needed. Final validation must preserve the original 18 records/raw/source files and verify all 340 fixed comparisons. An interrupted or error checkpoint is retained for diagnosis, not automatically retried.

Observed timing from archived native metadata: the suite began at 12:23:14 UTC, the first child's stdout file opened at 15:08:39, and the final pilot suite was saved at 15:14:31. Before the first launch, approximately 2 h45 min elapsed in prerequisite/startup work. After the first child, the median interval between starts was 17.890 s; 342 episodes at that rate are approximately 1 h42 min, excluding repeated prerequisite checks, final replay and archive work. This is a planning estimate, not a runtime guarantee. Native resume repeats the safeguards; storage/cache and server load can materially change their time. Allow several hours and use `nohup` rather than an attached session.

After the final `M8_FROZEN_EVIDENCE_VALID` marker, download the final archive and resume log in separate SCP commands. Return them for independent full evidence review, then return to 02 for acceptance and the next-scope decision. A file appearing during archive creation is not a completion signal.

## Prototype A recap for application planning

| Round | Established within accepted scope | Current boundary |
| --- | --- | --- |
| M6R | Effect-aligned lower-phase completion rescues 70/70 placement failures versus 0/70 under the old gate, with exact common-prefix evidence. Those condition outcomes reuse 19 eligible scenes. | Accepted by 02, DEC-0006. |
| M7 | Verification-gated retreat, one geometry refresh, realignment and reinsertion rescues 72 failed scene-condition pairs. V2 succeeds 18/20 at each harder offset; two persistent failures and one unnecessary easy retry remain counted. The 72 rescues reuse 18 scenes over four conditions. | Accepted by 02, DEC-0007. |
| M8 | Extends the same accepted placement/recovery mechanism to engine-force disturbances. Fresh pilot evidence reconstructs exactly and shows one rescue without pilot unnecessary retries or regressions. | 18/360 complete; 342 unstarted. Full result and02 acceptance pending. |

The defensible project milestone is a working, audited **simulation research prototype** that checks physical manipulation outcomes and selectively invokes one bounded recovery, with accepted placement and insertion studies. Controller completion and physical task success are explicitly distinguished. M8 addresses the planned physics-disturbance dimension; non-privileged sensor verification remains open. These rounds use fixed controllers and privileged simulator state, with no model training, physical robot experiment or demonstrated RGB/RGB-D verifier.

For the 零点计划 application, existing accepted results can support feasibility now; label the partial M8 result as ongoing until the full audit and02 decision. Do not describe Prototype A as fully closed. The intended next sequence is complete M8 → independent full review →02 →02W verifier design/scope →M9 if authorized. 06-01 does not initiate 02W/M9 or broader architectures through this pilot publication.
