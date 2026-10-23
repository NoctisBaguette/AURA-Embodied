# B 所需输入：可直接转发

依据：工作区根目录 LingBot-Team-Complete-Guide-EN-ZH.txt 中文第 2、4、5、6 节。已核对该文件与 lingbot/ 内同名文件 SHA256 相同：07b7eeab…6f10a9bb。以下日期均为北京时间，属于团队内部安排。

目前我们只有源码和模板；队长和 A 尚未提供实际资源。B 的 CPU 调度、记录、续跑和汇总继续开发，不等最终 candidate，也不需要把训练数据全部下载到电脑。

## 发给队长：现在最先要

1. **真实 baseline 证据包/获准私有目录**：全部已完成 episode 的 JSON 报告（不是状态截图或汇总百分比）、每条的 task/setting/scene_seed、官方 task_success、checkpoint 内容哈希、动作数/完整动作上限、视频、日志、wall time、planner/执行 telemetry。已报错的分片、scene rejection 和已有成功样例也一起保留；有缺项就列缺项，不要只给筛选后的失败视频。
   - 用途：现在开始失败复盘，核实真实计数、覆盖和对照；缺视频只能记 NOT REVIEWED。
   - 最晚：尽快，争取 10 月 23 日 12:00 草稿前收到第一批；可以分批，不用等 candidate。
2. **权威 50 任务/配置与当前实际评测源码身份**：确认 ZIP 内 official/results-template.json 的 50 任务是否就是此次权威清单；提供实际使用的 clean/randomized config、aloha-agilex robot config、各任务完整 action limit 的来源，以及 LingBot/RoboTwin/eval_policy 的 commit 或源码哈希。当前 recovery-v2 运行封装如和 reference/ 不同，请给准确版本/入口。
   - 用途：实现真实仿真 backend；不能把阅读快照或 2-episode pilot 当全量运行入口。
   - 最晚：首次真实联调前，目标 10 月 23 日晚。
3. **获准运行位置和资源安排**：在哪台已配置环境执行、Python/conda 环境、准确工作目录/依赖及 import 检查回执；队长安排的 GPU/时间窗口、资源 gate、允许的单组合/阶段时限。可以由队长在服务器执行命令并回传证据，不要求把 SSH 密码发给 B。
   - 用途：先跑一个真实组合，测启动+场景设置+推理+录制的总吞吐并验续跑。
   - 最晚：首次真实联调前，目标 10 月 23 日晚；不重启/抢占当前训练。
4. **评测方案确认**：B 提议每组合目标 100 个完整策略 episode、最多 1000 个候选 scene seed，从 100000 依次增加；clean 用 seen 指令，randomized 用 unseen；先串行。只有符合原规则的有类型场景拒绝才能换 seed，模型/基础设施/planner 故障终止分片。请确认候选预算和分片/阶段时限是否接受。
   - 最晚：真实执行前；目前只用于 CPU 计划。

## 发给 A：现在对接口，随后交包

1. **可接手的导出器/加载器代码与准确命令**：加载函数/CLI 签名、manifest 文件名/schema、错误如何返回、模型生命周期/cache 由谁管理，A 的 eval.sh 如何调用 B。先交已有代码和依赖缺口，不要等最终模型。
   - 最晚：现在对齐接口，10 月 23 日 12:00 前给可运行草稿。
2. **一个不可变、完整、可联调的模型包及 manifest SHA256**：可以是保留 fallback 或已完整保存的中间 checkpoint；不要 .partial，也不能仅 adapter。需覆盖准确 base revision、adapter、五个 projection 的全部 weight/bias、persistent buffers/model step、processor/tokenizer/config、clean50 normalization、预处理/zero-padding、推理设置及所有外部资产身份。给出准确包位置和读取方法；大文件走队长批准的私有存储，不进公开 GitHub。
   - 最晚：10 月 23 日晚首次真实联调前。最终冻结策略由队长决定，目标 24 日 12:00。
3. **真实新进程加载及一致性证据**：实际 checkpoint 身份、tensor/buffer/model-step 恢复核对、固定输入/固定噪声/参考输出、normalized (1,50,55) 与 decoded (50,14) 的最大误差和容差、准确命令/依赖/真实日志。CPU fixture 或同进程保存再恢复不算这项验收。
   - 最晚：全量真实评测前；目标 10 月 23 日晚单组合联调时具备。
4. **明确推理契约**：三路 RGB 240×320×3 uint8，14D float32 状态，语言指令；FP32、50 动作/chunk、10 denoising steps、每请求固定噪声身份；输出有限。接口必须允许完整任务动作预算，不能沿用旧 pilot 的 chunk<=40 上限。
   - 用途：B 的原生 backend 对接；最晚首次真实联调前。

## 队长后续还需给

- candidate 完成后的同 task/setting/seed 面板原始报告、视频/日志与固定包身份，供和 baseline 比较；没完成先写 PENDING。
- 正式 team_id、最终选定单一 checkpoint/manifest SHA、正式提交要求/公告核对结论。24 日 20:00 是本计划内部交付点，不冒充主办方截止。
- 如果基于实测吞吐无法完成 10000 次，请队长决定资源与如何向主办方处理覆盖缺口；B 不造数、不把部分覆盖叫全量。

**对方暂时交不出来时，请至少回复：缺哪个具体文件/权限、负责人、预计何时能给、可先替代的完整 fallback 或已完成证据。**

B 当前真实 episode=0；吞吐/剩余原生执行时间 UNKNOWN；真实加载、仿真、视频复盘、candidate 比较均未完成。收到资源后按「核对身份 → 一个真实组合 → 中断/续跑验证 → 测吞吐 → 决定扩大覆盖」推进。
