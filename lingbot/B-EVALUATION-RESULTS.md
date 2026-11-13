# Owner B — 22–24 October

Extract from the complete bilingual guide; its shared interfaces and schedule also apply.

4. B — FULL EVALUATION, RESUME AND RESULTS

Your outcome: evaluate one fixed policy across the required task/setting grid, retain every actual outcome and resume without fabricating or duplicating results. You own the runner, ledger, aggregation and coverage/error reporting.

Read:
  official/results-template.json
  reference/runtime/joint50_common.py — results_document and conversions
  reference/runtime/joint50_sim.py — episode completion and scene rejection
  reference/runtime/manager.py — current pilot/gates/receipts
  reference/runtime/joint50_policy.py — policy request identity/behavior
  reference/configs/demo_clean.yml and demo_randomized.yml
  reference/commission-negative-example.json — must be excluded from policy results

First work session, target a reviewable draft in roughly four hours:
  1) Under submission/evaluation/, implement a CPU-only dry-run schedule for all 100 task/setting cells. No GPU/model/physics imports or launch in this mode.
  2) Include manifest SHA, task, setting, target episodes, seed plan, shard identity, unique episode/request IDs and output paths.
  3) Implement aggregator/validation tests using clearly marked fixtures and the real commissioning negative example. Return code, schedule and check outputs, with zero real episodes if only fixtures ran.

The current pilot hard-codes test_num=2, two-episode assertions and a 64-candidate bound. Parameterize a new runner; do not repeat the unchanged pilot and call it a full suite. A 64-candidate limit cannot deliver 100 valid episodes. Propose an explicit finite budget and seed policy for review before real execution, retaining every typed invalid-scene rejection. Infrastructure/model/planner failures remain terminal for the affected shard; do not hide them by trying fresh seeds.

Preserve official task success, full task action limits, clean/seen versus randomized/unseen instructions and the policy contract in section 5. Distinguish a completed policy failure, rejected setup and infrastructure crash. No task-specific controller tricks or per-task best-checkpoint mixture.

Each immutable record needs checkpoint-content identity, task/setting/seed, episode/shard ID, outcome, action count, elapsed wall time, log/video references and errors/rejections. A path alone is not checkpoint identity. Resume must retain old records, deduplicate identical episode identities, reject conflicting duplicates/mixed checkpoint hashes and keep request IDs unique. Review shared policy-server/cache behavior before adding concurrent workers.

THREE-DAY PRIORITIES FOR B
P0 tonight: a CPU schedule for all 100 cells, ledger/aggregation implementation, a failure-review table, and exact missing real-evidence requests. Start failure review on the captain-provided baseline videos as soon as they arrive, while training continues.
P0 by 23 October 12:00: runnable runner/aggregation draft with resume identity checks and actual CPU evidence. Return partial code even if A integration is blocked. Keep the real episode count at zero for fixture-only runs.
P0 by 23 October evening when resources are available: one real cell using A's loader, safe resume demonstration, measured throughput and a concrete estimate of coverage achievable by the 24th. Multi-GPU concurrency is optional only after model lifetime/cache/resource behavior is reviewed; no assumption of four available GPUs.
P0 by 24 October 20:00: executable parameterized runner, actual result/coverage/error ledgers for the selected fixed policy, comparison evidence and reproduction commands. The full target remains 10,000 episodes, but completing them in three days is NOT promised. Report the measured shortfall early; the captain checks organizer handling. Do not fabricate counts or quietly treat partial coverage as a complete suite.

FAILURE REVIEW THAT DIRECTLY HELPS THE MODEL DECISION
Create failure-review.csv or an equivalent table: checkpoint hash, task/setting/seed, success flag from the official predicate, video/log path and inspected timestamp/frame, observed behavior, possible cause, confidence, and one discriminating next check. Review all available pilot failures; first inspect at least one failure per failing task/setting and the successful examples for contrast. Distinguish wrong arm/target, failure to reach, gripper/grasp, dropped object/placement, action-budget exhaustion and infrastructure failure. Multiple labels and UNKNOWN are allowed. An observed missed grasp is not proof of a training-data or coordinate bug.
With A, check input ordering, image/state preprocessing, normalization, action dimensions and complete checkpoint restoration against real producer/consumer code and parity evidence. Never change official success predicates, hide failures, hard-code task-specific actions, or choose a different checkpoint per task.
When candidate results arrive, compare the same task/setting/seed panel and one fixed checkpoint at a time; keep failures and caveats. If candidate results are unavailable, say PENDING. If it underperforms, send evidence to the captain for a fallback/correction decision; do not automatically promote it because it trained longer.

Required checks and delivery:
  • Cover true AND false task_success, including NumPy bool; duplicate/conflicting records; wrong checkpoint hash; unexpected task/setting; malformed counts; partial/error reports; fixture and commissioning exclusion.
  • Match all 100 official cells, with integer counts and 0 <= successes <= attempts. Keep actual partial counts and separate coverage/error/remaining-work ledgers. Do not average percentages as a replacement for counts.
  • Separate baseline and candidate. Production results contain only actual completed learned-policy episodes. Commissioning is explicitly NO_MODEL_TRANSPORT_COMMISSION, episodes=[], policy_actions_executed=0; it is never a success score.
  • Before full rollout, run one coordinated real cell through A's fresh loader and demonstrate safe interruption/resume. Measure throughput including startup, scene setup and inference; estimate remaining wall time/workers from real measurements. Do not promise 10,000 episodes will fit before measuring.
  • Return runner/configs, dry-run schedule, aggregator/checks and logs, real results when available, coverage/errors, failure-video references and exact commands. Keep synthetic fixture outputs outside final submission results.

