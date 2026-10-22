# 团队协作速查｜从保存一个链接到提交代码

更新：2026-10-19（v1.1）。项目背景看 [START_HERE.md](START_HERE.md)；完整分享版看 [TEAM_GUIDE.zh-CN.md](TEAM_GUIDE.zh-CN.md)。本文是协作建议，不代表权限、分支保护或Discussions已经配置；实际访问与合并要求以GitHub页面为准。

**自由探索与独立开发不需要等待共享合并。保存到自己的分支，与把修改合并到共享分支，是两件事。**

## 1. 刚加入时做什么

将GitHub用户名发给负责人，收到协作者邀请后登录自己的账号并接受。已接受不用重复操作，不提供密码或令牌。

先看中文入门，了解AURA与持续开发的暑期拣选系统的关系、上肢操作范围、迁移目标及当前问题。再按兴趣看架构、前沿或实验资料，不必读完所有历史。

在群里回复近期兴趣、已有工作/发现、大概时间和需要的帮助。申请分工是当前经验与兴趣，不是永久划分；已有工作也算进度，不额外要求重复任务。

## 2. 随手发现与中英文阅读

论文、代码、视频、问题和未完成想法都可以保存；只有来源链接也可以。AI摘要保留原文链接、标明核验程度。收藏不等于采纳，摘要不等于复现，也不自动变成待办任务。

**前沿优先看 [中文阅读索引（main）](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/README.zh-CN.md)**，再按兴趣进入 [中文当前雷达](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/CURRENT.zh-CN.md)、简报、证据和工作包。配套文件顶部可切换English；不是全仓库和全部历史都已有中文。

个人笔记中文、英文均可，不要求双语。正式双语材料保持任务ID、数值、证据限制和状态一致，记录对应版本；不同步就标记待同步。英文架构/工程记录仍标明英文，不用中文标题掩盖语言差异。

Discussions启用后可新建开放讨论；未启用时先发群里或保存成文件，不为一个链接强制建Issue。文件建议放 `docs/exploration/<GitHub用户名>/`，模板见 [探索笔记说明](docs/exploration/README.md)。目录不是私密空间，也不限制方向。

## 3. 浏览器里保存第一篇笔记

不需要先安装Git或配置服务器。

1. 打开Code页，确认当前分支是main。分支下拉菜单 → View all branches → New branch。
2. 输入如 `explore/yourname-perception-notes`，Branch source选择main，Create branch。yourname换成用户名；这是示例，不是已创建分支。
3. 切到新分支，从根目录选择Add file → Create new file。
4. 文件名填 `docs/exploration/yourname/2026-10-19-first-note.md`，正文写标题、来源和状态。路径中的 `/` 可创建子目录。
5. Preview后Commit changes，填写改动说明，确认提交到自己的分支，不是main或别人的工作分支。
6. 把文件/分支链接发给组员即可阅读；后续继续编辑提交，不需要每次都开PR。

准备纳入共享入口时，Pull requests → New pull request，检查base: main、compare: 自己的分支，说明内容和核验程度。可先开Draft PR询问，等待评审时仍可继续提交。

探索笔记的合并检查来源、状态与公开范围，不要求读完所有论文。合并表示记录适合保存，不表示结论已被证明。

## 4. 代码和实验：从正确基线开始

- 通用文档、阅读笔记和独立新实验通常从main建分支。
- 需要现有实验实现时，先与工程负责人确认起点，再从 `06-01/aether-cl-m0` 的约定版本建自己的分支；当前实验实现不全在main。
- 改动预期回到实验线时，PR的base选该实验分支，不把整条实验历史与main的差异当作小修改提交。
- 分支可用 `research/用户名-主题`、`dev/用户名-主题` 等；可以有多个分支，较长实验也可持续使用同一工作分支。
- “自己的分支”是协作约定，不是名字带来的独占权限。不要未经沟通修改或强推别人的分支。
- 在未受额外规则限制的工作分支上，协作者可以持续提交、推送、获取和测试；main的合并评审不等于每次开发都等批准。

各自使用独立工作目录或worktree、合适的隔离环境与输出位置，避免覆盖。运行中不切换或更新他人目录；GPU任务、共享环境修改和真机操作先协调。Git分支不会隔离硬件资源。正式实验记录代码版本、配置和真实结果，阅读/合成示例/单元测试与原生实验分开说明。

## 5. 轻量交流、展示与导师进展同步

**小会是轻松分享，不是每次正式答辩。** 聊最近在看什么、做什么、卡在哪里，互相帮助，也让导师看见实际投入和阶段变化。

建议约两周一次，普通交流约20—30分钟，有值得深入的内容再延长；具体时间共同确定。课业紧张时可缩短或改成群里异步更新，不设固定打卡、统一PPT或每次必须新增结果的要求。

负责人计划主要用实际视频、图片分享工作，并按需要整理DOCX/PDF/PPT；其他成员直接展示已有笔记、代码、截图或问题即可，不要求每人每次都制作完整汇报。基础学习、失败尝试、排除不合适的方法和明确阻塞都是可以分享的内容。

交流后轮流用几分钟记下日期、实际参与情况、讨论内容、材料链接、主要问题，以及已经约定的下一步或需要导师帮助的地方。可按需保存在 `docs/team/meetings/YYYY-MM-DD.md`；不要为未发生的会议提前填写记录。

可以附一两张实际现场照片或线上截图，先征得参与者同意，公开发布再检查人物和屏幕内容。照片用于记录交流，不替代实验日志；不强制每次拍照，不为拍照专门制造活动。示意图、重建动画、真实仿真录像和真机视频应注明类型，失败或未验证部分也如实保留。

导师同步复用这一简短记录和已有图像/视频/报告，不让每个人重复写正式材料。一次很短的真实更新，也可以比额外制作长篇汇报更有用。

## 6. 什么情况下建立任务？

只有双方约定开展的具体工作才需要任务Issue：问题、负责人、预期小成果、下一次交流点、依赖或困难。可以来自 [中文工作包菜单](https://github.com/NoctisBaguette/AURA-Embodied/blob/main/docs/research/frontier_watch/2026/2026-10-19-team-work.zh-CN.md)，也可以是自己的发现或原拣选系统的未完改进；菜单不是强制分工。

自由记录不套用正式实验验收标准。正式实验和共享资源使用则按现有科学范围、安全与资源约定执行，不把聊天兴趣直接视为运行批准。

## 7. 公开范围、媒体和版本

仓库及其分支公开，不上传个人报名表、密码、令牌、未授权录像或受限材料。第三方资料优先保存原链接；大型视频、数据和权重放约定存储，仓库记录可公开的说明、配置和索引。AI使用也遵守同样范围，没有执行的命令不能写成已通过。

建议小型可公开图像放对应笔记的资源目录；分享报告按日期和主题命名。PDF便于转发，DOCX便于编辑，PPT按需演示；在线Markdown承担持续更新，导出文件标注日期/版本和入口链接。实际采用的存储位置应先约定，不把本文示例当作已经建立的服务。

## 官方操作参考

以下为产品操作依据；上面的目录和交流节奏是团队建议，不是已启用权限。

- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [网页创建分支](https://docs.github.com/en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository)
- [网页创建文件](https://docs.github.com/en/repositories/working-with-files/managing-files/creating-new-files)
- [管理员启用Discussions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/enabling-or-disabling-github-discussions-for-a-repository)
