# AETHER Framework

AETHER is the evolving physical-intelligence architecture concept of AURA-Embodied.

Its purpose is **not** to prescribe one fixed neural architecture or one software module per capability. AETHER is a capability-and-interface framework for analyzing, designing, and experimentally testing adaptive physical intelligence systems.

## Historical Starting Point

The project originally used the following sequential representation as a capability inventory:

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

This remains useful as a list of required capabilities, but it should **not** be interpreted as the current assumption that embodied intelligence is a one-directional pipeline.

## Current Interpretation — after Intelligence Landscape v0.1

The first landscape synthesis found that embodied intelligence is better treated as a system of interacting capabilities operating at different timescales.

A current working representation is:

```
Memory ↔ World Understanding ↔ Reasoning / Planning ↔ Policy ↔ Physical Interaction
                                      ↕
                                  Verification
                                      ↓
                              Diagnosis / Recovery
                                      ↓
                                   Learning
```

This is **not a frozen architecture**. It is a research scaffold.

### Capability / Interface Principle

Names such as `Memory`, `Reasoning`, `Verification`, or `Recovery` denote capabilities and interfaces, not assumed software modules.

A capability may ultimately be implemented by:

- one foundation model;
- several specialized models;
- structured state;
- deterministic logic;
- learned policies;
- external tools;
- or a hybrid of these.

Whether a capability should be explicit, latent, modular, or unified is itself a research question.

## Architectural Themes from the Landscape

Current frontier systems increasingly distinguish among:

- **semantic intelligence** — understanding goals, objects, context, and task meaning;
- **physical intelligence** — generating and executing manipulation behavior;
- **embodiment-specific execution** — adapting shared knowledge to a particular robot body.

AURA therefore treats the boundary between transferable intelligence and embodiment-specific execution as an important architectural question.

## Open AETHER Research Questions

The current architecture work should investigate rather than assume:

1. Which capabilities must be explicit?
2. Which capabilities can remain latent inside learned models?
3. How should task state and memory be represented?
4. Should verification continuously monitor execution or occur only after actions?
5. How should failure diagnosis influence replanning and recovery?
6. How should capabilities interact across different timescales?
7. What information should cross the boundary between transferable intelligence and embodiment-specific execution?
8. Which architecture choices actually improve measurable physical autonomy?

## Evidence Rule

AETHER should evolve from evidence:

```
Observation
    ↓
Existing-system limitation
    ↓
Hypothesis
    ↓
Prototype / intervention
    ↓
Experiment
    ↓
Architecture update
```

Do not expand AETHER merely because a capability sounds conceptually desirable.

## Design Principle

Embodied intelligence is a system problem.

Models provide capabilities.
Architecture organizes interaction.
Physical execution creates consequences.
Verification and failure expose weaknesses.
Experience should become future capability.
