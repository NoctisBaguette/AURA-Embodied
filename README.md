# AURA-Embodied

## Adaptive Unified Robotic Agents

Research project exploring generalizable physical agents through adaptive manipulation intelligence, memory, and embodied AI systems.

---

## Research Direction

**Adaptive Robotic Manipulation Intelligence**

**面向多场景迁移的自主机器人操作智能系统研究**

Long-term vision:

**Towards Generalizable Physical Agents: Adaptive Manipulation, Memory, and Self-Improving Robotics**

---

## Core Philosophy

The robot is the body.

The intelligence system is the research object.

AURA-Embodied studies how physical agents acquire, transfer, maintain, recover, and improve manipulation intelligence across:

- objects;
- tasks;
- environments;
- embodiments;
- experiences.

The project is not defined by a single trend or architecture. VLA, VLM, world models, memory, planning, policies, and learning methods are treated as components of larger physical intelligence systems.

---

## Research Workflow

```
Study existing systems
        ↓
Reproduce
        ↓
Build experiments
        ↓
Modify components
        ↓
Measure results
        ↓
Identify limitations
        ↓
Develop improvements
```

---

## Architecture Concept

AETHER Framework:

```
Perception
    ↓
World Understanding
    ↓
Reasoning
    ↓
Action
    ↓
Verification
    ↓
Failure Diagnosis
    ↓
Recovery
    ↓
Learning
```

---

## Repository Structure

- `aura-core` — core architecture and shared interfaces
- `aura-perception` — visual understanding and perception
- `aura-manipulation` — manipulation skills and policies
- `aura-memory` — memory and adaptation systems
- `aura-sim` — simulation experiments and benchmarks
- `aura-system` — robotics integration and deployment
- `aura-research` — research notes, experiments, and analysis
- `aura-docs` — project documentation

---

## Research Memory

This repository is also the external memory of AURA-Embodied.

It records:

- research decisions;
- literature analysis;
- experiments;
- failures;
- hypotheses;
- architectural evolution.

## Prototype Implementations

- [AETHER-CL v0.1 — Prototype A held-cube experiment](aura-sim/prototype_aether_cl/README.md)
  — fixed policy, passive verification, bounded recovery and audited A100
  magnitude evaluation. M0–M4 findings
  [returned to 02](docs/research/experiments/AETHER_CL_06_01_Return_to_02.md);
  [M5 verification-gating attribution](docs/research/experiments/AETHER_CL_M5_Attribution.md)
  is complete, independently audited and [accepted by 02](docs/research/experiments/AETHER_CL_M5_02_Research_Review_v0.1.md).
  [M6 support placement/release](docs/research/experiments/AETHER_CL_M6_Placement.md):
  native execution and [independent audit](docs/research/experiments/AETHER_CL_M6_Results.md)
  are complete. V2 rescues none of 62 failed placements; all retries abort before release.
  Prototype A remains open; insertion, physically applied disturbances and a
  non-privileged verifier remain later closure dimensions. The
  [M6 return to 02](docs/research/experiments/AETHER_CL_M6_Return_to_02.md) was [accepted by 02](docs/research/experiments/AETHER_CL_M6_02_Research_Review_v0.1.md).
  The active round is [M6R effect-aligned lowering/release](docs/research/experiments/AETHER_CL_M6R_Placement.md)
  under DEC-0005; [fresh native evidence is audited](docs/research/experiments/AETHER_CL_M6R_Results.md), with 70 paired placement rescues and no observed healthy regressions. [Return to 02](docs/research/experiments/AETHER_CL_M6R_Return_to_02.md) before further scope. This is the first AETHER experiment, not AETHER v1.0.
