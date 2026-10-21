# LingBot team workspace

**Read one file: [Complete Team Guide — English / 中文](LingBot-Team-Complete-Guide-EN-ZH.txt).**

It contains the project context, full A/B assignments, source-reading order, shared interfaces, acceptance checks, daily reports through 23 October, AI prompts and GitHub/direct-file handoff. Choose one language; both cover the complete instructions. Older onboarding files are optional reference appendices.

**只需先读一份：[团队完整交接说明（中英双语）](LingBot-Team-Complete-Guide-EN-ZH.txt)。** 背景、A/B 分工、日报、交付和 GitHub 都已整合；选一种语言即可。开始实现时按其中清单阅读真实源码。

Send the same guide to both teammates and tell each person their role. For code/templates, use this branch or [the source ZIP, including the guide](deliverables/LingBot-AURA-Workspace-20261021.zip). GitHub is optional: teammates may send reports and changed-code ZIPs directly to the captain.

## Work locations

| Owner | Branch | New implementation |
|---|---|---|
| A: portable export/load | `lingbot/portable-package` | `submission/portable/` |
| B: evaluation/results | `lingbot/full-evaluation` | `submission/evaluation/` |
| Captain: integration | `lingbot/competition` | Reviews A/B pull requests and evidence |

Owner pull requests target **lingbot/competition**, not main. Optional daily reports go under `reports/YYYY-MM-DD/A.md` or `B.md` on the owner's branch, with the PR link sent to the captain. This does not grant write access or automate review/deployment.

## Evidence and references

The latest captain-supplied status reports a stopped run: ERROR / BASELINE, commissioning 16/16 and baseline 28/32 after a case/stage timeout. New joint training was not reached; 28 is a completion count, not successes. See [CURRENT.md](CURRENT.md) for the attributed snapshot; this is not live server monitoring. No teammate implementation or native acceptance is claimed by creating these directories.

`reference/` contains retained source inputs with host paths replaced by placeholders; they are not a runnable portable release. `official/` retains the supplied organizer templates. Read [the copy manifest](provenance/public-reference-manifest.json) for identities. Weights, datasets, credentials, original private evidence and the full runtime environment are not in this public bundle. Existing AURA/M9a work remains separate.

Supporting technical references: [interfaces](INTERFACES.md), [code map](CODE-MAP.md), [A card](A-PORTABLE-PACKAGE.md), [B card](B-EVALUATION-RESULTS.md), [sources](05-SOURCES.txt). They do not replace the single complete onboarding guide above.
