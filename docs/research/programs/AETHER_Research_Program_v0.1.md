# AETHER Research Program v0.1

## Purpose

This document converts the AETHER architecture exploration into a research program.

AETHER Architecture Evolution v0.1 described how adaptive physical intelligence may be organized. This document describes how those ideas should be tested experimentally.

The goal is not to prove a final architecture immediately. The goal is to create a research loop:

Study systems

↓

Form hypotheses

↓

Build controlled experiments

↓

Measure limitations

↓

Update architecture

---

# Research Philosophy

AURA-Embodied studies how physical agents acquire, transfer, maintain, recover, and improve manipulation intelligence.

The research object is the intelligence system, not a specific robot platform.

VLA, VLM, world models, memory, planners, policies, and learning methods are treated as components that may contribute to larger physical intelligence systems.

---

# Core Research Questions

## 1. Verification and Recovery

Question:

Can systems with verification and recovery outperform action-only policies under realistic disturbances?

Hypothesis:

A slightly weaker policy with strong verification and recovery may achieve higher autonomy than a stronger policy without recovery mechanisms.

Potential experiment:

Compare:

- policy only;
- policy + verification;
- policy + verification + recovery.

Metrics:

- final task success;
- recovery success;
- recovery cost;
- human intervention rate.

---

## 2. Experience to Capability

Question:

How can physical interaction experience become reusable intelligence?

Hypothesis:

Structured experience containing context, causes, outcomes, and lessons may transfer better than raw trajectory replay.

Potential experiment:

Compare:

- no memory;
- trajectory memory;
- structured experience memory.

Metrics:

- adaptation speed;
- transfer performance;
- failure reduction.

---

## 3. Embodiment Transfer

Question:

What manipulation knowledge transfers between different robot bodies?

Hypothesis:

Intent-level physical effects and task knowledge may transfer better than direct action representations.

Potential experiment:

Compare:

- action/trajectory transfer;
- intent/state-transition transfer with embodiment adaptation.

Metrics:

- adaptation samples;
- success rate;
- robustness.

---

## 4. Explicit State vs Latent Context

Question:

When does explicit task/world state improve physical autonomy?

Hypothesis:

Explicit state representations are valuable when information must be shared, inspected, corrected, or reused across multiple capabilities.

Potential experiment:

Compare:

- latent context only;
- latent context + structured task state.

Metrics:

- long-horizon completion;
- interruption recovery;
- diagnosis accuracy.

---

## 5. Adaptive Intelligence Allocation

Question:

Should a physical agent decide when to use deeper reasoning, prediction, memory, or verification?

Hypothesis:

Adaptive allocation of intelligence resources can improve efficiency without reducing reliability.

Potential experiment:

Compare:

- always-maximal reasoning;
- uncertainty/risk-triggered reasoning.

Metrics:

- performance;
- latency;
- compute cost.

---

# AURA Benchmark Direction

AURA should eventually develop evaluation environments focused on adaptive manipulation rather than only first-attempt success.

Potential dimensions:

## Object Generalization

New objects, materials, shapes, and affordances.

## Task Generalization

Transfer between manipulation skills and compound tasks.

## Environment Generalization

Changes in layout, obstacles, and disturbances.

## Embodiment Generalization

Transfer between robot arms, grippers, and platforms.

## Experience Generalization

Whether previous interactions improve future performance.

---

# Experimental Development Path

```text
Hypothesis

↓

Simulation Prototype

↓

Benchmark Evaluation

↓

Architecture Modification

↓

Physical Robot Validation

↓

Deployment-oriented Evaluation
```

---

# Initial Prototype Direction

The first AETHER prototype should not attempt to build a complete robot foundation model.

A reasonable first system:

```text
Observation

↓

Policy

↓

Physical Interaction

↓

Verification

↓

Failure Diagnosis

↓

Recovery

↓

Experience Update
```

The purpose is to test whether system organization improves adaptive behavior.

---

# Simulation First Strategy

Initial experiments should prioritize simulation because it enables:

- controlled failures;
- large-scale evaluation;
- rapid iteration;
- architecture ablation.

Physical robots should be used for validation after intelligence hypotheses are tested.

---

# Future Work

Major future decisions requiring deeper investigation:

- modular vs unified vs hybrid architectures;
- explicit vs latent intelligence boundaries;
- memory architecture;
- world model role;
- embodiment interfaces;
- benchmark design.
