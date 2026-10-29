# AURA Frontier Watch — Current Research Radar

**Languages:** English · [简体中文](CURRENT.zh-CN.md) · [Chinese reading index](README.zh-CN.md). **Updated:** 2026-10-29.

**Latest:** [October 29 Frontier Watch](2026/2026-10-29.md) · [中文周报](2026/2026-10-29.zh-CN.md) · [HQ/Core/team handoff](2026/2026-10-29-handoff.md) · [中文分工交接](2026/2026-10-29-handoff.zh-CN.md).

## Active conclusion

**No change to M9a.** The authoritative experiment branch is **06-01/aether-cl-m0**, inspected head cd8185dbe36676c1edd90031e13a105795b617d5. The latest applicable [BAGUETTE Core continuity v0.2](../coordination/BAGUETTE_Core_Research_Continuity_v0.2.md) says the 02W M9 package has already returned and narrow **non-privileged RGB/RGB-D/proprioceptive verification commissioning** has started. The published [camera-I/O work](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md) retains source inspection and reporting-only repairs but **does not establish a successful rendered-camera neutrality audit, an accepted sensor verifier or fresh M9a results**. The owner's actual pause/current server state is not verified by Frontier Watch. Keep tasks, seeds, 800-action budget, intervention, thresholds, evaluator and baseline frozen pending the existing Core gate.

Public identity **AURA**; **AETHER/AETHER-CL** remain historical experiments; **BAGUETTE** is provisional internal Core name. AURA's 02 = Core, 05 = watch, 06 = engineering; Embodied-AI's 02 = VLA lab and 05 = experiments. Do not confuse owners or duplicate baselines.

## October 29 research delta, independently checked

