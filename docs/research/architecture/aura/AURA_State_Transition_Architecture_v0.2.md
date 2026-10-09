# AURA State-Transition Architecture Refinement v0.2

Date: 2026-10-09  
Status: **02 architecture checkpoint after Zero Point application synthesis**  
Public identity: **AURA**  
Historical/internal provenance: **AETHER / AETHER-CL**

## Purpose

The Zero Point application process exposed several project and architecture
clarifications that materially change how AURA should be described. This note
classifies them instead of blindly promoting every application idea into a
technical decision.

The earlier AETHER v0.1 checkpoint remains historical evidence. This v0.2 note
does not declare a final robot architecture.

## What materially changed

### 1. The physical picking system is part of the research loop

The continuing intelligent-picking / soft-grasping system is not a completed
legacy demo or unrelated second project. It is AURA's concrete physical origin,
a continuing engineering/research branch, a source of real failures and a
primary place to validate selected mechanisms.

The research loop is therefore bidirectional:

```text
physical picking limitations
    ↓
general manipulation-intelligence question
    ↓
AURA hypothesis
    ↓
controlled simulation / public baseline
    ↓
physical validation and transfer
    ↓
architecture revision
```

### 2. Migration is a spine, not an optional future feature

AURA's Chinese research direction already encodes multi-scenario transfer.
Transfer must eventually be measured explicitly across objects, tasks,
environments, embodiments and experiences.

Important correction: M0-M8 show robustness and cross-task research progress,
but they are **not yet a formal transfer experiment** because task-specific
controllers and protocols changed. Task diversity must not be relabeled as
migration after the fact.

### 3. Physical state transition becomes the common architecture abstraction

The earlier v0.1 document already used desired state transitions. The new
checkpoint sharpens that idea into the common abstraction linking planning,
execution, verification and recovery:

```text
task-relevant state
→ intended physical transition
→ feasibility reasoning
→ execution
→ observed physical transition
→ verification / diagnosis
→ minimum sufficient response
```

This is an analysis/interface abstraction, not a requirement that every system
use an explicit symbolic graph.

### 4. Feasibility and reliability are separated

AURA now explicitly distinguishes:

- **planning feasibility:** whether a candidate action is expected to realize an
  intended transition;
- **execution reliability:** whether this physical execution actually realized
  and maintained the intended transition.

M6/M6R strongly motivate this distinction: controller-space completion was not
equivalent to the task-relevant physical effect.

### 5. Planning and verification should align semantically

The strong hypothesis is not "one exact state representation for every module."
That would be premature.

The refined hypothesis is:

> Planning and verification should refer to compatible task-state and
> state-transition semantics so that expected and observed effects can be
> compared meaningfully.

A structured planner and a learned verifier may still use different internal
representations.

### 6. Recovery needs applicability and escalation

M8 shows that the accepted local recovery has a bounded corrective envelope.
Future recovery selection should reason about applicability, expected success,
cost, sensing requirements and escalation.

Minimum-change rollback remains a hypothesis supported by architecture reasoning
and frontier prior art; AURA has not yet experimentally validated dependency-
aware rollback across a long-horizon task.

### 7. Verification is temporal

M7 retains an unnecessary recovery triggered by temporary instability. A verifier
must eventually distinguish transient deviation from persistent/action-worthy
failure, not only produce a binary label.

### 8. Sensor architecture is now tied to the physical branch

The summer system used RGB + RGB-D collaboratively. The next sensing question is
therefore not "replace privileged state with one camera" in the abstract.

Useful candidate designs include:

- RGB-D-rich state estimation;
- hybrid RGB + one/few RGB-D views;
- RGB-first with learned depth/state estimates;
- uncertainty-triggered depth use;
- rich-sensing teacher -> cheaper deployment.

Cost, latency, calibration and transfer across sensing configurations matter
alongside verification accuracy.

## Classification

### Frozen project decisions from HQ / application synthesis

