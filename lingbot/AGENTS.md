# Instructions for this LingBot workspace

These instructions apply only under `lingbot/`. The user explicitly requested a separate LingBot workspace; do not reinterpret it as a change to AURA's existing M9a experiment or frozen scientific protocol.

1. Start with README.md, CURRENT.md, TASKS.md, GITHUB-WORKFLOW-EN-ZH.txt, the assigned A/B card and INTERFACES.md. Read the actual checkpoint/episode producer and consumer before modifying their interface.
2. Keep reference/ and official/ read-only as retained inputs. Public reference copies contain placeholder host paths and are not deployable runtime files. Their copy manifest identifies differences from the private original; do not rewrite original source hashes to conceal those differences.
3. New implementation belongs under submission/portable/ or submission/evaluation/. A and B use their own branches and submit PRs to lingbot/competition. Do not alter unrelated AURA files or branches.
4. CPU fixtures, source inspection, compilation, real model loading and native simulator execution are distinct evidence. Label checks NOT RUN when unavailable. Never count commissioning, fabricated samples or duplicate episodes as policy results.
5. Preserve checkpoint completeness, preprocessing, official task success, finite rejection rules, resource gates, failure evidence and one fixed final policy identity. Propose a concrete interface change for captain review when required.
6. The active server run is independent of this repository. No checkout, import, test, merge or report update may automatically launch GPU work or deploy to it. Coordinate actual GPU use with the captain.
7. Keep public commits free of credentials, personal host addresses/paths, raw private incident history, weight/data binaries and private raw logs. The exact original archive and engineering history remain in the private repository; review applicable records there when authorized access is available, and state access limits otherwise.
8. Daily reports through 23 October follow 06-DAILY-REPORT-EN-ZH.txt. Return actual files, commands, evidence, remaining effort and takeover steps. Do not invent teammate progress or promise unattended monitoring.
9. Status observations are dated and attributed. CURRENT.md is a manually maintained summary, not a live dashboard. A stale watcher timestamp alone does not establish a stalled child.

No new simulator, training, dependency upgrade or alternate scientific experiment is authorized merely by reading this file.
