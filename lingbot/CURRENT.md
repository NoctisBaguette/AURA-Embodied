# Latest — 25 October: portable precision mismatch identified; corrected replay pending

Native two-loader evidence shows identical parameter/buffer fingerprints and model inputs. Original loader exactly matches its reference; portable repeats consistently but differs in actions. The upstream constructor overwrote the portable loader's early highest setting with high/TF32. The corrected portable loader reapplies highest after construction/restoration and guards each prediction; mismatch evidence is retained in full. See submission/portable/README.md. Public code checks:27 existing portable tests plus2precision-contract CPU checks pass. Corrected GPU replay and the captain's four laptop development episodes remain NOT RUN. No server deployment occurs from this branch. The prior6/32candidate result is unchanged; this packaging defect does not explain earlier original-loader task failures.

中文：已定位可移植加载器精度设置被构造函数覆盖的问题。权重和输入相同，原加载器精确匹配参考。新版调整顺序并在推理时检查，仍需真实GPU验收；没有重新训练或修改旧6/32结果，GitHub更新不自动启动服务器。

# Latest — 24 October: completed candidate evidence reviewed

The reports-only final archive has been checked: all 490 included manifest hashes match, all 29 runtime payloads match the reviewed release, and all 64 baseline/candidate episode records reconcile. Final state is COMPLETE/FINISHED with exit code 0, completed policy reports, unchanged parameters/buffers, and passing restore/replay receipts.

Candidate: 6/32 successes. Baseline: 3/32. Candidate successes are bell 4/4, laptop 1/4 and bottles 1/4; all 26 failures reached full action limits. Only 29 exact scene seeds match across stages, and all three added successes occur among those matches. This is an eight-task pilot, not an official full-suite score. Candidate videos and NPZ files are absent from the smaller archive.

B is unavailable tonight. Captain/assistant own native adapter and portable integration; B can review videos when awake. This supersedes the earlier two-working-hour adapter assignment. Portable native qualification and reproducible submission entrypoints remain pending. See the dated candidate final report review. This documentation update performs no deployment or GPU execution.

Earlier observations below are historical.

# Latest — 23 October 19:55 Beijing: candidate progressing; B CPU integration reviewed

Captain-pasted status, not an independent server query: fixed-checkpoint candidate23/32 completed with5successes; baseline32/32 with3successes;16nativecommissions. Current child progresses through stack_blocks_two randomized, seed100001,591actions, about1second since progress. Candidate restore and the separate later offline replay both PASS; no new training. Header timestamps/older probe pointers are historical. Evaluation remains RUNNING; no final coverage or broad improvement established. Four candidate successes are bell and one is randomized open_laptop.

B's uploaded CPU handoff contains useful schedule/ledger/aggregation code and explicitly no native adapter. Original50CPUtests reproduce. Integration revision under submission/evaluation passes57CPUtests on Python3.12.14: align package-manifest.json with the actual portable exporter, validate full package before backend startup, require explicitUTF8 transport, reject setup rejections carrying policy attempts/results, and separate runner wall time. Tests are CPU fixtures; real exported portable package, model loading, native adapter/rollouts, submission entrypoints and full evaluation remain pending.

The separate private team ZIP now supplies four genuine baseline videos,31full episode records and32compact records, plus a review CSV, unchanged sources, and bilingual next steps. B can immediately analyze videos and implement the native bridge while A/captain finish owned runtime evidence and portable qualification. Never commit that private evidence to this public repository. See reviews/2026-10-23/B-INTEGRATION-EN-ZH.txt and submission/evaluation/BACKEND-CONTRACT.md. This review branch does not deploy or modify the active server release.

# Latest — 23 October Beijing: early candidate evaluation requested; portable takeover

Captain terminal observation at 22 October 17:24:51 UTC: run-AQMVYnGr RUNNING/JOINT_TRAINING, baseline32 completed/3successes, candidate0, update24880/samples49760. Existing STOP_TRAIN receipt accepted; the second status about18seconds later is not proof of failure or completion. Post-loop diagnostics/checkpoint/restore then candidate32 are still pending. No restart or new training requested.

Captain authorizes taking over A overnight. This branch implements strict export and fresh-process loader/parity under submission/portable;27CPUboundary checks pass, real Torch/CUDA/model/portability NOT RUN. See reviews/2026-10-23/READ-FIRST-EN-ZH.txt and RESEARCH-EN-ZH.txt. Original A ZIP and running server release remain unchanged. No teammate was contacted. The integration base retains prior status until this review is accepted; this is a manually dated observation, not live monitoring.

