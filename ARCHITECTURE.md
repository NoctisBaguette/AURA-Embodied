# AURA Adaptive Manipulation-Intelligence Architecture

Status: **evolving research architecture**

Public project identity: **AURA-Embodied / AURA**  
Historical internal codename: **AETHER**

AURA studies adaptive robotic manipulation intelligence for generalizable
physical agents. The architecture is not a fixed neural network, software
pipeline, or mandatory collection of modules. It is a capability-and-interface
framework whose assumptions must be tested experimentally.

## 1. Public identity and historical naming

Use **AURA** as the public architecture/project identity. Historical AETHER and
AETHER-CL experiment identifiers remain unchanged for provenance. Because an
external Physical-AI company named Aether AI now works in nearby technical
territory, AETHER should not currently be promoted as the main public brand.

## 2. Research center

AURA focuses on **object-centric upper-body manipulation intelligence**:

- grasping, transport, placement and reorientation;
- insertion and contact-rich manipulation;
- opening/closing, transfer/pouring, organization, assembly and tool use;
- compound and long-horizon tasks built from these skills.

Navigation, SLAM, locomotion, gait generation and lower-body control are not
current primary research targets.

The continuing intelligent-picking / soft-grasping system is an active physical
branch of AURA. It is both a source of real manipulation failures and an
important validation environment; simulation and public baselines provide
controlled causal experiments around those physical questions.

## 3. Central analysis abstraction: task-relevant physical state transition

The current architecture is organized around a common analysis/interface
abstraction:

```text
task-relevant physical/task state
        ↓
intended physical state transition
        ↓
action-conditioned feasibility assessment
        ↓
policy / skill / controller
        ↓
physical interaction
        ↓
observation and state update
        ↓
observed physical state transition
        ↓
verification
        ↓
continue / correct / recover / replan / learn
```

This does **not** require every implementation to serialize symbolic states or
explicit transition objects. Learned, latent, geometric, symbolic and hybrid
representations remain valid research alternatives. The purpose of the
abstraction is to make planning, execution, verification and recovery refer to
the same intended physical effects.

AURA's updated core question is:

> How can a physical agent continuously maintain, execute, verify, repair,
> transfer and improve task-relevant physical state transitions during object
> manipulation?

## 4. Task-relevant state

Task-relevant state is a first-class research object, but AURA should avoid
building a universal ontology before experiments justify it.

Candidate state content includes:

- object identity/type, pose, geometry and physical-property estimates;
- relations such as supported-by, held-by, inside, contacting, aligned-with,
  occluded-by and reachable-from;
- functional states such as open/closed, grasped/released, inserted/not
  inserted, stable/unstable and blocked/reachable;
- task state: current objective, completed transitions, active skill, unmet
  preconditions, failed conditions and preserved progress;
- embodiment state: arm/end-effector, workspace, kinematic limits, sensing,
  contact capability and execution limits;
- uncertainty and information provenance.

A state item may conceptually carry:

```text
value
+ confidence
+ source/provenance
+ timestamp
+ validity
+ dependencies
```

Physical interaction can make previously valid state stale. State update,
invalidation and dependency tracking are therefore architecture questions, not
only data-management details.

## 5. Feasibility and reliability are distinct

AURA distinguishes two related questions.

### Planning feasibility

> Given the current state, embodiment and candidate action/skill, is the
> intended physical transition expected to be achievable?

Conceptually:

```text
P(transition succeeds | current state, intended effect, embodiment, action)
```

### Execution reliability

> Did this particular physical execution actually realize and maintain the
> intended transition?

A plan may be semantically valid, collision-free and kinematically reachable
while the physical execution still fails through slip, incomplete release,
contact error, disturbance or stale assumptions.

These quantities may be implemented by the same model or different mechanisms.
Their conceptual distinction is retained even when implementation is unified.

## 6. Planning and verification should share transition semantics

AURA should avoid a planner that reasons about one meaning of state while an
unrelated binary verifier judges another.

The working architecture is:

```text
estimated state S_t
    ↓
expected transition ΔS_expected
    ↓
execution
    ↓
updated estimated state S_t+1
    ↓
observed transition ΔS_observed
    ↓
compare expected vs observed
```

"Share transition semantics" does **not** mean planner and verifier must use the
same neural representation. They should agree on the task-relevant effects,
constraints and evidence needed to decide whether a transition occurred.

## 7. Verification is selective, temporal and multi-level

AURA's experiments now support several bounded conclusions:

- verification can prevent unnecessary or harmful recovery invocation;
- controller completion is not equivalent to physical task completion;
- contact-rich manipulation may invalidate an earlier alignment state during
  execution;
