# Final B CPU fix wave — 2026-10-22

This closes the three Important findings in `FINAL-REVIEW.md` and the
workspace-root unittest import-order failure. Production changes are confined
to `evaluate.py` and `ledger.py`; the aggregation implementation is unchanged.

## Regressions and fixes

- Before the import-order fix, root discovery failed to import
  `aggregate_results` because `test_aggregation.py` imported it before
  `support.py` added the evaluation directory to `sys.path`. Importing support
  first makes standalone root discovery work.
- Before the runner fixes, new tests reproduced missing stream paths for
  complete, rejected, crashed, invalid-JSON and timed-out attempts, and showed
  that `PENDING` video review could be accepted as a complete episode. The
  runner now writes full child stdout/stderr directly to exclusive files in
  each attempt output directory, records both paths in immutable terminal
  evidence, and applies the aggregator's video-status values before completion.
- Before the ledger fix, tests showed that STARTED records could disagree with
  `run_config.evidence_kind`, `run_config.plan.stage` and
  `run_config.plan.checkpoint_manifest_sha256` on both write and read. The
  ledger now checks those configured identity fields at both boundaries.

## Verification

Interpreter: Python 3.12.10. From the workspace root:

```powershell
python -m unittest discover -s lingbot/submission/evaluation/tests -v
```

Result: **50 tests passed**. The complete command output is in
`final-tests.txt`. The focused runner and ledger suites also passed; the final
root run includes all current regression tests, including exclusive log-file
creation.

These checks use synthetic CPU subprocess fixtures. Real policy episodes
remain zero; model loading, native simulation, real interruption/resume and
throughput remain NOT RUN.