## Latest — 22 October: training23,300; A handoff reviewed; real baseline visuals available

Captain-pasted status reports RUNNING / JOINT_TRAINING,16commissions,32baseline completions,0candidate completions;23,300/50,000updates and46,600samples. Latest batch loss0.0407627 is not a task-success measure. No fresh server query was made.

A's original22October ZIP is received. Independent repetition confirms7/7synthetic tests, but the real loader is not implemented and fresh-process parity has not run. Focused review reproduces incomplete-manifest/identity acceptance, ambiguous projection names, malformed tensor-payload acceptance, asset collisions, partial export and incorrect rejection-test success propagation. See reviews/2026-10-22/01-A-REVIEW-EN-ZH.txt. Old fallback(batch4/fivefiles) and new joint continuation(batch2/sixfiles) require distinct schemas; this corrects the earlier handoff ambiguity.

Recovered baseline evidence:31completed episodes/3successes(allclick_bell); no current candidate result. Real camera samples show failed grasp/dual-arm sequencing. Independent inverse normalization/mapping reproduces24retained bottle chunks exactly and their simulator float32 casts; this does not qualify the full encoder or policy. Across31episodes, tracking RMSE0.124–1.826degrees versus drive targets;2TOPPexceptions among34,116calls. Full unchanged example videos, real baseline input/output/noise, exact normalization and metadata are supplied in the new direct handoff ZIP.

A fixes packaging and implements full loading; B analyzes real failures while finishing evaluation/resume/aggregation. Read reviews/2026-10-22/00-READ-FIRST-EN-ZH.txt. Internal24October deadline and daily reporting remain. Captain-only optional early transition to candidate evaluation uses the current trainer's existing graceful stop; it is prepared/CPU-checked, NOT executed by the reviewer. It ends this training stage rather than automatically resuming unused updates. No runtime code, dependency, seed, success rule or active worker has been changed here.

Earlier observations below are historical.

# Current LingBot state — 22 October 2026, Beijing

## Team delivery update — 24 October internal finish

The captain confirms the teammate guide has not yet been sent and sets24October as the internal final date. The revised complete guide uses24October20:00Beijing as an explicit planning assumption, with23October12:00partial-code handoff and24October12:00readiness/checkpoint decision. A owns complete export/load/reproduction; B owns evaluation/resume/results plus immediate failure-video review. Reports22/23October22:00, final report24October20:00; late recipients follow the guide's two-hour initial-status rule.

Use `LingBot-Team-Complete-Guide-EN-ZH.txt` and `deliverables/LingBot-AURA-Workspace-20261022.zip`. No teammate implementation or native acceptance is claimed. The older guide/bundle is superseded for onboarding. Current public structured evidence: `progress/current.json` and `progress/2026-10-22-training-5420-user.json`; reference status files remain historical.

The three-day goal is a verified, reproducible selected policy and honest results; improved policy performance and completing10,000episodes are not guaranteed. The captain will review baseline failures now and candidate evidence when ready, preserving the fallback. This document does not change the active server workflow or official deadline.

中文：队长尚未发送旧说明，内部完成日改为24日。本计划具体按北京时间24日20:00安排，23日12:00先交代码草稿，24日12:00检查就绪并决定模型。A做完整打包/新进程加载，B做评测/续跑/汇总并马上复盘已有失败；22/23日晚日报，24日最终交接。使用22日新版说明与ZIP。不能承诺三天内模型提升或跑完10,000次，不改当前服务器流程或官方截止。

## Latest: baseline complete; joint training is running

Source: captain-pasted server status received on 22 October 2026, Beijing. Exact observation time is not supplied. This is a manual status update, not a live SSH query or an independent audit of the new run archive.

| Item | Reported state |
|---|---|
| Workflow | RUNNING / JOINT_TRAINING |
| Simulator commissioning | 16/16 complete |
| Baseline policy episodes | 32/32 complete; completion does not mean task success |
| Training updates | 5,420/50,000 maximum |
| Consumed training examples | 10,840/100,000 maximum; batch size 2 |
| Latest batch loss | 0.11704578250646591 |
| Candidate policy episodes | 0/32; evaluation follows training |

Training is 10.84% of the maximum update/sample budget. The update loop also has a 22-hour budget; it can stop earlier than 50,000 updates. Post-training checkpoint save/restore checks and 32 candidate episodes follow. Neither 22 hours nor the maximum update count is an end-to-end ETA. This snapshot lacks the training elapsed time needed for a credible throughput estimate.

The baseline's 0/2 lines are task failures. Batch training loss is not a task-success score; improvement must be assessed in candidate evaluation. The current run has passed the previously failing baseline boundary, but this does not prove the intermittent native crash is eliminated.

