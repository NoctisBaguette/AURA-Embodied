# Final independent B CPU review — 2026-10-22

SPEC: **CHANGES REQUIRED**. QUALITY: **CHANGES REQUIRED**. Native acceptance: **NOT RUN**.

This review stops at three confirmed remaining Important defects so the implementer can make one repair wave. It does not claim final CPU acceptance. The native A package, full inference assets and simulator adapter are unavailable; real loading, parity, native task success/action-limit verification, real interruption/resume and throughput remain NOT RUN, with zero real policy episodes from this review. The known unittest discovery import-order repair is being handled separately and is not a new finding here.

## Exact reviewed versions

Frozen root `review-final-snapshot.txt`: SHA256 `3f5e66b6e6ee1da4e8ca1fda0ec28e2ab3426698a43b61f440e1766f43be0e1c`.

Live source hashes at review (matching the relevant frozen implementation):

- `evaluate.py`: `91e6cec7e8e557d11162479095010d3fcdbf1a11c38835c756d1e4771e573d09`
- `ledger.py`: `f860456dd2f5c87bc4e8bc20fafb1647eff6b6184213e0ba38df9110e1baad04`
- `aggregate_results.py`: `fd0526dbccad64f88bd20ec71d59fa94a0785f576087adf38e7d77210808a57c`

Read the workspace AGENTS, complete guide B requirements, implementation plan and prior runner/aggregation reviews. No routine suite rerun, environment change, GPU/native invocation or retained-input modification. Focused probes execute frozen source in memory, use temporary explicitly synthetic records and a bounded dummy Python subprocess; their synthetic aggregation count demonstrates a defect and is not policy evidence.

## Confirmed Important defects

1. **Attempt stream evidence remains truncated and unpersisted.** `SubprocessBackend.evaluate` still uses PIPE and retains only the last 4,000 characters on failures. It writes no stdout/stderr stream files. A worker printing more than 5,000 characters then exiting 9 loses the beginning of both streams, produces no log file and leaves terminal log_path null. Elapsed time and unknown action count are now present, but the original evidence-preservation finding is only partly fixed. Preserve complete attempt-owned streams for success, rejection, failure and timeout, and record their paths; retain runner-measured elapsed independently of any backend-supplied wall time.

2. **Evidence kind is not bound to the immutable run configuration.** Ledger finish/read now enforce STARTED/terminal/child agreement, and aggregation checks pairing, but `EvaluationLedger.begin` and `_validate_started` never compare the kind against run_config. A ledger initialized with `{'evidence_kind':'fixture'}` accepts a real_policy STARTED, terminal and child, reads them back successfully, and aggregation counts one real-policy episode. This is a direct ledger API boundary defect; the ordinary SerialEvaluator constructs its identity consistently. Validate kind against configured kind at begin and all record reads, in addition to existing pair/child checks.

3. **Runner and aggregator still disagree on video status validation.** A complete episode with video_path='fixture.mp4' and video_review_status='PENDING' passes `_validate_episode`, but aggregation raises `video_review_status must be REVIEWED or NOT_REVIEWED`. A malformed completion can thus be made immutable/skipped on resume and then fail final aggregation. Align the runner's permitted status values with the aggregator before accepting completion. Strict chunk_index/noise_seed checks are now present and address the scalar half of the original finding.

## Status of original runner blockers

| Original blocker | Current review status |
|---|---|
| Failure/rejection evidence | PARTIAL FIX; Important defect 1 remains. Nullable unknown actions and elapsed field added. |
| Fatal execution returns zero | Source fix present: main returns 1 when report errors exist. Completed selected subset can return zero. |
| Silent candidate/cell/stage exhaustion | Source fix present: CANDIDATE_BUDGET_EXHAUSTED, CELL_TIMEOUT and STAGE_TIMEOUT are emitted outside policy counts. |
| Fixture relabeling | PARTIAL FIX; STARTED/terminal/nested agreement added, fixture pairing added to aggregate; Important defect 2 remains at run_config boundary. |
| Descendant timeout handling | Source fix present: Windows taskkill /T /F and POSIX process-group kill, followed by bounded communicate. Not independently re-probed in this stopped review; native process ownership remains NOT RUN. |
| Scalar/video acceptance mismatch | PARTIAL FIX; strict integer/non-bool request validation added; Important defect 3 remains. |

Prior six aggregation fixes retain their independently documented scoped PASS in `review-aggregation-stable.md`; this review does not rerun or supersede that earlier evidence. Latest fixture STARTED/terminal pairing is present in source. No additional Critical finding established.

## Reproduction

From workspace root: `python lingbot/submission/evaluation/evidence/final-review-probes.py`.

Observed output (elapsed time varies):

```text
FAILURE_LOG_FILES []
FAILURE_OUTPUT_START_RETAINED False False
FAILURE_EVIDENCE {'wall_seconds': 0.06300000000010186, 'actions_started': None, 'log_path': None, 'video_path': None}
PENDING_VIDEO_RUNNER accepted
PENDING_VIDEO_AGGREGATOR video_review_status must be REVIEWED or NOT_REVIEWED
FIXTURE_RUN_CONFIG_REAL_RECORDS_COUNTED 1
```

No further probes were run after notifying the implementer of this complete confirmed Important list. Re-review the repaired boundaries and final test receipt before claiming CPU completion.
