# Owner B — Full-suite evaluation, resumption and trustworthy results

目标：让一个固定checkpoint能覆盖50任务×clean/randomized，输出可追溯结果；崩溃、未完成、重复数据不能变成假分数。

## First4hours — CPU work now

1. Read official/results-template.json, `joint50_common.py` results_document, `joint50_sim.py` episode finish/rejection logic and `manager.py` pilot. The existing pilot is8tasks×2settings×2episodes; it is not the full-suite runner.
2. Implement a dry-run scheduler for all100(task,setting) cells with no GPU imports/processes. Record proposed checkpoint manifest SHA, task, setting, target episode count, seed schedule, shard identity and output path. CLI names are in INTERFACES.md. The100episodes/cell target is10,000policyepisodes total.
3. Implement and test aggregation/validation from immutable episode records. Use the actual commission-negative-example.json to prove commissioning is excluded. Put synthetic test episodes under a clearly marked fixtures directory and reject that marker in production aggregation.
4. Deliver a finite/resumable execution design and exact extra compute requirement. Do not launch additional GPU workers or contend with the captain's model process.

## Implementation boundaries

Extend the task list and parameterize episode count in a new submission runner. Inspect hard-coded test_num=2, final two-episode assertions, the64candidate bound and IDs in the current pilot; do not just run the unchanged file100times. Propose an explicit finite candidate budget adequate for the requested episode count, preserving typed invalid-scene handling and recording every rejection. Changes to bounds/seed policy need review before GPU execution. Infrastructure errors remain terminal for that shard; no automatic retry that hides a fatal seed.

Use the installed full task action limit, official success predicate, seen instructions for clean and unseen for randomized. Preserve14Dstate/commands,50actionchunks,10denoisingsteps, exact preprocessing and zero-padding. No task-specific controller tricks or per-task best-checkpoint selection. Distinguish completed policy failure from setup rejection and infrastructure crash.

Records must carry immutable checkpoint-content identity, task, setting, seed, episode/shard ID, outcome, action count, elapsed wall time, video/log paths and failure/rejection details. The original pilot uses a checkpoint path; add content identity rather than assuming equal paths mean equal bytes. Do not overwrite records during resume. Deduplicate the same checkpoint/task/setting/seed and detect conflicting duplicates. Use unique request episode IDs across workers. Shared policy-server/cache behavior must be reviewed before enabling concurrency.

## Acceptance and output

- Tests cover task_success true/false including NumPy bool, duplicate/conflicting episodes, mixed checkpoint hashes, unexpected task/setting, malformed counts, partial/error reports, synthetic fixtures and commissioning exclusion.
- Match the official100cells exactly. Integer0<=successes<=attempts; retain actual counts for unfinished cells. Do not use an average of task percentages as a substitute for counts or infer success from an image.
- Keep baseline and candidate separately. Full evaluation is for the selected frozen policy, never a mixture of per-task winners. Emit a separate coverage/error ledger and queue of remaining work.
- Before full rollout, one coordinated end-to-end cell and resume interruption must work through A's fresh loader. Then measure throughput including model/simulator startup and inference; give total remaining hours versus available workers.
- Required delivery: runner/config, CPU dry-run manifest, aggregator/tests, results.json for REAL completed episodes only, coverage/error ledger, and links to real failure videos. Keep fake fixture outputs outside the submission tree.

Suggested branch: lingbot/full-evaluation. The deadline requires honest partial coverage if full completion becomes infeasible; captain must confirm organizer handling rather than silently changing counts or claiming completion.

## Daily progress through 23 October / 每日进度到 23 日

Use 06-DAILY-REPORT-EN-ZH.txt. Send the captain a brief report each day, including when blocked; AI drafting is fine if checked against real files/logs. Proposed check-ins: 21/22 October 22:00 and23 October 12:00, Beijing. Include remaining hands-on effort, missing inputs and takeover-ready partial code/commands by the 23rd. Report critical blockers immediately.

每天汇报完成项、真实验证、剩余工时、阻塞和接手说明；可用 AI 起草，但本人核对。建议21/22日22:00、23日中午12:00北京时间，最后一天附当前代码及命令，以便下午补进度。
