# Independent runner/ledger review B — 2026-10-22

SPEC: **CHANGES REQUIRED**. QUALITY: **CHANGES REQUIRED**.

Reviewed frozen `review-runner-snapshot.txt`, SHA256 `6bee5bc4dcf98424d98ddfa2859ab4aec3aea8deae32cd481fd2682682bc2b39`, including evaluate.py, ledger.py, runner/ledger tests and synthetic backend. Integration probes used a single read of live aggregate_results.py SHA256 `f0c59ae127268cdf7106d4e64a70778f7ecd4ca8db8152fabb51fe2678be96e7`. These verdicts do not cover later moving runner fixes. No routine suite rerun, model/native simulator/GPU work, dependency changes or retained source modifications.

Repro command: `python lingbot/submission/evaluation/evidence/review-runner-probes.py` from workspace root. The script executes frozen source in memory, creates only temporary labeled CPU fixtures, runs bounded dummy Python processes, and removes its temporary records. No outputs are real policy results.

## Important findings

1. **Terminal evidence is lost for failures and rejected scenes.** Snapshot evaluate.py sections 194–215, 367–372 and 510–516. The subprocess wrapper buffers stdout/stderr, discards stdout on failure, truncates stderr to 4,000 characters and does not create either stream log. Timeout errors discard captured output too. Failure/rejection terminal records omit wall_seconds, actions_started, log_path and video_path, even though these outcomes require auditable evidence; any returned rejection telemetry beyond category/evidence is discarded. Probe prints all four fields missing and zero log files. Preserve raw streams in attempt-owned files, runner-measured elapsed time, any reported actions/video, and explicit unknown/unavailable values when a crash prevents measurement. Retain actual backend exit/timeout details and paths in immutable terminal records. Do not invent zero actions for a crashed worker.

2. **Fatal execution exits successfully.** Snapshot 631–634 discards `runner.run(...)`'s report and always returns 0. A synthetic backend `python -c 'import sys; sys.exit(9)'` produces an INFRA_ERROR and zero completions, yet `main(...)` returns 0. This prevents eval.sh/automation from detecting failed evaluation. Return a documented nonzero code for execution errors/incomplete requested work, preserving report files. Distinguish an intentionally selected completed subset from the global 100-cell coverage target.

3. **Exhausted budgets and deadlines have no explicit terminal reason.** Snapshot 456–488 and 535–538 silently break/skip. One candidate returning a valid EXPERT_UNSOLVED at budget=1 gives `status=PARTIAL, remaining_episodes=1, errors=[]`; simulated persisted stage expiration gives exactly the same fields with no attempted episode. Coverage retains the shortfall, but cannot explain whether work is blocked by candidate budget, stage deadline, cell deadline or awaiting execution. Persist/report separate stage/cell start/deadline/elapsed and explicit BUDGET_EXHAUSTED, CELL_DEADLINE_EXCEEDED, STAGE_DEADLINE_EXCEEDED states (including cells not started), keeping them outside policy success counts. The tests used a clock method substitution only to make expiration deterministic; no system clock was changed.

4. **Ledger permits fixture-to-real evidence relabeling.** Snapshot ledger.py 768–788 and 818–840 validate seven identity fields but omit evidence_kind; neither finish nor its reader compares it to STARTED/run configuration. The probe creates a fixture run config, a fixture STARTED, then calls finish with the same IDs and a real_policy terminal/child. All ledger checks pass, and stable aggregator f0c59... counts the record as one real episode because it excludes the fixture STARTED before pairing. This is a ledger API/integration defect; the current SerialEvaluator backend-response boundary separately rejects this mismatch, so this is not claimed as an exploit through the ordinary backend path. Include evidence_kind in immutable identity validation at write/read and reconcile terminal/run/STARTED evidence kinds before exclusion. Same principle applies to parent terminal versus nested episode kind.

5. **Timeout does not bound descendant processes or inherited output pipes.** Snapshot 194–205 uses subprocess.run timeout, which kills only the immediate backend. CPU repro backend launches a child `sleep(1.2)` inheriting pipes then sleeps itself; with requested timeout 0.15 seconds, evaluate returns only after 1.391 seconds. A long-lived child would extend the wait/resources further. Use a process group/job boundary and verified descendant cleanup on timeout, plus bounded log handling. Before native use, document model-server ownership and cleanup rather than claiming a hard process timeout from this wrapper. The probe's child exits itself; no native worker was launched or left running.

6. **Runner accepts malformed request scalar that aggregator rejects.** Snapshot 356–363 compares values using equality without checking types. Set chunk_index=True on the first valid request: SerialEvaluator._validate_episode accepts it because True == 1; stable aggregator rejects `request chunk_index must be an integer >= 1`. Float equivalents have the same equality issue. An adapter response can therefore be recorded as COMPLETE_POLICY and skipped on resume but fail final aggregation. Validate strict integer/non-bool chunk indexes and noise seeds consistently before immutable completion; also align video_review_status enumeration between runner and aggregator.

No Critical finding established. Fixture laundering is an Important boundary defect, and no actual policy score was produced during review.

## Positive findings and limits

Source inspection shows deterministic task/setting/seed episode IDs and request namespaces, configurable finite candidate budgets, same seed panel across stages/checkpoints, serial workers, configuration equality on resume, exclusive atomic record writes, integrity hashes on episode records, STARTED-before-backend, unresolved-start shard blocking, fatal-error shard blocking and no automatic fresh-seed replay after infrastructure failure. Only typed EXPERT_UNSOLVED/UNSTABLE_SETUP paths advance seeds. Scene rejection typing includes exact exception origin checks. Shared subprocess requests use seen/unseen instructions, full-limit intent, FP32, 50 actions/chunk, 10 denoising steps and noise 777 + chunk_index - 1.

Full action-limit authority remains delegated to the missing native adapter: the runner checks backend-reported step_limit equals backend-reported official_step_limit, without an independently loaded per-task limit. A loader also must validate actual artifact content against the package manifest; hashing manifest bytes is identification, not real model validation. These native dependencies are intentional NOT RUN boundaries, not additional claims of CPU proof. Process ownership, timeout recovery, native predicate/action-limit preservation and real interruption/resume require a later coordinated native receipt.

Scope metadata timestamps are stored with exclusive writes but lack the episode-record integrity hash; this is a smaller consistency gap to address when adding explicit deadline evidence. The stale lock after an abrupt host/process kill requires a documented manual ownership check/reconciliation procedure; automatically removing an active lock would be unsafe.

## Probe observations

```text
BUDGET status=PARTIAL remaining_episodes=1 errors=[] completed_episodes=0
REJECTION_MISSING_FIELDS wall_seconds actions_started log_path video_path
STAGE_EXPIRED status=PARTIAL remaining_episodes=1 errors=[] completed_episodes=0
FAILURE_MISSING_FIELDS wall_seconds actions_started log_path video_path
FAILURE_LOG_FILES []
FATAL_CLI_EXIT 0
FIXTURE_TERMINAL_EVIDENCE_KIND real_policy
FIXTURE_LAUNDER_COUNT 1
BOOLEAN_CHUNK_INDEX_RUNNER accepted
BOOLEAN_CHUNK_INDEX_AGGREGATOR request chunk_index must be an integer >= 1
DESCENDANT_PIPE_TIMEOUT_SECONDS 1.391 requested=0.15
```

The first stdout-preservation probe searched every JSON file and matched the literal command stored in run-config, which does not prove output retention. The evidence script now checks terminal/report contents instead; the direct source shows stdout is discarded on a nonzero exit. No claim of retained stdout is made.
