# AURA 前沿观察：当前研究雷达

[English](CURRENT.md) · [中文阅读入口](README.zh-CN.md)。**更新：2026-10-29。**

**最新材料：**[10月29日中文周报](2026/2026-10-29.zh-CN.md) · [English watch](2026/2026-10-29.md) · [HQ/Core/队友中文交接](2026/2026-10-29-handoff.zh-CN.md) · [英文交接](2026/2026-10-29-handoff.md)。

## 当前执行结论

**M9a 暂不改变。**权威工程分支是 **06-01/aether-cl-m0**，核对头 cd8185dbe36676c1edd90031e13a105795b617d5。[Core 连续性 v0.2](../coordination/BAGUETTE_Core_Research_Continuity_v0.2.md)确认 02W 的 M9 设计包已经返回，已进入狭义的**非特权 RGB/RGB-D/本体感知验证器 commissioning**。[相机记录](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md)保留源文件检查和报告层错误修复，但**未证明真实相机渲染/物理不扰动性验收，也未证明新 M9a 正式评测通过**。当前操作者是否解除暂停及服务器实时健康状况未获本期验证。原任务、种子、800 步预算、阈值、评估器、控制器、干预保持冻结，需 Core 审批下一关。

对外身份 **AURA**；AETHER/AETHER-CL 是历史实验名，BAGUETTE 暂为内部 Core 名。AURA 的 02=Core、05=前沿观察、06=工程；Embodied-AI 的 02=VLA 实验室、05=实验分支。不能混淆负责人，也不重复创建同一个基线。

## 10月29日研究更新：已查一手来源

