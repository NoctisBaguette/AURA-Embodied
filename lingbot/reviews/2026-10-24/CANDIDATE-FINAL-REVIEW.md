# Candidate final report review — 24 October 2026

The reports-only archive is accessible and reviewed. Its 492 unique entries pass ZIP CRC; all 490 included manifest payloads match their recorded size and SHA256. All 29 runtime payload pins match the previously reviewed recovery release. The original manifest also lists 80 MP4s, 2,280 JPGs, 111 PNGs and 1,036 NPZs omitted from this subset. Those candidate media and array files have not been reviewed.

The manager is COMPLETE/FINISHED, both exit codes are 0, and the final policy and trained-stage reports are COMPLETE. The serving receipt records unchanged parameters and persistent buffers. Restore and the separate saved-input replay receipts PASS. No optimizer was created and no new training occurred. Cleanup and preservation are recorded as successful; these are retained receipts, not a fresh live process inspection or independent reload of external weights.

## Completed outcomes

Each task has two clean and two randomized episodes.

| Task | Baseline | Candidate |
|---|---:|---:|
| click_bell | 3/4 | 4/4 |
| lift_pot | 0/4 | 0/4 |
| handover_block | 0/4 | 0/4 |
| place_can_basket | 0/4 | 0/4 |
| open_laptop | 0/4 | 1/4 |
| stack_blocks_two | 0/4 | 0/4 |
| rotate_qrcode | 0/4 | 0/4 |
| pick_dual_bottles | 0/4 | 1/4 |
| Total | 3/32 | 6/32 |

All 64 parent episode records reconcile with their child episode.json files. Nine earlier candidate outcomes are preserved exactly. The 23 new candidate episodes account for 273 learned-policy requests; two offline replay requests bring the final serving receipt to 275. All 26 unsuccessful candidate episodes reached their full task action limits.

Only 29 exact task/setting/seed combinations match between stages. Setup qualification changed the accepted seeds in clean basket, randomized basket and randomized bottles. All three added successes occur among matching scenes: randomized bell seed 100001, randomized laptop seed 100000 and clean bottles seed 100000. No baseline success was lost among those matching scenes. This is a small eight-task pilot, not a full competition score or proof of general improvement.

## Timing and diagnosis limits

Candidate episode durations sum to 22,116.79 seconds across the source and replacement runs; recorded neural inference sums to 481.86 seconds, about 2.18%. The replacement run itself records 20,444.12 seconds, including qualification and admission. These totals cover different work and cannot be substituted for each other. The records do not separately time physics, rendering, recording and other overhead.

The candidate summaries record 32,632 TOPP calls, one caught exception, no empty returns, and joint tracking RMSE from 0.151 to 4.446 degrees. The exception occurred in unsuccessful randomized laptop seed 100001. These summaries do not establish correct commanded behavior, a visual failure cause, or a reason to swap arms or change normalization. The omitted NPZ files have not been independently recomputed.

Training consumed 49,784 examples: 995 or 996 per task across 50 tasks. The selected checkpoint remains update 24,892. Balanced sample counts do not establish model competence.

## Work allocation and remaining work

B is unavailable tonight. The earlier two-working-hour adapter assignment is superseded: the captain/assistant own native adapter and portable-package integration; B can review videos and return timestamped observations when awake. Existing B CPU work remains useful.

Native adapter integration, fresh CUDA loading/parity of an exported portable package, and reproducible submission entrypoints remain unfinished. Successful replay in the existing runtime does not qualify that separate delivery path.

Preserve both checkpoints and all unsuccessful outcomes. No new training or restart is needed to inspect this completed evidence. The next visual comparison can use the successful and unsuccessful randomized laptop videos from the already downloaded full archive. Public Git contains reviewed source and aggregate findings; private runtime records remain private.
