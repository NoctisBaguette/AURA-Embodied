# Current LingBot state — 21 October 2026, 19:06:05 Beijing watcher update

## Archive-reviewed update: shared three-hour cutoff confirmed

The newly supplied archive has now been inspected. The baseline-ready timestamp is16:05:48Beijing and the timeout log19:05:48; the interrupted bottle case began about one minute earlier. The shared three-hour stage limit caused this stop; there is no evidence here of a20minute bottle-case stall or renderer deadlock. The old ambiguity below is retained as the earlier status-only interpretation.

All28completed baseline episodes are preserved and independently checked, including their videos;3were successful. This is incomplete pilot evidence, not an official score.16commission receipts and cleanup/source-preservation receipts pass. Joint training did not start.

A separate captain-owned recovery release is prepared and CPU-checked, but NOT RUN on the server. It verifies original archive/source/checkpoint identities, repeats fresh admission/normal/16commission gates, imports the28completed records with provenance, and runs only the remaining4baseline episodes before training/candidate evaluation. The interrupted original seed restarts from setup in a new run; its earlier partial attempt remains unscored. The shared three-hour pilot limit is removed for bothbaseline/candidate; individual20minute case bounds and fatal/cancel guards remain. The old run/release stays intact.

A/B assignments and daily reports remain unchanged; both can work now. They do not need another handoff bundle for this runtime correction. Latest evidence: [progress/2026-10-21-timeout-reviewed.json](progress/2026-10-21-timeout-reviewed.json). Recovery execution and outcome are still pending; no automatic server deployment or monitoring occurred.

中文：新ZIP已确认是整个baseline的3小时上限中断了刚开始约1分钟的瓶子组合。28次已完成/3次成功的证据保留。独立恢复版本已通过CPU检查，尚未在服务器执行；验证后复用28次，仅补剩余4次，再训练/评测。A/B任务和日报不变。

## Earlier user-status interpretation (superseded above)


Source: captain-pasted status, not a new SSH query or independent run-archive review. This supersedes the earlier RUNNING / 8-of-32 snapshot.

| Item | Last reported value |
|---|---|
| Watcher | `wait-v6ie9xo8`, **FAILED** |
| Worker identity / held lease | False / False |
| Linked retained run | `run-L6iqyVGy`, **ERROR / BASELINE** |
| Simulator commissions | **16/16** |
| Baseline completed | **28/32**; success count not supplied |
| Candidate completed | **0/32** |
| Failed case | `baseline/14-pick_dual_bottles-clean` — manager timeout |
| Failed child record | RUNNING, zero completed episodes, seed 100000, no recorded rejection |
| Textures presence/header check | 1000/1000; no missing/extra/invalid files |

New joint training was not reached. The retained child RUNNING label is not a live process check. Actual cleanup must be checked in the new package. The review package is now `review-1792580758125196661.zip`; it has not yet been independently inspected.

## What the source establishes

The manager uses the earlier of a 20-minute case limit and a three-hour deadline for the entire baseline pilot, but reports both as “Simulator pilot case timed out”. Archive timings are needed to identify the exhausted bound. The stack's repeating 30-second “Timeout” entries are diagnostic dumps, not the manager's stop deadline. The final stack is in observer camera capture during policy actions; it does not prove a deadlock or identify a renderer defect. This is a timeout, not evidence that the earlier SIGSEGV recurred.

## Next work

Captain: inspect the new retained package for timing, 28 completed records, policy activity and cleanup before deciding a correction. Keep this failed run and completed evidence; do not restart the whole workflow or change limits based solely on this display. A and B continue their CPU assignments now; no new checkpoint is needed to start inventory/export or scheduler/aggregation work. B's new runner should distinguish case and stage deadlines without changing the frozen release.

The [complete bilingual guide](LingBot-Team-Complete-Guide-EN-ZH.txt) and source ZIP include this status. Daily reports through 23 October still apply. No teammate implementations/reports or successful final acceptance are claimed. There is no automatic runtime feed or deployment from GitHub.

Latest attributed snapshot: [progress/2026-10-21-baseline-028-timeout.json](progress/2026-10-21-baseline-028-timeout.json). Earlier 8/32 evidence remains unchanged as history.

中文：最新运行在 baseline 28/32 超时停止，训练尚未开始。20 分钟单组合与 3 小时阶段上限共用一条错误，需检查新包时间信息。A/B 的 CPU 任务继续，不等此次运行修复。