- official namespace: AURA-Embodied; short name: AURA;
- AETHER remains historical/internal for provenance pending naming review;
- research center: transferable object-centric upper-body manipulation
  intelligence;
- navigation/locomotion are not primary scope;
- continuing picking/soft-grasping is an integrated active physical branch;
- migration is central to project evaluation;
- models are components rather than project identity;
- RGB and RGB-D are collaborative sensing sources;
- Zero Point is a one-year Phase-I stage, not the lifetime of AURA;
- Phase I should use public benchmarks/tasks plus controlled AURA protocols
  rather than promise a universal benchmark.

### Evidence-backed findings from Prototype A

- M5: verification has value as selective recovery invocation; recovery can be
  harmful when invoked unnecessarily.
- M6/M6R: controller-space completion can disagree with physical task completion;
  task-effect-aligned phase completion can matter causally.
- M7: contact-rich recovery can transfer the closed-loop pattern to insertion;
  verification timing/persistence can matter.
- M8: the pattern remains useful under a physics-engine force disturbance;
  local recovery has a bounded corrective envelope.
- Across M6/M7/M8, controller schedule completion is not a sufficient task
  success criterion.

### Strong working architecture hypotheses

- task-relevant state should be representable with uncertainty, provenance,
  validity and dependencies;
- planning and verification should share transition semantics;
- state should be updated/invalidated before choosing recovery or replanning;
- minimum-change/local repair should be preferred when sufficient;
- recovery mechanisms should expose an applicability envelope and escalation;
- non-privileged verification should compare expected and observed transition
  evidence;
- sensing may be actively allocated according to uncertainty and risk.

### Candidate directions, not decisions

- action-conditioned feasibility estimators;
- adaptive RGB/RGB-D depth querying;
- rich-sensing teacher -> RGB-heavy deployment;
- policy-independent AURA wrappers;
- state dependency graphs;
- persistent experience memory;
- recovery-to-learning;
- world-action-model-assisted action ranking/verification;
- cross-end-effector or cross-robot transfer.

## Architecture questions before M9

The previous planned 02W prompt was too narrow if it asks only "which camera
verifier should we use?"

Before M9, deep research should connect non-privileged sensing to the v0.2
state-transition architecture:

1. Define the **minimum experiment-specific task-relevant state** required for
   the selected task; avoid a universal ontology.
2. Define an intended transition representation that a planner/controller and
   verifier can both reference.
3. Specify non-privileged observations and how they update the state estimate.
4. Specify verifier output: observed transition, confidence/evidence,
   persistence and failure/effect mismatch—not merely a binary label.
5. Separate perception/state-estimation error from verification-decision error
   and recovery-execution error.
6. Decide whether M9 should only isolate sensing realism or also include a
   transfer axis.

### Important experimental-design caution

Migration is central to AURA, but combining a new sensor verifier and a transfer
experiment in one first M9 comparison may confound causal attribution.

A likely disciplined structure is:

```text
M9a: same validated task/recovery, replace privileged verification only
    ↓
establish sensor-verifier behavior
    ↓
M9b or next experiment: freeze verifier and test one explicit transfer axis
```

02W should challenge this proposal rather than assuming it.

## Internal comparison boundary

Nearby internal research directions may inform AURA's thinking, but they should
not be published as competitive comparisons without explicit approval. This
checkpoint therefore records the adopted architecture ideas without naming
private/internal comparison targets.

## Decision-log handling

Do **not** copy the application handoff's suggested DEC-0002...DEC-0010 numbers
directly.

The active experiment branch already contains DEC-0001 through DEC-0008, while
main contains only the earlier decision-log history. Decision numbering must be
reconciled after the branch histories are brought together.

Until then, this v0.2 architecture note records the classification above without
creating conflicting decision IDs.

## Next route

Normal 02 should use this checkpoint to rewrite the 02W mandate.

02W should investigate **task-relevant state + non-privileged transition
verification + M9 design**, not just choose a visual classifier.

No M9 implementation should begin before 02W returns and normal 02 approves a
frozen experiment.
