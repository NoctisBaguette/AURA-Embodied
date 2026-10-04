# AETHER Architecture Evolution v0.1

## From Sequential Pipeline to Adaptive Physical Intelligence Framework

Status: Research checkpoint

---

## 1. Purpose

The original AETHER representation:

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

was useful as an initial capability inventory.

After studying embodied AI systems and developing the architecture concept further, this representation is no longer treated as a fixed execution pipeline.

Current interpretation:

> AETHER is a capability-and-interface framework for analyzing and designing adaptive physical intelligence systems.

Capabilities do not necessarily correspond to independent modules. A single model may provide multiple capabilities, and one capability may require multiple interacting components.

---

## 2. Core Architectural Shift

Old question:

> How does information flow through a robot system?

Updated question:

> How does an autonomous physical agent maintain itself through interaction with the real world?

A physical agent requires continuous closed-loop interaction:

```
Current belief
 ↓
Desired state transition
 ↓
Physical execution
 ↓
Observation
 ↓
Comparison
 ↓
Correction / Recovery
 ↓
Experience update
```

---

## 3. Current AETHER Principles

### 3.1 Capability Framework

Important capabilities include:

- perception;
- world understanding;
- task state;
- reasoning;
- planning;
- policy / skill execution;
- physical interaction;
- verification;
- failure diagnosis;
- recovery;
- memory;
- learning.

These are capability concepts, not mandatory software modules.

---

### 3.2 Multi-timescale Intelligence

Physical intelligence operates across multiple timescales:

- control loop: milliseconds;
- skill loop: seconds;
- task loop: minutes;
- experience and learning loop: long term.

AETHER investigates how these loops interact.

---

### 3.3 State-Centric Intelligence

A robot does not act directly from raw observations.

Relevant state includes:

- world state;
- task state;
- execution state;
- embodiment state;
- experience context;
- uncertainty.

State should include more than values:

```
value
+
confidence
+
source
+
validity
+
dependencies
```

---

## 4. Long-Horizon Intelligence

Long horizon does not mean unlimited context.

It means:

> Maintaining, updating, invalidating, and retrieving information according to future decision relevance.

Important concepts:

- context lifetime;
- dependency tracking;
- selective rollback;
- revalidation;
- task commitments.

A completed task step may become invalid if later events violate the assumptions that future actions depend on.

---

## 5. Verification and Recovery

Verification is not only a final check.

It exists across levels:

- control level: did execution occur?
- skill level: did manipulation succeed?
- task level: did the desired state change occur?
- dependency level: are previous assumptions still valid?

Recovery is hierarchical:

```
Local correction
 ↓
Skill adaptation
 ↓
Subtask recovery
 ↓
Task replanning
 ↓
Strategy change
```

---

## 6. Experience as Future Capability

Experience is not equivalent to replay data.

A useful experience contains:

- context;
- initial state;
- intent;
- action;
- observed transition;
- expected transition;
- outcome;
- failure cause;
- recovery;
- lesson;
- confidence;
- applicability scope.

The learning process is:

```
Physical interaction
 ↓
Episode
 ↓
Interpretation
 ↓
Causal abstraction
 ↓
Reusable knowledge
```

---

## 7. Embodiment-Aware Transfer

A central hypothesis:

> Manipulation intelligence should separate transferable knowledge from embodiment-specific execution.

Transferable:

- object understanding;
- task knowledge;
- desired physical effects;
- interaction principles.

Embodiment-specific:

- trajectories;
- force profiles;
- gripper actions;
- motor commands.

The robot body is a variable, not the research target.

---

## 8. Research Hypotheses

### H1 — Multi-level feedback

Adaptive physical intelligence requires interacting feedback loops.

### H2 — Dependency-aware long horizon

Long-horizon capability depends on maintaining relevant dependencies rather than storing unlimited history.

### H3 — Verification-centered autonomy

Reliable autonomy requires knowing whether intended physical effects occurred.

### H4 — Recovery as intelligence

Recovery capability may be more meaningful than first-attempt success.

### H5 — Experience transformation

Experience should become reusable capability through abstraction.

### H6 — Embodiment-aware transfer

General manipulation intelligence requires separating intent from realization.

### H7 — Adaptive intelligence allocation

Agents should decide when to act, observe, predict, retrieve memory, or replan.

---

## 9. Open Questions

- What information requires explicit representation?
- What can remain latent inside learned models?
- When do world models provide measurable value?
- What is the correct embodiment interface?
- How should experience become reusable knowledge?
- Where should modular boundaries exist?

---

## 10. Next Research Phase

AETHER should continue through:

```
Study existing systems
 ↓
Reproduce
 ↓
Compare
 ↓
Identify limitations
 ↓
Form hypotheses
 ↓
Modify components
 ↓
Experiment
 ↓
Update architecture
```

This document records an architectural evolution checkpoint, not a final architecture.
