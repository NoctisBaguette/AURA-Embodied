# LingBot competition workspace / 灵波比赛工作区

This is the shared GitHub home for our LingBot-VLA 2.0 / RoboTwin competition work. It is separate from AURA's AETHER/M9a experiments.

**Integration branch:** [`lingbot/competition`](https://github.com/NoctisBaguette/AURA-Embodied/tree/lingbot/competition/lingbot). Start here when returning in a new chat.

**Latest captain-reported snapshot, 21 October:** `run-L6iqyVGy` is RUNNING / BASELINE; simulator commissioning **16/16**, baseline **8/32**, candidate **0/32**. Completion counts are not success scores. Read [CURRENT.md](CURRENT.md) for the evidence limits.

## Start here

1. Read [CURRENT.md](CURRENT.md), [TASKS.md](TASKS.md) and [GITHUB-WORKFLOW-EN-ZH.txt](GITHUB-WORKFLOW-EN-ZH.txt).
2. Read [English instructions](00-READ-FIRST-EN.txt) or [中文说明](00-READ-FIRST-ZH.txt).
3. A reads [the packaging assignment](A-PORTABLE-PACKAGE.md); B reads [the evaluation assignment](B-EVALUATION-RESULTS.md). Both read [INTERFACES.md](INTERFACES.md).
4. Your AI can use [A's prompt](02-AI-PROMPT-A.txt) or [B's prompt](03-AI-PROMPT-B.txt). Actual source navigation is in [CODE-MAP.md](CODE-MAP.md).
5. Report daily through 23 October using [the bilingual report template](06-DAILY-REPORT-EN-ZH.txt). Place public summaries in [reports/](reports/README.md), or send them privately to the captain.

## Where work lives

| Location | Purpose |
|---|---|
| `reference/runtime/` | 25 retained runtime reference files for inspection |
| `reference/inference_common.py` | Existing preprocessing and inference support |
| `reference/configs/` | Clean/randomized scene configuration references |
| `official/` | Exact supplied organizer templates |
| `submission/portable/` | A's new implementation area; currently awaiting teammate work |
| `submission/evaluation/` | B's new implementation area; currently awaiting teammate work |
| `reports/` | Dated teammate reports; no reports received yet |
| `progress/` | Attributed status snapshots, not an automatic server feed |
| `provenance/` | Original/public file identities and copy limitations |

## How changes move

A works on `lingbot/portable-package`; B works on `lingbot/full-evaluation`. Their pull requests target **`lingbot/competition`**, where the captain reviews and integrates them. The current server does not deploy from GitHub automatically. Changing this repository does not restart or update the running workflow.

This repository is public. Reference copies replace personal server paths with `/path/to/...` placeholders. They are useful source references, **not a runnable portable release**. Their hashes can differ from the exact frozen server files; see [provenance](provenance/public-reference-manifest.json). Weights, datasets, credentials, detailed private incidents and original server evidence are outside this public workspace. Missing dependencies are requested specifically, not fabricated.

The original archive remains in the private [Embodied-AI-Research project](https://github.com/NoctisBaguette/Embodied-AI-Research/tree/main/experiments/lingbot-competition). Future A/B implementation work belongs here; original frozen references and historical evidence stay in that archive. Access to the private archive is not assumed for teammates or their AI tools.

## 中文快速说明

以后从本目录进入 LingBot 工作。先读 CURRENT、TASKS 和 GitHub 协作说明，再读自己的 A/B 任务卡。A 在 `lingbot/portable-package` 开发模型打包/加载，B 在 `lingbot/full-evaluation` 开发评测；PR 都提交到 `lingbot/competition`，由队长整合。原有 AURA/M9a 工作保持独立。

当前最后一次队长报告为基线 8/32、模拟器验收 16/16，不是 8 次成功，也不代表训练完成。进度是人工提供的快照，GitHub 不会自动读取服务器。公网参考代码中的主机路径已替换为占位符，不能直接当作服务器发布版本执行。每日汇报与部分代码交接要求仍然有效。
