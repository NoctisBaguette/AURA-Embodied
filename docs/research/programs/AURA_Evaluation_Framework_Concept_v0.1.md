# AURA Evaluation Framework Concept v0.1

## Purpose

This document defines the current evaluation philosophy for AURA-Embodied.

The goal is not to measure only whether a robot can complete a manipulation task once. The goal is to evaluate whether a physical agent can maintain, recover, transfer, and improve manipulation intelligence through interaction.

---

# Core Principle

Traditional evaluation often asks:

> Can the robot complete the task?

AURA evaluation asks:

> Can the robot maintain and improve intelligent behavior when reality differs from expectation?

Therefore, evaluation must include:

- capability;
- robustness;
- recovery;
- adaptation;
- transfer;
- experience utilization.

---

# Evaluation Dimensions

## 1. Manipulation Capability

Measures basic competence:

- grasping;
- placing;
- pushing;
- inserting;
- organizing;
- assembly.

Metrics:

- success rate;
- efficiency;
- execution quality.

---

## 2. Robust Interaction

Measures behavior under disturbances:

Examples:

- object movement;
- changed object properties;
- occlusion;
- environmental changes;
- uncertainty.

Metrics:

- degradation under disturbance;
- robustness curve;
- recovery after perturbation.

---

## 3. Long-Horizon Autonomy

Long horizon is not defined as simply longer action sequences.

It concerns:

- maintaining dependencies;
- preserving task state;
- detecting invalid assumptions;
- selective rollback;
- revalidation.

Metrics:

- interruption recovery;
- dependency preservation;
- unnecessary restart rate.

---

## 4. Experience Adaptation

Measures whether previous interaction improves future behavior.

Important distinction:

Experience is not only raw replay.

Useful experience contains:

- context;
- state transition;
- outcome;
- failure cause;
- recovery strategy;
- reusable lesson.

Metrics:

- adaptation speed;
- data efficiency;
- improvement after experience.

---

## 5. Embodiment Transfer

Measures whether manipulation intelligence transfers across robot bodies.

Examples:

- different grippers;
- different arms;
- different sensors.

Questions:

- What knowledge transfers?
- What requires embodiment adaptation?

Metrics:

- adaptation data required;
- transfer efficiency;
- final performance.

---

# Failure Taxonomy

AURA evaluation should record not only failure occurrence, but failure understanding.

Possible categories:

- perception failure;
- state estimation failure;
- planning failure;
- execution failure;
- verification failure;
- recovery failure.

A valuable evaluation output should describe:

- what failed;
- why it failed;
- whether the agent detected the failure;
- whether it improved afterwards.

---

# Episode-Level Evaluation

An evaluation episode should preserve more than success/failure.

Conceptually:

```
Episode
    ↓
Context
    ↓
Initial state
    ↓
Intent
    ↓
Action
    ↓
Observed transition
    ↓
Outcome
    ↓
Failure/success interpretation
    ↓
Experience extraction
```

The benchmark itself should produce useful research data.

---

# Simulation and Physical Evaluation

The framework supports both:

## Simulation

Purpose:

- scalable experiments;
- controlled failures;
- architecture comparison.

## Physical validation

Purpose:

- real-world uncertainty;
- sensor limitations;
- embodiment effects.

Simulation develops hypotheses. Physical experiments validate them.

---

# Current Research Questions

Open questions:

1. Which metrics best represent autonomy?
2. How should recovery quality be measured?
3. How should experience transfer be evaluated?
4. How much explicit structure is needed?
5. How should benchmark tasks balance difficulty and interpretability?

---

# Status

This is a conceptual evaluation framework, not a finalized benchmark.

Future work should define:

- concrete tasks;
- datasets;
- simulation environments;
- metrics;
- physical validation protocols.
