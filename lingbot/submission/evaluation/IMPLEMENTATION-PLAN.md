# B evaluation implementation plan — 2026-10-22

Goal: reviewable CPU runner, immutable ledger, safe resume and official-schema aggregation; real rollout requires captain-supplied runtime and A package.
Architecture: Python standard library scheduling/ledger/CLI, a serial subprocess backend boundary, separate fixture evidence and production records.
Spec: ../../B-EVALUATION-RESULTS.md, ../../INTERFACES.md and complete team guide section 4–6.

## Global constraints

- reference/ and official/ remain read-only. No GPU/simulator launch, environment upgrade, training or deployment.
- Exactly 50 official tasks × clean/randomized; default 100 completed policy episodes/cell.
- One manifest content SHA per run; baseline/candidate separated; no commissioning or fixture scores.
- Full official action limits, seen/unseen instructions, FP32, 50 action chunks, 10 denoising steps; no per-task shortcuts.
- Proposed seed budget: 1,000 candidates/cell for 100 completions (configurable >= target); sequential seeds from 100000, same panel across checkpoints; only typed invalid setup permits next seed. Requires captain review before native execution.
- Immutable started/terminal records, deterministic episode identity, globally unique per-chunk request identity, conflict rejection and fail-closed interrupted attempts. Serial workers only.
- Every unavailable native check is NOT RUN; real episodes = 0 for CPU fixtures.

## Task 1: CPU implementation (one cohesive testable deliverable)

Files: evaluate.py, aggregate_results.py, focused library modules, tests/, configs/, README.md, BACKEND-CONTRACT.md, fixtures/ under this directory.

1. Read real producer/consumer files listed in the B task card before defining schema.
2. Write meaningful failing unittest tests for schedule (100 cells), bool success (including numpy.bool_ when installed), ledger identity/dedup/conflicts, hash mismatch, unknown cells, malformed counts, partial reports, commissioning exclusion, fixture exclusion, terminal crashes and interrupted resume. Run red, save evidence.
3. Implement CPU CLI `evaluate --policy-package PATH --tasks-file PATH --setting clean|randomized|all --episodes N --output PATH --resume --dry-run`; explicit fixture-only SHA mode allowed, never called real load. Generate plan with manifest SHA, target, budget, seeds, shard/episode/request namespace, outputs, instruction type. No torch/sapien/model imports.
4. Implement immutable ledger with atomic exclusive writes and run lock, unchanged run configuration validation, deterministic candidate IDs; persist STARTED before backend call and terminal outcome afterward. Unresolved STARTED blocks shard instead of replaying actions. Infrastructure/model/planner failures terminate shard; typed UNSOLVED_SCENE/UNSTABLE_SETUP only may advance seed. Process timeouts bound cell and stage, preserve partial evidence. Native backend boundary is explicit, missing adapter fails clearly; do not pretend the reference pilot is a native full evaluator.
5. Aggregator validates counts/identities/status before counting real completed learned-policy records. Produce official counts, coverage/errors/remaining queue separately; retain actual completed records within partial/error report envelopes. Reject conflicting duplicates, request reuse, mixed stage/hash. Fixture and commissioning excluded with reason counts.
6. Run tests green and CLI schedule/zero-real aggregation demonstrations, save concise exact commands/results as CPU evidence. Document API, backend startup/timeout ownership, limitations, missing native adapter/A integration.

## Task 2: independent review and fixes

Reviewer reads implementation package and spec, returns separate spec and quality verdicts with precise findings. Implementer fixes important issues with regressions, reviewer rechecks fixed scope. Main agent independently checks schedule, negative examples, records and protected source hashes.

## Task 3: handoff

Main agent writes B report, failure-review CSV schema, exact missing inputs/latest-needed checkpoints, remaining estimate and runnable commands. Preserve plan, evidence and review; directory is a ZIP extraction, no git repository or branch operations required. No publication or contact messages.
