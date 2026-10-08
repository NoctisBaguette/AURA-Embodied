# AURA-Embodied Research Log

This file records research decisions and evolution.

---

## 2026-10-08 — Frontier Watch integration and AETHER competitive signal

### Existing Knowledge

The AURA Frontier Watch was cross-checked against the companion Embodied-AI Research frontier-watch archive. Important overlapping research themes now include:

- governed execution around strong policies;
- explicit task state and memory;
- bounded world-model prediction for action selection/verification;
- failure attribution and recovery;
- converting recovery signals into persistent learning;
- embodiment transfer and adaptation.

DynaHarness is now treated as a serious external comparison point because it overlaps with AETHER's execution-governance, verification, failure-attribution, and recovery territory.

### Observation

Independent AURA and Embodied-AI scans found different papers but converged on a similar system-level pattern:

```
long-horizon task structure / state
        ↕
memory / experience
        ↕
reasoning / planning
        ↓
fast policy / capability
        ↕
bounded physical prediction
        ↓
verification
        ↓
failure diagnosis
        ↓
recovery
        ↓
persistent learning
```

### Hypothesis

A robust manipulation agent may need long-horizon task structure and explicit memory above a fast physical policy, bounded predictive models around action selection/verification, and a recovery loop that turns diagnosed failures into reusable experience.

This remains a working hypothesis rather than a fixed AETHER design.

### Experiment Opportunity

Priority candidates:

1. governed execution ablations;
2. failure-localized supervision;
3. bounded world-model action selection/verification;
4. recovery-to-learning experiments;
5. memory-type ablations;
6. hierarchical recovery under controlled failure injection;
7. small cross-embodiment transfer studies.

### Decision

Create a dedicated durable Frontier Watch memory under:

`docs/research/frontier_watch/`

Frontier Watch should not directly rewrite `ARCHITECTURE.md` or `DECISION_LOG.md`. Architecture-changing signals should be handed to branch 02 for explicit review, while experiment candidates should flow to branch 06.

### Notes

See:

- `docs/research/frontier_watch/CURRENT.md`
- `docs/research/frontier_watch/TREND_LEDGER.md`
- `docs/research/frontier_watch/2026/2026-10-08.md`

---

## Entry Template

### Date

YYYY-MM-DD

### Topic


### Existing Knowledge

What systems, papers, or approaches were studied?

### Observation

What capability or limitation was identified?

### Hypothesis

What do we believe may improve the system?

### Experiment Opportunity

How can this be tested?

### Decision

What direction should AURA pursue?

### Notes

Additional reasoning and future questions.