- transient deviation is not automatically an action-worthy failure.

Verification therefore may need to operate at multiple timescales and distinguish:

```text
temporary deviation
persistent/action-worthy failure
recoverable failure
failure requiring escalation
```

Non-privileged verification remains an open architecture problem.

## 8. Recovery: minimum sufficient response and corrective envelopes

AURA should first update the believed physical/task state after a failure and ask
what actually became invalid.

Working response hierarchy:

```text
continuous/contact correction
local pose correction
retry current skill
regrasp / alternate contact
switch execution strategy
revise current subtask
replan remaining task
full restart
safe abort / human assistance
```

The architecture principle is:

> Preserve still-valid progress and invalidate/repair only what is actually invalid.

Only the lower part of this hierarchy has been experimentally studied so far;
dependency-aware rollback and minimum-change replanning remain hypotheses.

M8 adds an evidence-backed concept: a local recovery has a **corrective
envelope**. A recovery mechanism should eventually expose or estimate:

- applicability/preconditions;
- expected success;
- expected cost;
- required sensing;
- confidence;
- escalation target.

How to estimate those quantities remains open.

## 9. Multi-timescale physical intelligence

AURA retains the multi-timescale view:

- fast control/contact regulation;
- skill-level execution and verification;
- task-level state/progress and recovery;
- longer-term experience and learning.

Disturbance accommodation while a grasp remains valid is distinct from recovery
after the invariant is lost. Future work may study when fast regulation should
escalate to regrasp, recovery or replanning.

## 10. Sensing as an information interface

The physical branch uses **RGB and RGB-D collaborative sensing**, not an
RGB-D-only route.

Possible research configurations include:

- full RGB-D;
- one RGB-D plus multiple RGB cameras;
- RGB-first with learned depth/state inference;
- uncertainty-triggered depth queries;
- rich-sensing teacher -> cheaper deployment.

A useful architecture view is to treat sensing as information sources with
capability, uncertainty, latency and cost. Whether depth is always needed or
queried adaptively is a research question.

Non-privileged verification may additionally use proprioception and, when
available, pressure/vacuum/tactile/force information.

## 11. Migration is a core evaluation principle

AURA studies transfer across:

1. objects;
2. tasks;
3. environments;
4. embodiments;
5. experiences.

Multiple demonstrations are not automatically transfer evidence. A transfer
experiment should specify source condition, target condition, shared mechanism,
allowed adaptation, adaptation cost, target performance, transfer gap and
failure modes.

The current M0-M8 Prototype-A experiments establish robustness/recovery evidence,
not a completed migration study. Future experiments must measure transfer
explicitly rather than retrospectively relabeling task diversity as transfer.

## 12. Models are replaceable capabilities

AURA may use VLA/VLM systems, world models, world-action models, diffusion or
imitation policies, classical planners, structured or learned memory,
deterministic verification and hybrid systems.

No one model family defines the project.

A strong future comparison is:

```text
existing modular manipulation system
vs
strong learned/VLA policy
vs
the same baseline + selected AURA mechanisms
```

The research question is which system-level capabilities remain valuable across
different action-generation mechanisms.

## 13. Evaluation strategy

Phase I should prefer established public task/benchmark infrastructure where
possible (for example ManiSkill, LIBERO, RoboTwin or RoboCasa) and add controlled
AURA evaluation conditions.

AURA should not promise a universal new benchmark during Phase I.

Relevant evaluation dimensions include:

- task success;
- verification quality;
- recovery success and cost;
- unnecessary intervention and healthy-case preservation;
- latency;
- uncertainty/calibration;
- transfer/adaptation cost;
- sensor/hardware adaptation cost.

## 14. Evidence rule

Architecture should evolve through:

```text
external evidence
→ explicit hypothesis
→ controlled intervention
→ measurable result
→ failure analysis
→ architecture decision
```

Do not add a capability because it sounds desirable, and do not promote an
experiment-specific implementation detail into a universal architectural law.

## 15. Immediate open questions

The next architecture investigation should resolve enough of the following to
design non-privileged verification without prematurely freezing a universal
state ontology:

1. What is the minimum task-relevant state schema?
2. How should intended physical transitions be represented: symbolic,
   geometric, learned or hybrid?
3. What interface should connect predicted feasibility to observed execution
   reliability?
4. What should a non-privileged verifier output beyond success/failure?
5. How should state invalidation and preserved progress be represented?
6. How should recovery applicability/corrective envelopes be represented?
7. How should transfer and adaptation cost be measured?
8. How should sensing configuration and active depth queries enter the
   architecture?
9. Which public baseline/task best isolates the next hypothesis?

These are research questions, not frozen module requirements.
