# Current LingBot state — 21 October 2026

Source: the captain's latest pasted status. Exact capture time was not supplied. This is not a fresh SSH query or an independently audited run archive.

| Item | Last reported value |
|---|---|
| Watcher | `wait-v6ie9xo8`, RUNNING |
| Verified worker / lease | True / True |
| Linked run | `run-L6iqyVGy`, verified process-tree relationship |
| Phase | **BASELINE** |
| Simulator commissions | **16/16** |
| Baseline completed | **8/32**, previously 2/32 |
| Candidate completed | **0/32** |
| Texture presence/header check | 1000/1000, no missing/extra/invalid files |
| Success counts | Not supplied |

GPU admission has been passed. The existing checkpoint is being evaluated before new joint training. Let this workflow continue; this snapshot does not call for a restart.

The watcher's 15:47:19 Beijing timestamp records its transition to RUNNING. The controller blocks while its child workflow executes, so that timestamp is not a per-episode heartbeat. Parent baseline counts are committed after a complete two-episode case and video checks. Recorded GPU samples are historical.

The displayed review package has the same filename as in the earlier 2/32 snapshot. It may lag the live report; do not claim that it contains all eight completed episodes without inspecting it. Commissioning is not learned-policy success. No completed new training, 32/32 baseline, 10,000-episode evaluation or final submission is established.

## Next work

- Captain: continue the current workflow and review its actual reports when available; select one checkpoint from the baseline/candidate evidence. No automatic candidate promotion.
- A: CPU-first export/loading work, followed by coordinated fresh-process validation.
- B: CPU-first full-suite scheduling/results work, followed by coordinated integration and measured rollout throughput.
- Both teammates: daily progress reports through 23 October; implementations and reports have not yet been received in this workspace.

Planned workflow: remaining baseline → joint continuation → candidate pilot. The 22-hour training-loop limit is a limit, not an ETA. Full-suite evaluation and final submission are separate downstream work.

Machine-readable snapshot: [progress/current.json](progress/current.json). Retained observation: [progress/2026-10-21-baseline-008.json](progress/2026-10-21-baseline-008.json). Update these with an attributed new observation, never a guessed counter.
