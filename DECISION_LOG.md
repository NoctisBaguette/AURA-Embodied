# AURA-Embodied Decision Log

This document records important project decisions, alternatives considered, and the reasoning behind them.

Research projects evolve. Decisions should remain traceable.

---

# DEC-0001

## Date

2026-10-04

## Topic

Interpret AETHER as an evolving capability-and-interface framework rather than a fixed linear pipeline.

## Context

The original AETHER representation used a sequential chain:

`Perception → World Understanding → Reasoning → Action → Verification → Failure Diagnosis → Recovery → Learning`.

After the first Embodied Intelligence Landscape study covering major systems including RT-1, RT-2, OpenVLA, π0/π0.5, GR00T, Gemini Robotics, and HomeBody, the project reached a more mature interpretation: embodied intelligence consists of interacting capabilities operating across different timescales, with recurrent feedback rather than a strictly one-directional pipeline.

The landscape also suggested increasing separation among semantic intelligence, physical intelligence, and embodiment-specific execution.

## Options Considered

1. Keep the original sequential AETHER pipeline as the assumed architecture.
2. Replace it immediately with a new fixed modular architecture.
3. Treat AETHER as an evolving capability/interface framework whose implementation choices remain research questions.

## Decision

Choose Option 3.

AETHER boxes represent capabilities and interfaces, not necessarily separate software modules or neural networks.

The framework should support concurrent and recurrent interaction, and architecture choices should be validated experimentally before becoming stronger project commitments.

## Reasoning

This avoids prematurely encoding assumptions such as:

- verification must happen only after action;
- failure diagnosis must be a standalone module;
- memory must be a separate subsystem;
- planning must always be explicit;
- one model cannot provide multiple capabilities;
- modularity is always superior to end-to-end learning.

Instead, AURA can compare explicit, latent, modular, unified, and hybrid implementations under controlled experiments.

## Future Re-evaluation Condition

Revisit this decision when experimental evidence supports a more specific architecture, or when a concrete AETHER prototype requires implementation-level interface commitments.

## Upstream Evidence

See `AURA-Embodied Intelligence Landscape v0.1` and the corresponding research history from branch 01.

---

# DEC-0002

## Date

2026-10-04

## Topic

Record AETHER Architecture Evolution v0.1 checkpoint.

## Context

Following deeper architecture exploration, AETHER evolved beyond a capability list into a broader research framework involving:

- multi-timescale feedback loops;
- state and uncertainty management;
- dependency-aware long-horizon intelligence;
- verification and hierarchical recovery;
- experience transformation;
- embodiment-aware transfer.

The checkpoint documents architectural evolution after comparing AETHER concepts against major embodied AI systems.

## Decision

Create `docs/research/architecture/aether/AETHER_Architecture_Evolution_v0.1.md` and associated Mermaid diagrams.

The checkpoint records:

- stable architectural principles;
- research hypotheses;
- open questions;
- experimental directions.

It does not define a final implementation architecture.

## Reasoning

The project should preserve architectural evolution rather than prematurely freezing a design.

Important conclusions:

- AETHER is a capability/interface framework, not a sequential pipeline.
- Physical intelligence requires interacting feedback loops across timescales.
- Long-horizon intelligence concerns relevant dependencies rather than unlimited context.
- Experience should become reusable capability rather than remain raw replay data.
- Embodiment should be treated as a variable with adaptation interfaces.

## Future Re-evaluation Condition

Revisit after experimental validation of candidate AETHER architectures, especially around:

- explicit versus latent state;
- memory mechanisms;
- verification and recovery systems;
- embodiment transfer.

---

# Decision Template

## Decision ID

Example: DEC-0002

## Date

YYYY-MM-DD

## Topic


## Context

Why does this decision need to be made?

## Options Considered


## Decision


## Reasoning

Why was this direction selected?

## Future Re-evaluation Condition

When should this decision be reconsidered?

## Notes

