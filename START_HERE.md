# 从这里开始｜AURA 团队阅读与协作入口

更新：2026-10-19（v1.1）。本文是成员入门导航，不是新架构决议或实验授权。具体人员任务、时间和评审安排仍由团队协商。

**想一次读完并转发给组员：[团队入门与轻量协作指南（中文）](TEAM_GUIDE.zh-CN.md)。该稿配套PDF/DOCX用于分享，在线Markdown用于持续更新。**

准备动手时看 [TEAM_WORKFLOW.md：中文操作速查](TEAM_WORKFLOW.md)；看新研究时先进入 [05前沿观察中文索引（main）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/README.zh-CN.md)。不需要读完历史聊天或全部论文才能参与。

## 1. 我们在做什么？

AURA-Embodied，简称 **AURA（Adaptive Unified Robotic Agents）**，研究方向是 **面向多场景迁移的自主机器人操作智能**。

我们关心的是机器人怎样理解物体、选择并执行操作、判断物理结果、从失败中恢复，以及把已有能力迁移到新的物体、任务、环境、机器人本体和经验中。研究对象是操作智能系统，机器人是物理交互与验证平台。

当前物理范围是面向物体的上肢操作：机械臂、末端执行器及必要上半身机构完成抓取、放置、整理、插入、开合、倾倒、装配和工具使用等任务。单臂、双臂都可以；导航、走路、腿足控制不是当前研究主线。这是共同方向，不是限制成员只能阅读或探索某个细分领域。

## 2. 暑期项目与 AURA 是什么关系？

《2026ISIP—智能拣选软体抓取系统》不是已经结束、等待恢复的旧Demo，也不是与AURA无关的另一个项目。它是已有物理基础、必须持续推进的开发内容，以及真实问题和验证机会的来源。

我们继续完成未完成功能，改进RGB与RGB-D协同感知、机械臂控制与运动规划、软体/混合末端执行器、物理反馈和分拣可靠性；也研究普通学习策略/VLA及AURA机制能否帮助系统，并面向合适的拣选、机器人和创新赛事形成成果。

共同研究循环是：**真实问题或外部研究 → 提出问题 → 复现/实现 → 仿真或物理对照实验 → 分析失败与适用边界 → 修正架构与系统 → 检验迁移。** 不要求所有探索都先进入当前原型，也不要求每个实验都必须在真机上完成。

## 3. 当前架构在问什么？

AURA不是必须由若干独立模块组成的固定流水线。当前用“任务相关物理状态转移”作为分析和接口视角：希望什么物理事实发生变化，动作之后究竟发生了什么变化？

例如，“控制器已经到达位置”“夹爪已打开”不一定等于“物体已释放、得到独立支撑并稳定放好”。系统需要结合可获得的证据判断；看不到或信息过期也不应直接当成物理失败。

研究问题包括任务相关三维状态、动作可行性、非特权结果验证、局部恢复、长程任务、记忆与经验利用，以及RGB/RGB-D配置的性能与成本权衡。VLA、VLM、世界模型、世界动作模型、传统规划与控制都是可研究、可比较的实现选择，而不是AURA唯一身份。

**迁移不等于做出几个独立演示。** 要说明哪些机制保持不变、从什么条件迁移到什么条件、做了多少适配，以及性能和失败发生了什么变化。具体架构仍可被实验和成员的新想法挑战。

详细定义见 [ARCHITECTURE.md（英文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/ARCHITECTURE.md) 和 [状态转移架构v0.2（英文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/architecture/aura/AURA_State_Transition_Architecture_v0.2.md)。本页是中文导读，不冒充完整译本。

## 4. 已有什么？还没有证明什么？

