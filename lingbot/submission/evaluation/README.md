# Captain integration review — 23 October 2026

B's original archive is retained separately and its 50 CPU tests reproduce. This separate revision has **57 CPU tests passing**; no native adapter, model or simulator was run. Use the sibling portable implementation from the same integration branch.

Changes: canonical `package-manifest.json` identity; A's full CPU package validation before runner records/backend startup; explicit UTF-8 subprocess transport; setup rejection cannot contain policy actions/requests/outcomes; separately measured `runner_wall_seconds`. The former production CLI test using a fictitious manifest now correctly rejects it before execution. A separate test with an explicitly mocked package gate exercises fatal backend exit propagation. These are CPU test fixtures, never submitted results.

The remaining native interface and model lifecycle are described in BACKEND-CONTRACT.md. One adapter process per scene must not imply loading the6Bmodel anew for every scene: integrate a separately owned persistent policy service after captain allocation. Keep complete model identity, no hidden automatic retry, and full task action budgets. This integration is not implemented by these CPU fixes.

Original B documentation follows; its historical50-test receipt remains historical.

# CPU evaluation package

This package implements the deterministic B schedule, serial subprocess
boundary, immutable journal/resume rules, and strict official-schema
aggregation. It is a CPU-only deliverable. The native task/policy adapter and A
policy package are not present, so it contains **zero real-policy episodes**;
all tests use labeled subprocess fixtures. `reference/` and `official/` are read
only.

From this directory, use Python 3.12 or newer:

```powershell
python --version
python -m unittest discover -s tests -v
```

The default schedule is 50 official tasks × clean/randomized, 100 completed
episodes per cell, at most 1,000 consecutive candidate seeds per cell starting
at 100000. The package maps clean to `seen` and randomized to `unseen`, runs one
worker, requests FP32, 50 actions per chunk and 10 denoising steps, and sends the
full official action-limit contract to the backend. Only the two typed setup
rejections in `BACKEND-CONTRACT.md` advance a seed; an unresolved start or any
other error blocks its cell.

Each attempted episode retains the backend's complete stdout and stderr in
exclusive files under that attempt's output directory. Their paths are recorded
in the immutable terminal ledger for successful, rejected, crashed, invalid-
response and timed-out attempts.

Create a one-task CPU schedule without importing third-party packages:

```powershell
python -S evaluate.py --tasks-file ..\..\official\results-template.json --setting clean --task lift_pot --episodes 1 --max-candidates 1 --seed-start 100000 --stage baseline --fixture-only --output .\evidence\single-cell-plan --dry-run
```

Create the complete 100-cell CPU schedule with the default candidate budget:

```powershell
python evaluate.py --tasks-file ..\..\official\results-template.json --setting all --episodes 100 --max-candidates 1000 --seed-start 100000 --stage baseline --fixture-only --output .\evidence\full-cpu-schedule --dry-run
```

Both commands write `run-plan.json` and an `evidence_kind: fixture`,
`status: NOT_RUN` report with zero policy episodes. They launch no backend and
load no policy or simulator. The second schedule file is a CPU artifact, not a
submission result.

For the disconnected native interface, see `BACKEND-CONTRACT.md`. After the
captain accepts the candidate budget and timeouts, the adapter and package are
provided, and the run is independently approved, a production command has this
form:

```powershell
python evaluate.py --policy-package PATH_TO_POLICY_PACKAGE --tasks-file ..\..\official\results-template.json --setting all --stage baseline --episodes 100 --max-candidates 1000 --seed-start 100000 --episode-timeout-seconds 3600 --cell-timeout-seconds 86400 --stage-timeout-seconds 604800 --backend-executable PATH_TO_REVIEWED_ADAPTER --output PATH_TO_RUN
```

This command is documentation only; no adapter is shipped and it has not been
run. Resume only with the same output directory and unchanged run configuration:

```powershell
python evaluate.py --policy-package PATH_TO_POLICY_PACKAGE --tasks-file ..\..\official\results-template.json --setting all --stage baseline --episodes 100 --max-candidates 1000 --seed-start 100000 --episode-timeout-seconds 3600 --cell-timeout-seconds 86400 --stage-timeout-seconds 604800 --backend-executable PATH_TO_REVIEWED_ADAPTER --output PATH_TO_RUN --resume
```

Aggregate a retained journal or report into the exact official schema; the
coverage sidecar remains separate from the upload-shaped JSON:

```powershell
python aggregate_results.py --records PATH_TO_RUN --checkpoint-manifest-sha256 CHECKPOINT_MANIFEST_SHA256 --team-id TEAM_ID --output PATH_TO_OFFICIAL_RESULTS.json
```

Do not submit files under `evidence/` or the fixture example directories as
evaluation results. Full native validation is NOT RUN; no model, GPU, simulator,
environment, or external service was launched for this deliverable.

Final CPU acceptance: 50 tests passed on Python 3.12.10, independently repeated
by the main agent. See `evidence/main-verification-tests.txt`,
`evidence/acceptance-summary.json` and `evidence/FINAL-REVIEW-FIXES.md` for the
current receipts. Earlier reviews intentionally retain findings from old
snapshots; the final fixes review is the current CPU verdict.

After an abrupt interruption, a `.run.lock` may remain. Verify the old runner
and its owned backend processes have stopped before manually clearing that
lock. Unresolved STARTED attempts still block the affected cell and require
evidence reconciliation; removing a lock does not authorize replaying them.

The forwardable resource request is `向队长和A索取的清单.md`. No real policy
results are included. The handoff ZIP is intended to overlay the supplied
workspace; it includes the two unchanged template/negative inputs needed by
the CPU tests, rather than a native simulator environment.
