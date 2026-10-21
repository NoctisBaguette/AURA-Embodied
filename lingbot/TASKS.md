# LingBot work and ownership

Last update: 21 October 2026. Role names A/B are placeholders for the captain to assign; no teammate work is claimed as completed.

| Work | Owner | Evidence-backed status | Next delivery |
|---|---|---|---|
| Existing baseline/train/candidate workflow | Captain + assistant | Captain reports BASELINE 8/32, commission 16/16 | Actual baseline/candidate evidence |
| Portable export and loading | A | Assignment delivered; implementation not reported | Artifact inventory and CPU draft |
| Full evaluation and resumption | B | Assignment delivered; implementation not reported | 100-cell dry-run and result validator |
| Fresh-process loading and parity | A + captain | Pending | Real checkpoint/load comparison |
| Integrated evaluator | B + A + captain | Pending | Small real cell and resume test |
| Final checkpoint decision | Captain | Pending | One reproducible fixed identity |
| Full evaluation/results | B + captain | Pending | Actual coverage, outcomes and throughput |
| Reproduction and submission | A/B + captain | Pending | Matching code/config/weights/results |

## Daily handover

Use [06-DAILY-REPORT-EN-ZH.txt](06-DAILY-REPORT-EN-ZH.txt). Suggested Beijing check-ins: 21/22 October 22:00; 23 October 12:00 with current code and commands. These are internal targets. Report blocking dependencies promptly.

Public reports go in `reports/YYYY-MM-DD/A.md` or `B.md` on the owner's branch. Do not commit placeholder reports as if a teammate had submitted them. A private TXT/ZIP sent to the captain is also acceptable; the captain can record a sanitized summary with attribution.

## Integration decisions

A owns the loader and package; B owns the evaluator and records. A's eval.sh invokes B's evaluator. Both use [INTERFACES.md](INTERFACES.md). Planned CLI names are not implemented tools yet. The captain reviews code and execution evidence before integration and server use.
