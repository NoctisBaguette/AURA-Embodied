# AURA Frontier Watch — Current Research Radar

**Last updated:** 2026-10-09  
**Scope:** early October 2026  
**Status:** active AURA research radar

## Working system hypothesis

Current combined evidence from the AURA and Embodied-AI frontier watches supports a refined working hypothesis:

> **Reliable manipulation likely requires access to task-relevant history, physical/task state, predictive information, trustworthy evidence of outcomes, and recovery/learning mechanisms. Which of these capabilities must be explicit, which can remain integrated inside learned policies, and how they should interact across timescales must be determined experimentally.**

This is a hypothesis to test, not an architecture to defend.

## Highest-priority developments

| Development | AURA relevance | Current disposition |
|---|---|---|
| DynaHarness | execution governance, verification, failure attribution, replanning | **DEEP DIVE + REPRODUCE** |
| HELM | episodic memory, learned state verification, rollback/replanning | **DEEP DIVE + baseline candidate** |
| CRIS-0 / Aether AI | explicit task state, causal world modeling, verification, retry/replan | **DEEP DIVE / external comparator** |
| Long-WAM | long causal visual history under real-time control | **DEEP DIVE + REPRODUCE candidate** |
| VPP2 | strong WAM baseline, RoboDojo leader, Tsinghua-linked open research | **DEEP DIVE + baseline/reproduction candidate** |
| EvoMem-VLA | state-evolution memory and progress tracking | **DEEP DIVE** |
| The Planning Limits of Latent World Models | bounded predictive planning | **DEEP DIVE** |
| RoboCoach | world-model-guided failure localization and targeted supervision | **DEEP DIVE + REPRODUCE** |
| FailBank | runtime correction -> persistent learning | **DEEP DIVE** |
| FoldBack | selective rollback and minimum-change recovery | **DEEP DIVE** |
| D²-VLA | dual-timescale memory and long-horizon manipulation | **DEEP DIVE** |
| FineART | explicit subtask supervision and long-horizon bimanual control | **DEEP DIVE** |
| RoboICL | episodic interaction memory and in-context adaptation | **DEEP DIVE conceptually** |
| Magic-W0 / CtrlWAM / ATI-VLA | action-relevant and physically consistent world modeling | **READ -> DEEP DIVE** |
| Rho | embodiment midtraining and corrective adaptation | **READ + REPRODUCE candidate** |
| RobotWorld / RoboQuest | information seeking and completion verification | **READ / DEEP DIVE conceptually** |
| Rephrase Before You Act | instruction robustness as a failure source | **READ / small reproduce** |
| OpenViTac | tactile/contact-rich evaluation | **READ / WATCH** |
| RealtimeWAM / ESP | latency-aware policy execution | **READ / WATCH** |
| RawVLA | sensor/ISP robustness | **WATCH / evaluation backlog** |
| RoboDojo / WorldArena 2.0 | broader evaluation of manipulation and world models | **WATCH closely** |

## Competitive signal — AETHER prior art is now substantial

AURA should **not** claim novelty merely from:

```
strong policy
+ memory
+ execution monitor
+ verification
+ rollback / recovery
+ replanning
```

Relevant external systems now include:

- **DynaHarness** — execution governance, grounding, failure attribution, substitution and replanning;
- **HELM** — episodic memory, learned verification, rollback and replanning;
- **CRIS-0** — explicit task state, causal prediction, tool/policy orchestration, verification and retry/replanning;
- **FoldBack** — selective rollback and trajectory repair;
- **RoboCoach** — failure-localized supervision;
- **FailBank** — persistent learning from runtime corrections.

The immediate research question is:

> **What do these systems already solve, what remains unsolved, and can AURA demonstrate a simpler, more reliable, or more general architecture through controlled experiments?**

Potential remaining AURA research space:

- diagnosis that separates perception, task-state, semantic, policy, geometry/contact, control, and environment failures;
- hierarchical minimum-cost recovery across control-, skill-, subtask-, and task-level timescales;
- choosing between integrated temporal memory, explicit external memory, and hybrid memory;
- explicit outcome/state-transition representation rather than raw historical snapshots;
- converting successful recovery into persistent reusable experience;
- bounded, action-relevant world-model use for selection and verification;
- separation of transferable task knowledge from embodiment-specific execution;
- architecture ablations proving which explicit capabilities are actually necessary;
- latency-aware architecture design.

