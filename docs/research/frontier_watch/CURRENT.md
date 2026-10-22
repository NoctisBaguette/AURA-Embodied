# AURA Frontier Watch — Current Research Radar

**Languages:** English · [简体中文](CURRENT.zh-CN.md) · [Chinese reading index](README.zh-CN.md)

**Updated:** 2026-10-22. **Latest issue:** [October 22 weekly watch](2026/2026-10-22.md), [Chinese companion](2026/2026-10-22.zh-CN.md). Prepared manually after the scheduled run failed; no new model tests or native experiments.

## Current decision

**No change to the active experiment.** Core continuity v0.2 confirms M9a commissioning/repair, followed by Core acceptance/protocol freeze before fresh evaluation. Respect the current operator pause. Do not restart 02W, migrate the simulator or insert a new memory/policy mechanism because a new paper appeared.

Public naming is AURA; BAGUETTE remains provisional internal naming; historical AETHER-CL identifiers stay unchanged. Authoritative engineering evidence remains on `06-01/aether-cl-m0`, not main's old experiment-log template.

## October 22 delta

| Item | What was checked | Disposition | Execution impact |
| --- | --- | --- | --- |
| UniWALM, October 20 | Primary abstract: joint video/action/language generation and next-step textual memory; not full ablations/code | DEEP DIVE, bounded information-flow comparison | MONITOR/BACKLOG; WP1 comparator, not M9a integration |
| AWLS, October 20 | Primary abstract: frozen decoder with learned latent-noise adapter | READ | MONITOR/BACKLOG; requires a compatible learned baseline |
| NVIDIA Isaac expansion, October 21 | Official release: learning/runtime/data updates with distinct access/availability conditions | WATCH / READ | MONITOR/BACKLOG; no pinned-environment or driver change |
| RoboDojo, October 17–21 news | Official news distinguishes sim agent-track and real-world entries; separate leaderboard retrieval was older | READ / WATCH | MONITOR/BACKLOG; no unqualified overall rank claim |
| CBST, October 15 | Primary abstract: task-level cross-embodiment transfer under predefined causal/semantic assumptions | READ | MONITOR/BACKLOG; keep transfer separate from sensing ablation |
| Both FastVLA methods, October 15 | Independently checked primary abstracts; different inference mechanisms | READ / existing REPRODUCE-feasibility candidate | MONITOR/BACKLOG; retain one bounded WP3 feasibility review |

The dated issue includes technical explanations, source dates/versions, limitations, reproduction ideas and a complete Chinese companion. Source access was partial for several primary pages; no full-paper or runnable-release audit is claimed.

## What HQ and Core/02 should decide

The [October 19 decision brief](2026/2026-10-19.md), [evidence register](2026/2026-10-19-evidence.md) and [team work packages](2026/2026-10-19-team-work.md) remain the allocation basis. Their [Chinese decision brief](2026/2026-10-19.zh-CN.md), [evidence](2026/2026-10-19-evidence.zh-CN.md) and [work packages](2026/2026-10-19-team-work.zh-CN.md) remain available.

- **D1:** confirm M9a's current blocker/pause and support needs; preserve its existing scope and fresh-evaluation gate.
- **D2:** at the next accepted sensing checkpoint, select one comparison. Evidence freshness/invalidation remains the strongest existing proposal; intervention value remains an alternative. No new experiment is nominated this week.
- **D3:** approve one isolated learned-baseline feasibility task, reuse compatible Embodied-AI work, or defer. Keep the two FastVLA identities separate; evaluate new infrastructure only against a documented obstacle.
- **D4:** assign actual people, reviewers and budgets only when HQ/user capacity is known. This radar does not assign teammates.

WP1 may add UniWALM as an integrated alternative in its existing comparison table. WP3 may add an artifact/compatibility row for NVIDIA's announcement. WP2/WP4 keep their scope. These refine existing deliverables rather than generating a fresh task list.

## Current evidence and source of scope

Read [Core continuity v0.2](../coordination/BAGUETTE_Core_Research_Continuity_v0.2.md), [architecture](../../../ARCHITECTURE.md), [roadmap](../../../ROADMAP.md), and the experiment-branch [M9a camera commissioning record](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md).

M9a isolates non-privileged verification around a preserved executor. The inspected records do not establish sensor-verifier acceptance, current server health or completed fresh M9a results. Missing/stale evidence is not automatically confirmed physical failure.

## Working hypothesis and preserved research

Reliable manipulation may benefit from relevant history, current evidence-supported state, useful prediction and selective recovery/learning. Explicit, integrated and hybrid implementations remain alternatives. Generating memory text is not evidence that its physical claims are true; freezing decoder weights is not evidence that an adapter leaves behavior unchanged.

DynaHarness remains a verified older comparator, not a new weekly release. Its same-capability-library comparison is particularly relevant when separating policy/library strength from execution governance. Existing HELM, Long-WAM, REMM, RESCUE and other historical entries remain leads at their recorded evidence levels; they were not all re-audited this week.

Earlier [October 15](2026/2026-10-15.md) and [October 19](2026/2026-10-19.md) issues are unchanged. The [previous current-radar snapshot](https://github.com/NoctisBaguette/AURA-Embodied/blob/5ef6ee848751277c8754f79a66a29dc3c4e4aadb/docs/research/frontier_watch/CURRENT.md) remains in Git history. No material new persistent-trend judgment was made, so both trend ledgers remain unchanged.

## Execution-impact footer

**Continue:** authorized M9a commissioning/repair, subject to pause and acceptance gates.

**Change now:** watch scheduling/delivery correction only; no scientific or infrastructure change.

**Next checkpoint:** zero newly added experiments; preserve evidence freshness/invalidation as the existing candidate.

**Deferred:** large training, new memory/world-model stacks, platform migration and hardware purchases.

**Evidence produced:** targeted primary-source/repository review, bilingual synthesis and GitHub publication checks. No new local model test, native run or audited scientific result.
