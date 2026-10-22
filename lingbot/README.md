# LingBot team workspace

**Read one file: [Complete Team Guide — English / 中文](LingBot-Team-Complete-Guide-EN-ZH.txt).**

It contains the project context, full A/B assignments, source-reading order, shared interfaces, acceptance checks, 22–24 October milestones and reports, AI prompts and GitHub/direct-file handoff. Choose one language; both cover the complete instructions. Supporting role/report files are extracts or pointers; this guide is the complete assignment.

**只需先读一份：[团队完整交接说明（中英双语）](LingBot-Team-Complete-Guide-EN-ZH.txt)。** 背景、A/B 分工、日报、交付和 GitHub 都已整合；选一种语言即可。开始实现时按其中清单阅读真实源码。

Send the same guide to both teammates and tell each person their role. For code/templates, use this branch or [the source ZIP, including the guide](deliverables/LingBot-AURA-Workspace-20261022.zip). GitHub is optional: teammates may send reports and changed-code ZIPs directly to the captain.

## Work locations

| Owner | Branch | New implementation |
|---|---|---|
| A: portable export/load | `lingbot/portable-package` | `submission/portable/` |
| B: evaluation/results | `lingbot/full-evaluation` | `submission/evaluation/` |
| Captain: integration | `lingbot/competition` | Reviews A/B pull requests and evidence |

Owner pull requests target **lingbot/competition**, not main. Optional daily reports go under `reports/YYYY-MM-DD/A.md` or `B.md` on the owner's branch, with the PR link sent to the captain. This does not grant write access or automate review/deployment.

## Evidence and references

Latest captain-supplied status: JOINT_TRAINING, 16/16 commissions,32/32 baseline,5,420 updates/10,840 examples;candidate 0/32. These are completion/update counts, not successful-task counts or a live feed. See [CURRENT.md](CURRENT.md). The team's internal finish is 24 October; this plan uses 20:00 Beijing, with partial code due23 October 12:00. A packages a reproducible policy; B implements evaluation and reviews failures; captain owns the runtime and model decision. Native acceptance and full coverage are still pending.

`reference/` contains retained source inputs with host paths replaced by placeholders; they are not a runnable portable release. `official/` retains the supplied organizer templates. Read [the copy manifest](provenance/public-reference-manifest.json) for identities. Weights, datasets, credentials, original private evidence and the full runtime environment are not in this public bundle. Existing AURA/M9a work remains separate.

Supporting technical references: [interfaces](INTERFACES.md), [code map](CODE-MAP.md), [A card](A-PORTABLE-PACKAGE.md), [B card](B-EVALUATION-RESULTS.md), [sources](05-SOURCES.txt). They do not replace the single complete onboarding guide above.
