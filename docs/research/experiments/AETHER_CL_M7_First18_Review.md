# AETHER-CL M7 first18 independent pilot review

Reviewed 2026-10-07 UTC / 2026-10-08 Asia/Shanghai. Native measurement remains pinned to `a51e5d2073c4033141b26e956804d593aa45d6df`, under DEC-0006 and the frozen [M7 preregistration](AETHER_CL_M7_Insertion_Preregistration.md). This publication changes evidence documentation only.

## Decision

Continue the 342 unstarted slots of the frozen M7 matrix. Retain all first18 slots and their immutable pilot archive. Resume through the existing guarded parent with the same code, software and physical environment; do not rerun, exclude or replace any outcome. Return to02 after the complete native M7 audit before further scope. No model training occurs.

## Observed pilot

The18 slots reuse two fresh scenes, seeds140/141, across three conditions and Baseline/V1/V2. These are two independent reset scenes, not18 independent scenes. The remaining matrix and all thresholds were frozen before these outcomes.

| Misalignment | Baseline | V1 | V2 | V2 attempts |
| --- | --- | --- | --- | --- |
| Normal0mm | 2/2 | 2/2 | 2/2 | 0 |
| Easy1.5mm | 2/2 | 2/2 | 2/2 | 0 |
| Hard6mm | 0/2 | 0/2 | 2/2 | 2 |

Both6mm attempts complete backout, one geometry refresh, realign, reinsert and verify, using159/160 recovery actions within the frozen420-action budget. Final recovered depths are114.455/121.351mm. Reference and V1/V2 diagnosis agree on `INSERTION_LATERAL_INTERFERENCE`: failure step630, detection642, first recovery action643. Healthy matched pairs have zero unnecessary recovery and zero regression. All18 retained legacy-velocity shadow scores are false; active scoring and motion remain unchanged.

The achieved object-target Y offsets in the Baseline pairs are1.499930/1.500328mm for easy and6.001131/6.001375mm for hard. All12 nonzero trial injections apply with the required precontact readiness; the gate checks all eight nonzero Baseline/V1 cases. Extra total TCP path relative to V1 in the two recovered pairs is224.231/232.673mm. Healthy zero-attempt and failed outcomes remain in reporting.

## Independent evidence audit

Pilot archive SHA-256: `3ec98dea029d19d7237c6ff6579878c87d42d4992fe61563be340dcd62439c66`. Machine protocol SHA-256: `9c5a713fc1744e11f0d6f6cd1f12ef386948f59bba6982b3c4864a69d54a4e6d`.

All111 indexed files have exact membership, sizes and SHA-256 hashes. All15 source/protocol/inspection/review/guard snapshot Git blobs match the authoritative measurement tree. Eleven execution-source SHA-256 values match the frozen protocol. Installed17-source and Panda URDF identities match the original inspection receipt; all child-parent configuration, software, source, startup environment, scope and preregistration identities agree. The retained history guard checked2776 prior event files, reported resets0-139 and found no140-159 overlap; this does not cover deleted or unreported runs.

Portable read-only replay in Python3.10.21, NumPy1.26.4 and SciPy1.10.1 reconstructs21,600 actions with zero maximum action error, all108,000 external100Hz physics samples and every independent physical endpoint. All18 result and parent audit copies agree. All16 exact comparisons pass: six full Baseline/V1 pairs, six V1/V2 full or pre-recovery pairs and four430-action normal/disturbed control prefixes. The retained aggregate JSON and all three CSV files regenerate byte-exactly.

The four commissioning/evidence checks pass: complete first18 replay; exact pairs; viable normal Baseline; precontact injection. The pilot gate has no V2 success requirement. Its observed rescues support commissioning only; generalization and the robustness curve require the remaining frozen matrix. No source, task asset, threshold, disturbance, seed selection or recovery budget changes follow these outcomes.

[Machine review](evidence/AETHER_CL_M7_First18_Review.json) records the complete replay and comparison checks. Native frozen measurement code stays pinned to `a51e5d2073c4033141b26e956804d593aa45d6df` for resume even when this documentation advances the GitHub branch. PR#1 remains open, draft and unmerged; main is unchanged.
