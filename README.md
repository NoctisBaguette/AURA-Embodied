# AURA-Embodied

## Adaptive Unified Robotic Agents

Research project exploring generalizable physical agents through adaptive manipulation intelligence, memory, and embodied AI systems.

**团队成员从这里开始：[START_HERE.md — 项目是什么、已经做了什么、如何自由探索与协作](START_HERE.md)。**

Quick navigation: [Current architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Frontier Watch](docs/research/frontier_watch/CURRENT.md) · [Exploration notes](docs/exploration/README.md).

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

The historical AETHER chain below is a capability inventory, not a prescribed one-way implementation. The current public architecture identity is **AURA**; see [ARCHITECTURE.md](ARCHITECTURE.md) for the task-relevant state-transition framework, recurrent verification, bounded recovery, transfer and sensing questions. Capabilities need not map one-to-one to software modules.

Historical inventory:

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

The following names describe the intended logical component areas, not a claim that every directory or subsystem is implemented:

- `aura-core` — core architecture and shared interfaces
- `aura-perception` — visual understanding and perception
- `aura-manipulation` — manipulation skills and policies
- `aura-memory` — memory and adaptation systems
- `aura-sim` — simulation experiments and benchmarks
- `aura-system` — robotics integration and deployment
- `aura-research` — research notes, experiments, and analysis
- `aura-docs` — project documentation

Current entry points and the main/engineering branch distinction are explained in [START_HERE.md](START_HERE.md). Follow linked records rather than assuming the full implementation is present on `main`.

---

## Research Memory

This repository is also the external memory of AURA-Embodied.

It records:

- research decisions;
- literature analysis;
- experiments;
- failures;
- hypotheses;
- architectural evolution;
- exploratory sources, unfinished questions and clearly labeled AI-assisted notes.

Exploration does not require prior assignment or a mature conclusion. Save sources and verification status; distinguish discovery from reviewed knowledge and experimental evidence. See [Exploration notes](docs/exploration/README.md). Merging an exploratory note does not adopt its claims or authorize a new experiment.
