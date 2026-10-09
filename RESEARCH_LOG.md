# AURA-Embodied Research Log

This file records research decisions and evolution.

---

## 2026-10-09 — BAGUETTE provisional Core and chat-continuity protocol

### Observation

The architecture/research conversation is becoming the persistent intellectual
core of AURA and will eventually exceed individual chat context limits. The
project also now has recurring Frontier Watch input, Work-mode deep-research
branches and substantial experiment histories on a diverged engineering branch.

A durable continuity protocol is therefore necessary so that research decisions
do not depend on one chat transcript.

### Decision

Use **BAGUETTE** as a provisional internal name for the Core architecture/research
thread and possible successor codename to AETHER. This is not yet a public or
frozen architecture name.

Create
`docs/research/coordination/BAGUETTE_Core_Research_Continuity_v0.1.md`
to define branch routing, authority, checkpoint cadence and chat-rollover
procedure.

Historical AETHER/AETHER-CL experiment names remain unchanged.

### Notes

The Core normal-chat thread remains final architecture-decision authority.
02W/Work investigations return synthesis to Core; 05 supplies frontier evidence;
06 returns experimental evidence.

---

## 2026-10-09 — Zero Point architecture refinement: state transitions, migration, sensing and physical branch

### Existing Knowledge

The Zero Point application synthesis combined the existing physical picking /
soft-grasping system, Prototype-A M0-M8 evidence, current architecture work and
Frontier Watch findings.

### Observation

Several project-level relationships became clearer:

- the physical picking system is an active integrated AURA branch rather than a
  completed legacy demo;
- migration is a core evaluation principle rather than an optional extension;
- the physical state transition is a useful common abstraction linking planning,
  execution, verification and recovery;
- planning feasibility and execution reliability should be distinguished;
- non-privileged verification should compare expected and observed physical
  transition evidence rather than become an unrelated binary classifier;
- M8 motivates recovery applicability/envelope and escalation;
- RGB and RGB-D should be treated as collaborative sensing sources, with
  uncertainty/cost-aware depth use as a research direction.

### Hypothesis

AURA may be organized around task-relevant physical state transitions while
remaining implementation-agnostic: explicit, latent and hybrid state mechanisms
should be compared experimentally rather than assumed.

Planning and verification should share compatible transition semantics, while
recovery should update invalid state, preserve valid progress and choose the
minimum sufficient corrective level when possible.

### Experiment Opportunity

The next deep-design problem is non-privileged transition verification.

A disciplined sequence is likely:

1. hold task/recovery fixed and replace privileged verification with a realistic
   RGB/RGB-D/proprioceptive state-estimation/verifier interface;
2. after that interface is stable, freeze it and test an explicit transfer axis
   with adaptation-cost metrics.

This avoids conflating sensing realism and migration in the first comparison.

### Decision

Create the architecture checkpoint
`docs/research/architecture/aura/AURA_State_Transition_Architecture_v0.2.md`
and update the public `ARCHITECTURE.md` / `ROADMAP.md`.

Do not copy the application handoff's provisional decision IDs into
`DECISION_LOG.md` yet because main and the active experiment branch have
diverged and the experiment branch already contains DEC-0001 through DEC-0008.
Reconcile histories before issuing new global decision numbers.

### Notes

AETHER remains historical/internal provenance; public-facing architecture
language should use AURA pending the naming review.

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