| 内容 | 当前记录的边界 | 去哪里查看 |
|---|---|---|
| 长期方向与年度安排 | 一学年是阶段计划，不是AURA研究终点；寒假偏远程软件/模型/仿真，真机系统持续开发 | [ROADMAP.md（英文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/ROADMAP.md) |
| 架构与前沿研究 | 已形成架构说明、持续前沿跟踪和候选问题；论文摘要、作者结果不等于团队复现结果 | [前沿中文入口](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/README.zh-CN.md) |
| Prototype A / M0—M8 | 已有受控仿真中的验证与有限恢复研究；不能据此声称已完成传感器驱动自主操作、真机迁移或通用学习 | [实验分支文档（以英文为主）](https://github.com/NoctisBaguette/AURA-Embodied/tree/06-01/aether-cl-m0/docs/research/experiments) |
| M9a | 较新记录进入传感器验证的相机/接口调试准备，并保留报告修正；所读记录不证明相机中立性或传感器验证器已通过验收 | [启动记录（英文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Commissioning_Start_v0.1.md)、[相机记录（英文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md) |

M9a是围绕保留执行器研究传感器验证，不代表整套执行系统已经摆脱仿真特权信息。实时阻塞、暂停和后续结果以工程负责人最新记录为准；本文不安排任何服务器或机器人运行。

## 5. 大家可以怎样参与？

**自由探索与约定任务并存。** 申请中的分工体现当前经验和兴趣，不是永久限制；不同年级、不同经验可以用不同方式起步。

- 看到有趣的论文、仓库、视频或方法，可以只保存来源，不必已经读懂，也不必马上证明它与当前架构相关。
- 可以保留问题、未完成想法、自己的阅读笔记和AI辅助摘要。标明“待阅读/未核验/已初读”等实际状态即可；AI摘要应保留原始来源，并标明核验程度。
- 想深入时，再将某个兴趣转成一个小问题：比较方法、读懂机制、检查源码、做小复现/小实验、改进软硬件部件或分析已有结果。
- 已经约定的任务需要有下一次交流点；没有约定的随手发现不自动变成作业。
- 架构、评测、数据分析与物理实验可共同参与；新成员不是固定负责文档或标注，也不要求所有人立即独立训练大模型。

**不再要求“只有成熟结论才能进入GitHub”。未成熟探索可以记录；成熟度要求用于项目结论、架构采用和实验宣称，而不是限制保存发现。**

小会以轻松分享为主，帮助彼此交流，也让导师了解真实进展。建议约两周交流一次，时间随课业调整；忙时可以很短或异步，不要求统一PPT、固定照片或每次必须有新结果。负责人计划用实际视频、图片及按需整理的DOCX/PDF/PPT分享工作，不把这一形式要求强加给所有人。具体做法见 [协作速查第5节](TEAM_WORKFLOW.md#5-轻量交流展示与导师进展同步)。

## 6. 资料放哪里？任务怎么协作？

| 想做的事 | 建议位置 |
|---|---|
| 随手发现、开放问题、AI摘要 | 微信群；Discussions启用后可集中讨论；或 [探索笔记区](docs/exploration/README.md) |
| 想保留成文件的笔记 | `docs/exploration/<GitHub用户名>/`；中文或英文均可 |
| 约定开展的任务、分工、阻塞与进度 | GitHub Issue：问题、实际负责人、预期小成果、下一次交流点；探索不强制建任务 |
| 修改共享文档或代码 | 具体任务的工作分支；可以持续提交和开发，准备纳入共享分支时再开PR |
| 已采纳结论与实验结果 | 对应架构/研究/实验记录；附证据与决定，未核验笔记不直接写成已证实结果 |

探索笔记的合并只表示“适合保存”，不表示技术结论成立。研究笔记通常从main建分支；依赖实验代码的修改先与工程负责人约定基线，不直接改变他人的活跃分支。分支只隔离文件，不隔离GPU进程、共享环境或机器人操作；这些资源需另行协调。

仓库公开：不上传口令、令牌、个人申报信息、受限资料或未经许可的数据/视频。第三方资料优先保存原链接，大型媒体使用约定存储位置。

## 7. 中文与英文怎么选？

团队入门优先中文；部分研究文件同时维护英文和简体中文，不要求所有个人笔记双语。常见配套为 `name.md` 与 `name.zh-CN.md`，但应以文件语言标注为准，不能只凭扩展名判断。

05当前中文覆盖：中文索引、当前雷达、10月19日简报/证据/完整工作包、10月15日周报及四份附件、趋势台账。10月8/9日旧报告、其他分支架构全文、代码和原始工程记录未因此全部翻译。

两种语言保留相同任务ID、来源、数值、证据限制和审批状态，并标明对应版本/日期。重要变更应同步；未同步时明确标记，不默认翻译日期较新就意味着技术结论更新。来源冲突回查原始记录和正式决定，而不是按语言选择权威。

## 8. 按需要阅读，不必一次读完

1. **整体与协作合订本**：[TEAM_GUIDE.zh-CN.md（中文）](TEAM_GUIDE.zh-CN.md)。
2. **前沿首选入口**：[中文阅读索引](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/README.zh-CN.md)；每周有空浏览，不作为阅读考核。
3. **当前问题**：[当前研究雷达（中文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/CURRENT.zh-CN.md)。
4. **深入判断**：[10月19日简报（中文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/2026/2026-10-19.zh-CN.md)。
5. **可选起步题目**：[团队工作包（中文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/2026/2026-10-19-team-work.zh-CN.md)。这是待讨论菜单，不是已分配作业。
6. **核对论文依据**：[证据登记表（中文）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/2026/2026-10-19-evidence.zh-CN.md)。来源阅读、作者宣称、可下载资源与实际复现不同。
7. **动手操作**：[TEAM_WORKFLOW.md（中文）](TEAM_WORKFLOW.md)。

这些前沿链接明确指向main，避免在尚未包含中文发布的工作分支里打开相对路径失败。各前沿中文文件顶部保留English对照链接。

刚加入时，先了解方向，再告诉团队最近的兴趣、已有发现、希望怎样开始和近期大概可投入的时间。尚未确定方向也可以，不需要负责人重讲全部历史。