4. B：全量评测、续跑与结果

目标：让一个固定策略覆盖所有任务/设置，保留实际结果，续跑时不重复、不造分。你负责 runner、episode ledger、汇总及覆盖/错误报告。

先读：
  official/results-template.json
  reference/runtime/joint50_common.py：results_document 与转换
  reference/runtime/joint50_sim.py：episode 完成与场景拒绝
  reference/runtime/manager.py：当前 pilot、门槛和回执
  reference/runtime/joint50_policy.py：请求身份与策略行为
  reference/configs/demo_clean.yml、demo_randomized.yml
  reference/commission-negative-example.json：必须排除在策略成绩之外

第一轮工作，争取约四小时内交 CPU 草稿：
  1）在 submission/evaluation/ 实现 100 个 task/setting 组合的 CPU dry-run 调度，不导入或启动 GPU/model/physics。
  2）计划包含 manifest SHA、task、setting、目标次数、seed 计划、shard 身份、唯一 episode/request ID 和输出路径。
  3）用明确标记的 fixtures 和真实 commissioning 反例实现汇总/校验。交代码、计划和检查结果；如果只跑样例，真实 episode 就是 0。

现有 pilot 写死 test_num=2、两次 episode 断言及 64 个候选 seed 上限。应在新 runner 参数化，不能重复调用旧文件后称为全量方案。64 个候选不可能产出 100 个有效 episode。提出明确有限的候选预算和 seed 方案，在真实执行前交审查；保留所有有类型的无效场景拒绝。基础设施、模型或 planner 错误应让对应 shard 终止，不能换 seed 偷偷掩盖。

保持官方成功判据、完整任务动作上限、clean/seen 与 randomized/unseen 指令设置以及第 5 节策略契约。区分“完整执行但策略失败”“初始化场景被拒绝”“基础设施崩溃”。不能做按任务特调控制器或拼接各任务最优 checkpoint。

不可覆盖的记录应含：checkpoint 内容身份、task/setting/seed、episode/shard ID、结果、动作数、墙钟时间、日志/视频引用及错误/拒绝原因。相同路径不等于相同权重。续跑保留旧记录，去重相同 episode 身份，拒绝冲突重复和混合 checkpoint 哈希；请求 ID 全局唯一。并发前审查共享 policy server/cache 行为。

B的三天优先级
P0今晚：100组合CPU计划、ledger/汇总实现、失败复盘表和准确缺证据请求。baseline视频一到就开始看，不等训练结束。
P0，23日12:00前：可运行的runner/汇总草稿、续跑身份校验及真实CPU检查证据。A接口未接好也交已有代码；只跑fixtures时真实episode数为0。
P0，资源允许时23日晚：接A加载器跑一个真实组合，演示安全续跑，测吞吐并估24日前可完成覆盖。并发是可选优化，先审查模型生命周期/cache/资源行为，不假设有4张可用GPU。
P0，24日20:00前：可执行参数化runner，选定固定模型的真实结果/覆盖/错误清单、对比证据和复现命令。全量目标仍是10,000次，但不承诺三天内跑完；尽早报告实测缺口，由队长确认主办方处理。不能造计数或把部分覆盖说成全量完成。

直接帮助模型决策的失败复盘
建立failure-review.csv或等价表：checkpoint哈希、task/setting/seed、官方判据的success标志、视频/日志路径与已查看时间点/帧、观察到的动作、可能原因、置信度、一个能区分原因的下一步检查。复盘所有可获得的pilot失败；先覆盖每个失败task/setting至少一条，并看成功样例作对照。区分错臂/错目标、到达失败、夹爪/抓取、掉落/放置、动作预算耗尽、基础设施失败；允许多标签及UNKNOWN。看到“没抓住”不等于证明数据或坐标系有错。
与A对照真实producer/consumer及一致性证据，检查输入顺序、图像/状态预处理、normalization、动作维数及完整权重恢复。不能改官方成功判据、隐藏失败、硬编码按任务动作或逐任务选不同checkpoint。
candidate结果到后，按相同task/setting/seed面板和单一固定checkpoint比较；保留失败及限制。未到就写PENDING。若更差，提交证据让队长决定fallback或纠错，不因训练步数更多就自动采用。

必做检查与交付：
  • task_success 的 true/false（包括 NumPy bool）、重复/冲突、错误 checkpoint 哈希、未知 task/setting、非法计数、未完成/错误报告、fixtures 与 commissioning 排除。
  • 准确对应官方 100 个组合；整数计数满足 0 <= successes <= attempts。未完成项保留真实部分计数，另给覆盖/错误/剩余队列，不能用平均百分比冒充计数。
  • baseline/candidate 分开。正式结果只计真实完成的学习策略 episode。commissioning 记录为 NO_MODEL_TRANSPORT_COMMISSION、episodes=[]、policy_actions_executed=0，不能当成绩。
  • 全量前，用 A 的新进程加载器跑一个真实组合，并验证安全中断/续跑。吞吐测量包括启动、场景设置和推理，再估剩余时间/worker 数；未测量前不能保证 10,000 次一定赶得上。
  • 交 runner/config、CPU 计划、汇总器/检查/日志、已有的真实 results、覆盖/错误清单、失败视频引用和准确命令。样例输出放在正式提交结果之外。