Some status fields retain earlier stages: MODEL_LOADING is the admission receipt, and the last pilot record is historical baseline progress. Current phase and training update counters establish the reported training state. The advertised package now belongs to the current attempt but is still intermediate.

A/B: continue the same portable-package and evaluation-runner assignments. No new onboarding ZIP is needed. Today's report target is 22 October 22:00 Beijing; the 23 October 12:00 handoff includes current code even if incomplete, exact commands/evidence, blockers and takeover steps. No teammate completion or actual GPU acceptance is claimed. This repository update does not deploy to or restart the server.

中文：队长最新状态显示，16/16仿真准备检查和32/32 baseline已完成，现已进入联合训练。已完成5,420次更新、消耗10,840个训练样本，达到50,000次更新/100,000样本上限的10.84%。训练循环还受22小时预算约束，可能先达到时间预算；之后仍有checkpoint校验和32次candidate评测，不能把22小时当作整个流程的完成时间。32次完成不代表32次成功，日志里的0/2是任务失败；loss也不是机器人任务成功率。当前已通过之前中断的baseline边界，但不能据此声称间歇性崩溃根因已解决。MODEL_LOADING和最后的pilot记录属于较早阶段；以当前JOINT_TRAINING及更新计数判断。A/B继续原任务，22日22:00前交日报，23日12:00交可接手代码与未完成项，无须重发入门包。

## Earlier: 31 completed episodes verified; targeted recovery prepared

Source: independent inspection of the captain-supplied recovery archive, not a live SSH query. All31 completed policy episodes and their videos validate:3task successes and28task failures. The final randomized bottle case completed its first episode as a failure; its next candidate has no completed record. Joint training has not started. Cleanup/source-preservation receipts pass.

The actual stop was SIGSEGV about five minutes into the case. A recurring diagnostic stack dump ended partially; native cause remains unproved. A separate captain-owned recovery-v2 is prepared and CPU-checked. It removes recurring asynchronous stack dumping, retains31records with provenance, and resumes the interrupted candidate once after fresh qualification and policy identity checks. Once32baseline episodes complete, the existing jointtraining/candidate workflow proceeds. Native recovery-v2 has NOT RUN; this is a mitigation, not a demonstrated fix.

A/B assignments and reports through23October continue. There is no need to wait, obtain a new checkpoint for CPU work, or redistribute the onboarding bundle. The captain's server runtime remains separate from this repository; this update does not deploy or launch it.

中文：已独立检查新归档，确认31次完整episode及视频：3次任务成功、28次失败。最后一个随机瓶子组合的首个episode已完整失败，下一候选尚未完成；训练还未开始。新恢复版本已通过CPU检查：移除周期性异步堆栈转储，保留31次结果，经过新资格检查后仅补未完成候选，再进入训练和候选评测。服务器尚未执行新版，根因仍未证实。A/B继续任务与截至23日的日报，不需要重发入门包。

## Earlier snapshots (superseded)

# Current LingBot state — 21 October 2026, 22:14:03 Beijing watcher update

## Latest: recovery stopped with a native crash

Source: captain-uploaded status transcript; no fresh SSH query or independent review of the new run archive. This supersedes the recovery-not-run state retained below.

The recovery ran and completed fresh simulator commissioning (16/16). The parent recorded 30/32 baseline episodes. The final randomized bottle case then exited with SIGSEGV (-11); its last progress record was about five minutes into a 20-minute case limit, with no shared stage deadline. Joint training did not start; candidate evaluation remains 0/32.

The failed child recorded one additional completed episode, logged as a task failure. It is pending archive validation and parent integration: do not describe this as 31 validated episodes or 31 successes. The next candidate seed was recorded but did not complete. Native root cause and complete cleanup evidence remain unverified. A partial diagnostic stack does not identify the faulty library.

Captain is reviewing this new failure before a targeted next action. A and B continue their existing CPU assignments and daily reports; there is no need to redistribute the onboarding bundle or wait for a new checkpoint. No new restart or runtime change accompanies this status update.

中文：恢复运行已执行，16/16 仿真准备检查完成；父进程记录 baseline 30/32。最后一个随机化瓶子组合约运行5分钟后发生段错误（SIGSEGV），没有触发20分钟上限。子进程另外记录了1次已完成但任务失败的episode，仍需检查新归档，不能声称31次均已验证。训练尚未开始，根因未确定。A/B继续原定CPU任务与日报，不需要等待，也不用重发入门包。

## Earlier snapshots (superseded by the update above)

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