| 优先级 | 论文/项目和日期 | 已核对的核心内容与阅读建议 | 执行影响 |
| --- | --- | --- | --- |
| **创新性最大压力** | [RoboDoctor](https://arxiv.org/abs/2610.35604)，**10月26日v1** | 策略/智能体监督、局部修正、持久经验；[官方代码](https://github.com/THUSI-Lab/RoboDoctor) README 已读，作者54任务数据**未隔离跨回合经验因果收益**。**DEEP DIVE** | MONITOR/BACKLOG：补充WP1，不集成M9a |
| **创新性最大压力** | [RoboAuto](https://arxiv.org/abs/2610.36533)，**10月27日v1** | 物体/场景/交互知识、主动探测、阶段效果检查。**DEEP DIVE** | MONITOR/BACKLOG：检查特权输入和主动观察成本 |
| **挑战在线世界模型必要性** | [PDRVLA](https://arxiv.org/abs/2610.37381)，**10月27日v1** | 在训练期学习RGB/深度/光流未来，在线用轻量物理 token 预测动作、无需生成视频。**DEEP DIVE** | 有兼容VLA基线后才考虑的NEXT-CHECKPOINT替代设计；不是新批准实验 |
| **反事实学习** | [Rollback](https://arxiv.org/abs/2610.36068)，**10月26日v1** | 在学习型世界模型中回溯/分支，再用真实数据更新；**不是物理机器人回退**。**READ→DEEP DIVE** | BACKLOG：将来先做仿真检查点oracle |
| **三维/感知/底层控制** | [E0.5](https://arxiv.org/abs/2610.36011)，10月26日v1；[ActiveAlign](https://arxiv.org/abs/2610.36859)、[VLA-Stem](https://arxiv.org/abs/2610.37378)，10月27日v1 | 3D原生未来预测、主动标定/触碰、冻结VLA下快速安全修正。**READ/WATCH** | BACKLOG：不迁移仿真器、不添硬件 |
| **历史工作修订** | [UniManip](https://arxiv.org/abs/2602.13086)，**2月13日初投、10月24日修订** | 智能体操作图、物体场景图、几何落地及诊断恢复。**先前工作 DEEP DIVE** | MONITOR/BACKLOG：压缩架构创新性声明 |
| **基准动态** | [RoboDojo 官网](https://robodojo-benchmark.com/)，**10月24–27日** | 10月27日GO-3 Nano Preview仿真agent赛道61.90分/56.42%成功；10月24日PyRUA-Lean 55.26/50.35；实机赛道独立。**WATCH** | MONITOR：按赛道和维度读榜单 |

**上游10月26日已覆盖：**AW-0、P² Progress Probes、Echo、FastHarness、WholeBodyMem/HuMeGo、UniWALM、UniFlowWAM、OpenTac、Isaac Lab 3.0 和 NVIDIA 10月20–21日材料。AURA 独立核对 AW-0/FastHarness 官方仓库 README、P²/Echo 等一手摘要，**没有实际执行这些系统去验证分数**。FastHarness CPU 符号原理可由 Embodied-AI 负责人考虑复现，AURA 复用而非重复投入；前期两种不同 FastVLA 仍列在 WP3 可行性表。

**解释分歧：**RoboDoctor/RoboAuto/UniManip 表明仅“规划+状态+验证+恢复”的设计创新性空间已很小；PDRVLA 说明某些任务可用**训练期预测监督**替代独立在线 WAM。P²/Echo 的进度与停止判断仍需**实际物理效果验证**，且“报警准确”不代表“恢复值得”。所有论文成功率均为**作者报告**。

## HQ、Core/02、队友要做什么

[10月19日原中文工作包 WP1–WP4](2026/2026-10-19-team-work.zh-CN.md)及[英文](2026/2026-10-19-team-work.md)仍是正式**拟议分工模板**。[10月29日中文交接](2026/2026-10-29-handoff.zh-CN.md)与[英文](2026/2026-10-29-handoff.md)只是扩展其阅读和比较内容，不另开大量任务：

- **D1 / 06：**核实 M9a 操作者是否允许继续、真实 Vulkan/相机/MP4/数据包/物理中立性阻塞；先经过 Core 冻结协议，再用新正式评测。
- **D2 / WP1 / 02：**把 RoboDoctor、RoboAuto、UniManip、PDRVLA、DynaHarness 置于相同策略/预算/特权信息对照，找出真正可证伪的**剩余**问题。
- **D3 / WP3：**可选地筛查一种可行学习型基线，比较已有两种 FastVLA 及 AW-0/PDRVLA/E0.5；先与 Embodied-AI 基线负责人协调，避免重复装环境。
- **D4 / HQ：**实际队友、工时、评审者、GPU/时间预算仍**未分配**，由用户/HQ 决定；WP2/WP4 只能在获准的准备范围内继续。

**下一正式科学实验的既有首选仍是：非特权感知验收后，比较证据时效性/状态失效处理。**干预价值 Continue/Reobserve/Recover 和明确迁移实验仍是重要备选，需要 Core 另行批准。**本周新增实验数为零。**

## 工作假设与证据标准

可靠操作可能需要历史、当前证据、选择性动作和从失败中学习，但具体功能可以通过**简单规则、显式状态、学习的时序表示、训练期蒸馏的世界模型监督、程序化技能或混合方法**实现。没有匹配预算的消融证明之前，不得把独立在线世界模型、外部记忆库、复杂验证器当作强制组件。

AURA 现有 M0–M8 严格审计和实物抓取分支即使与先前工作重叠，也仍有科研价值；创新性须来自非特权物理效果正确性、干预成本、失败归因与独立测试迁移，而非架构图组件数量。

历史[10月22日](2026/2026-10-22.zh-CN.md)、[10月19日](2026/2026-10-19.zh-CN.md)、[10月15日](2026/2026-10-15.zh-CN.md)均未改。研究[趋势台账](TREND_LEDGER.zh-CN.md)增加“在线世界模型并非强制需求”的10月29日假设修订。

## 执行影响结尾

**Continue：**现有已授权M9a渲染/Vulkan/相机调试与报告修复，服从暂停与Core科学协议关卡。  
**Change now：**不改实验/架构；只在前沿记录中提醒Core修改过宽创新主张。  
**Next checkpoint：**零个新增实验；保留已有状态证据时效性候选，待传感验收。  
**Deferred：**完整RoboDoctor/RoboAuto/AW-0/E0.5/PDRVLA复现、迁移仿真栈、买硬件、长期学习整合。  
**Evidence produced：**一手摘要/项目/官方仓库阅读、上游交叉核对、中英文交接；本期没有CPU实验、新模型推理、原生仿真或独立科学审计、没有分配人员。