**Branch 02 action candidate:** perform a structured AETHER ↔ DynaHarness ↔ HELM ↔ CRIS-0 comparison before strengthening any novelty claim.

## Current synthesis

A useful capability view is now:

```
task goal / task state
          ↕
history / memory / state evolution
          ↕
reasoning / planning
          ↓
fast policy / capability
          ↕
bounded physical prediction
          ↓
physical execution
          ↕
verification / evidence gathering
          ↓
failure diagnosis
          ↓
hierarchical recovery
          ↓
persistent learning
```

Important qualifications:

- not every capability must be a separate module;
- longer historical context and longer prediction horizon are different variables;
- recovery does not imply learning;
- action completion does not imply intended outcome completion;
- verification may include deciding to gather more information before acting;
- additional intelligence is only useful if latency remains compatible with physical control.

## Active architecture questions

1. **Integrated vs explicit memory**  
   Long-WAM argues for learned causal history; HELM and EvoMem-VLA argue for explicit structured memory. Compare rather than assume.

2. **State representation**  
   CRIS-0 and EvoMem-VLA strengthen the case for task-relevant state / state-transition representations.

3. **World-model role**  
   Current evidence favors bounded, action-relevant prediction around selection/verification over assuming the world model is the entire long-horizon planner.

4. **Recovery hierarchy**  
   FoldBack and DynaHarness motivate local correction -> retry -> rollback -> alternate capability -> subtask replan -> task replan.

5. **Recovery-to-learning**  
   FailBank / RoboCoach motivate converting failure and recovery evidence into persistent improvement.

6. **Information sufficiency**  
   RobotWorld / RoboQuest motivate explicit evaluation of whether the agent knows enough to act and whether the task is truly complete.

7. **Latency**  
   Long-WAM, RealtimeWAM, and ESP make response time a first-class architecture metric.

## Naming / communication risk

Aether AI is now publicly operating in the same technical neighborhood as AURA's internal **AETHER** architecture name, including causal world models, task-state reasoning, verification, recovery, and physical-agent intelligence.

This creates searchability and communication ambiguity.

**HQ + Branch 02 action candidate:** decide whether AETHER remains an internal codename or should be renamed before external publication. Frontier Watch does not make that decision.

## Near-term AURA research queue

### Tier A — direct architecture / competitor review

1. DynaHarness
2. HELM
3. CRIS-0
4. Long-WAM
5. The Planning Limits of Latent World Models
6. RoboCoach
7. FailBank

### Tier B — strong model / mechanism baselines

8. VPP2
9. EvoMem-VLA
10. FoldBack
11. D²-VLA
12. FineART
13. RoboICL
14. Magic-W0
15. CtrlWAM
16. Rho

### Tier C — preserve and watch

17. ATI-VLA
18. RobotWorld / RoboQuest
19. Rephrase Before You Act
20. RealtimeWAM / ESP
21. OpenViTac
22. RawVLA
23. RoboDojo / WorldArena 2.0
24. human-behavior pretraining / cross-embodiment scaling

## Experiment candidates

1. **Execution governance ablation**  
   Raw policy vs one-step replanning vs governed execution.

2. **Integrated history vs external memory**  
   Short history vs long causal history vs task/event memory vs hybrid.

3. **Snapshot vs state-evolution memory**  
   Compare stored frames/keyframes with explicit before/after state changes.

4. **Failure-localized supervision**  
   Random extra data vs data targeted at the first failing skill.

5. **Recovery -> persistent learning**  
   Recovery only vs selective reuse / policy update.

6. **Hierarchical minimum-change recovery**  
   Local correction, skill retry, rollback, alternate skill, subtask replan, full task replan.

7. **Bounded world-model selector / verifier**  
   No prediction vs short-horizon action ranking / verification.

8. **Information-gathering before action**  
   Immediate commitment vs inspect/test before deciding.

9. **Latency accounting**  
   Measure observation age, policy time, verifier time, prediction time, detection time, and recovery time.

10. **Strong-policy + AETHER intervention**  
    Where tractable, test architecture interventions around a strong baseline such as VPP2 rather than a weak policy.

## Current architecture caution

AETHER should remain a **capability-and-interface research framework**.

Do not add components simply because frontier papers contain them. Each proposed mechanism should survive:

```
external evidence
-> explicit hypothesis
-> controlled intervention
-> measurable improvement
-> architecture decision
```

The target is not the largest architecture diagram. It is the **smallest architecture that measurably maintains reliable physical autonomy under uncertainty**.