| Priority | Paper/item, first submission or revision | Evidence and decision | Execution impact |
| --- | --- | --- | --- |
| **Highest prior-art pressure** | [RoboDoctor](https://arxiv.org/abs/2610.35604) v1 **Oct 26** | Policy/agent supervision, bounded correction, linked reusable experience; [official code](https://github.com/THUSI-Lab/RoboDoctor) README inspected; author 54-task results, **no causal isolation of cross-episode experience**. **DEEP DIVE** | MONITOR/BACKLOG: augment WP1; do not install into M9a |
| **Highest prior-art pressure** | [RoboAuto](https://arxiv.org/abs/2610.36533) v1 **Oct 27** | Object/scene/interaction knowledge, active evidence gathering, stage-level effect checking. **DEEP DIVE** | MONITOR/BACKLOG: compare privileged inputs and cost of probing |
| **Challenging online WAM requirement** | [PDRVLA](https://arxiv.org/abs/2610.37381) v1 **Oct 27** | Predict future RGB/depth/flow **during training**, use lightweight physical tokens for fast action without online video rollout. **DEEP DIVE** | NEXT-CHECKPOINT design alternative **only if compatible VLA baseline**; not a newly authorized experiment |
| **Counterfactual learning** | [Rollback](https://arxiv.org/abs/2610.36068) v1 **Oct 26** | World-model imaginary rollback/branching + real-data refinement; not real robot rewinding. **READ→DEEP DIVE** | BACKLOG; start with simulator checkpoint oracle later |
| **3D/fast control & sensing** | [E0.5](https://arxiv.org/abs/2610.36011) v1 **Oct 26**; [ActiveAlign](https://arxiv.org/abs/2610.36859), [VLA-Stem](https://arxiv.org/abs/2610.37378) v1 **Oct 27** | Native 3D predictive WAM, active calibration/touch alignment, fast safety refinement under fixed VLA. **READ/WATCH** | BACKLOG; no new sensors/simulator migration |
| **Historical revision, not a new launch** | [UniManip](https://arxiv.org/abs/2602.13086) **v1 Feb 13, revised Oct 24** | Agentic operational graph, dynamic object-centric scene, geometric grounding, memory/recovery. **DEEP DIVE prior art** | MONITOR/BACKLOG; update innovation comparison |
| **Benchmarks** | [RoboDojo official news](https://robodojo-benchmark.com/) **Oct 24–27** | GO-3 Nano Preview agent-track Oct 27 61.90 score/56.42% success; PyRUA-Lean Oct 24 55.26/50.35; real track separate. **WATCH** | MONITOR; track by category/dimension, not global winner |

**Upstream already covered (Oct 26):** AW-0, P² Progress Probes, Echo, FastHarness, WholeBodyMem/HuMeGo, UniWALM, UniFlowWAM, OpenTac; Isaac Lab 3.0 and NVIDIA Oct 20–21. AURA independently rechecked official AW-0 and FastHarness repo READMEs and selected primary abstracts, **not their published measurements by executing anything**. CPU-only FastHarness principle can be an **Embodied-AI** reproduction candidate; AURA should reuse it rather than duplicate. Two distinct earlier FastVLA implementations remain in the original WP3 feasibility queue.

**Interpretation differs from simple architecture stacking:** RoboDoctor/RoboAuto/UniManip narrow novelty for a generic planner+state+verifier+recovery, while PDRVLA shows *training-time physical predictive supervision* may substitute for a separate online WAM on some tasks. Policy-native P²/Echo status still needs true physical outcome validation; alarm performance alone does not justify a recovery action. All headline numbers are **author-reported**.

## What HQ, Core/02 and teammates should do with this

Keep [October 19 WP1–WP4](2026/2026-10-19-team-work.md) and their [Chinese version](2026/2026-10-19-team-work.zh-CN.md) as the actual proposed allocation template. [October 29 handoff](2026/2026-10-29-handoff.md) / [中文版](2026/2026-10-29-handoff.zh-CN.md) extends rather than multiplies packages:

- **D1 / 06:** establish M9a's actual current operator authorization and Vulkan/render/MP4/packet/neutrality blocker; preserve Core freeze before new scientific evaluation.
- **D2 / WP1 / 02:** add RoboDoctor, RoboAuto, UniManip, PDRVLA vs DynaHarness to same-policy/budget and information-privilege comparison, isolate a falsifiable **remaining** question.
- **D3 / WP3:** optional source-only feasibility for one accessible learned baseline against two FastVLA, AW-0/PDRVLA/E0.5; coordinate with Embodied-AI's baseline owner before duplicate implementation.
- **D4 / HQ:** actual teammate names, effort, reviews, dates and compute remain **unassigned** until user/HQ approval; WP2/WP4 can continue only under their own approved preparation scope.

**The one existing proposed next experimental question stays evidence freshness / task-state invalidation after accepted sensing.** Cost-aware Continue/Reobserve/Recover and explicit migration/transfer are alternatives requiring their own Core decision. **Zero new active or newly nominated experiments this week.**

## Working hypothesis and evidence standard

Reliable manipulation may need task-relevant history, current physical evidence, selective actions, and learning from diagnosed outcomes, but these functions might be implemented by **rules, structured state, learned temporal features, distilled world-model supervision, procedural memory, or hybrids**. A separate online world model, external memory database or heavy verifier is **not mandatory** absent an ablation showing added value under matched task, intervention and latency costs.

The controlled physical branch and M0–M8 audits are valuable even if prior art overlaps. Novelty claims must rest on nonprivileged physical outcome correctness, intervention costs, failure attribution and held-out transfer, not just an architecture diagram.

Older [October 22](2026/2026-10-22.md), [October 19](2026/2026-10-19.md), and [October 15](2026/2026-10-15.md) issues remain unchanged; historical radar is in Git history. The [trend ledger](TREND_LEDGER.md) records one Oct 29 hypothesis refinement (online world-model inference is optional).

## Execution-impact footer

**Continue:** authorized M9a camera/render/Vulkan commissioning/repair, respecting current pause and Core scientific protocol gate.  
**Change now:** none to experiment/protocol/architecture; record narrowed prior-art/novelty claims for Core review.  
**Next checkpoint:** zero newly nominated experiments; existing evidence-freshness candidate after accepted sensing.  
**Deferred:** full RoboDoctor/RoboAuto/AW-0/E0.5/PDRVLA reproductions, sim-stack migration, new hardware and long-term learning integrations.  
**Evidence produced:** primary abstract/project and official repo reading, upstream cross-check, bilingual decision packet. No new CPU test, model inference, native run, audited evidence or assignment.
