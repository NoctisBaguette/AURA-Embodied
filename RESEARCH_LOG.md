# AURA-Embodied Research Log

This file records research decisions and evolution.

---

## 2026-10-09 — Expanded AETHER prior-art map and architecture questions

### Existing Knowledge

The weekly Frontier Watch added several high-priority systems:

- HELM: episodic memory + learned state verification + rollback/replanning;
- Long-WAM: integrated long historical context in a causal world-action model;
- EvoMem-VLA: state-evolution memory;
- FoldBack: selective rollback and trajectory repair;
- CRIS-0 from Aether AI: explicit task-relevant state + causal prediction + verification + retry/replanning;
- VPP2: a strong Tsinghua/RobotEra-linked world-action model and current RoboDojo simulation leader.

### Observation

AETHER's easy novelty space is narrower than previously understood. Memory, verification, rollback, execution governance, task-state tracking, and replanning all have substantial external prior art.

At the same time, the literature does not establish one universally best architecture. Important unresolved design choices remain:

- integrated temporal memory vs explicit external memory vs hybrid;
- snapshot history vs state-transition / outcome memory;
- bounded predictive verification vs long-horizon imagination;
- local recovery vs hierarchical rollback/replanning;
- recovery vs persistent learning;
- architecture intelligence vs physical response latency.

Aether AI also creates a significant naming collision with the internal AETHER architecture name in nearly the same technical domain.

### Hypothesis

The more defensible AURA direction is not to add more modules by default, but to identify the **smallest architecture that measurably maintains task-relevant state, physical foresight, outcome verification, appropriate recovery, and future improvement under uncertainty.**

### Experiment Opportunity

Priority comparisons now include:

1. strong policy vs governed execution;
2. integrated long history vs explicit event/task memory;
3. snapshot vs state-evolution memory;
4. full restart vs minimum-change hierarchical recovery;
5. no prediction vs bounded action ranking/verification;
6. recovery-only vs recovery-to-learning;
7. latency-aware architecture ablations.

VPP2 is a candidate strong policy baseline where tractable.

### Decision

Frontier Watch does **not** modify AETHER architecture directly.

Branch 02 should review:

- AETHER vs DynaHarness vs HELM vs CRIS-0;
- memory implementation choices;
- task-state representation;
- recovery hierarchy;
- role of world models;
- latency constraints;
- the AETHER/Aether naming collision.

06 should receive experiment candidates only after architecture/research prioritization, without interrupting active milestones solely to chase new papers.

### Notes

See:

- `docs/research/frontier_watch/2026/2026-10-09.md`
- `docs/research/frontier_watch/CURRENT.md`
- `docs/research/frontier_watch/TREND_LEDGER.md`

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
