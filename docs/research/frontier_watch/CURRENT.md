# AURA Frontier Watch — Current Research Radar

**Languages:** English · [简体中文](CURRENT.zh-CN.md) · [Chinese reading index / 中文阅读入口](README.zh-CN.md)

**Updated:** 2026-10-19. **Latest update type:** cross-project decision checkpoint with targeted source checks; not a new full weekly scan or reproduction.

## Start here: decisions and collaboration

Read the [October 19 decision brief](2026/2026-10-19.md), then the [evidence register](2026/2026-10-19-evidence.md) and [team work packages](2026/2026-10-19-team-work.md). These combine AURA's October 15 watch with Embodied-AI's October 19 watch and translate the findings into reviewable choices for the user, HQ and Core/02.

**HQ needs:** which bounded tasks to assign, to whom, with what time/resource limit and reviewer.

**Core/02 needs:** which hypothesis is worth the next experiment, what comparison discriminates it, what remains unsupported, and whether any active work actually needs to change.

**Teammates need:** exact inputs, outputs, acceptance criteria, dependencies, exclusions and return format. The linked work packages provide those; they are not assignments or new experimental authorization.

## Current execution context — do not reset development

Public architecture identity is **AURA**. AETHER/AETHER-CL remains historical; BAGUETTE is provisional internal Core naming. The current [architecture](../../../ARCHITECTURE.md) already includes task-relevant state transitions, temporal/selective verification and bounded recovery.

The experiment branch `06-01/aether-cl-m0` contains newer M9a commissioning records than the October 9 Core continuity summary. The [commissioning-start record](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Commissioning_Start_v0.1.md) and [camera I/O record](https://github.com/NoctisBaguette/AURA-Embodied/blob/06-01/aether-cl-m0/docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md) describe narrow sensor-verifier preparation, retained reporting corrections and a separate fresh-evaluation gate.

The inspected records do not establish completed native camera neutrality or sensor-verifier acceptance. Respect any current operator/HQ pause. No server health, new native result, fresh protocol approval or teammate availability is inferred here.

## What is newly useful from the combined watches?

| Theme | Relevant sources | Research disposition | Execution impact |
| --- | --- | --- | --- |
| Evidence freshness and state revision | REMM + TacitVLA + once-per-episode Fast-VLA | DEEP DIVE scoped to current state/sensing questions | Next-checkpoint candidate after sensing baseline acceptance |
| Cost-aware intervention | RESCUE + ForkCast; existing AURA recovery evidence | DEEP DIVE | Preserve as the next alternative, not additional M9a recovery behaviors |
| Efficient learned baseline | Two distinct FastVLA repositories | READ / reproduction-feasibility candidate | One isolated source/artifact feasibility task if HQ allocates capacity |
| Action-aware episode retrieval | Robota-Embed | DEEP DIVE conceptually | Backlog until usable corpus, action interface and artifacts exist |
| Evaluation and labeling | LABIT; Anvil as an upstream review lead | READ | Small annotation/protocol task can support current work |
| Skill reuse and selective reasoning | RoboRSI / ChunkAct; SEAR / LoopWAM retained leads | READ / DEEP DIVE by a bounded question | Not an instruction to train or reproduce every system |

**Critical distinction:** `Garfield-kh/FastVLA` caches task context and runs a streaming actor. `jiuyixu25/FastVLA` prunes visual tokens around compatible VLA backbones. Do not conflate their models, dependencies, checkpoints or experiments.

TacitVLA/Robota-Embed project extracts indicated forthcoming code; a complete runnable release was not verified in this pass. The two FastVLA READMEs advertise more concrete implementation paths, but no checkpoint download, import, local test or native evaluation was executed here.

## Decisions awaiting the user, HQ and Core

1. **D1:** confirm current M9a gate/blocker and support needs; do not add new mechanisms to its frozen scientific scope.
2. **D2:** choose one next comparison. Current proposal: evidence freshness/invalidation after sensing acceptance; intervention-value evaluation remains an alternative.
3. **D3:** choose one learned-baseline feasibility effort, reuse compatible Embodied-AI work, or defer it.
4. **D4:** assign selected preparation tasks to actual teammates with reviewers and time caps; leave unselected work in backlog.

The detailed options, acceptance criteria and local decision register are in the [team packet](2026/2026-10-19-team-work.md). No decision is marked approved by this radar.

## Working hypothesis

Reliable manipulation may benefit from task-relevant history, current evidence-supported state, action-relevant prediction and selective recovery/learning. The implementation could be explicit, learned, compiled or hybrid. Longer context, more modules, generated reasoning and more retries are not themselves proof of reliability or transfer.

The current decision pressure is not simply whether to add memory. It is **which information must stay fresh, which computation must finish before action, and what evidence justifies intervention**. Compare simple alternatives before expanding the architecture.

## Preserved earlier research map

The [October 15 issue](2026/2026-10-15.md) retains RoboRSI, SEAR, ForkCast, REMM, RESCUE, LoopWAM, ChunkAct and physical-interface evaluation. The [October 9 issue](2026/2026-10-09.md) retains Long-WAM, HELM, CRIS-0, VPP2, EvoMem-VLA, FoldBack and related prior art. Earlier frontier classifications remain research leads, not executable assignments or newly revalidated numerical results.

DynaHarness, HELM and similar systems remain comparison points. Broad component overlap requires careful novelty wording, not abandoning a valid experimental instrument. The historical Aether naming concern has already been addressed in the current public-naming guidance; do not reopen it automatically each week.

The complete pre-update radar is preserved in [Git history](https://github.com/NoctisBaguette/AURA-Embodied/blob/1986bca1530ac779e34f8d3de5cfe5a2364915c4/docs/research/frontier_watch/CURRENT.md).

## Execution-impact footer

**Continue:** latest authorized M9a commissioning/repair scope, subject to current pause and native acceptance gates. Independent physical engineering keeps its own authorization.

**Change now:** no new model, intervention, native run or architecture change. Update coordination to the newer branch record.

**Next checkpoint:** normally zero or one strongest new experiment; evidence freshness/invalidation is the current proposal.

**Deferred:** large model training, full memory/world-model stacks, additional benchmark platforms and hardware acquisition.

**Evidence produced:** source review and a decision/collaboration packet only. Historical reports, architecture decisions and frozen engineering sources are unchanged.
