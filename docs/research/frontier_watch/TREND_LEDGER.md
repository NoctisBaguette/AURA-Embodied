# AURA Frontier Watch — Trend Ledger

This file tracks persistent research patterns relevant to AURA-Embodied. It should evolve more slowly than `CURRENT.md`.

## T1 — From action prediction to governed manipulation-agent loops

**Status:** strengthening strongly

Independent systems increasingly add capabilities around a foundation policy:

- task/subtask state;
- memory;
- bounded execution;
- verification;
- failure attribution;
- replanning;
- recovery;
- persistent adaptation.

Representative signals now include DynaHarness, HELM, CRIS-0, RoboCoach, FineART, RoboICL, FailBank, D²-VLA, and FoldBack.

**AURA interpretation**

The VLA/WAM/policy increasingly looks like one powerful capability inside a larger physical-intelligence loop rather than the entire agent.

**Open question**

Which surrounding capabilities must be explicit, and which can remain latent/integrated inside learned models?

---

## T2 — World models are becoming bounded, actionable, and physically constrained

**Status:** strengthening strongly

Signals:

- Planning Limits: predictive ranking degrades beyond practical planning horizons; nearby subgoals and feedback help.
- RoboCoach: world-model imagination is used for targeted failure diagnosis.
- Magic-W0: structured physical transition modeling is coupled to control.
- CtrlWAM: action/future supervision is made physically consistent.
- ATI-VLA: predictive representations are aligned with action generation.
- VPP2: manipulation-specific video pretraining and a distilled visual planner are used for action generation.
- CRIS-0: predicted action consequences are compared against physical outcomes during execution.

**AURA interpretation**

A world model should not automatically be treated as the long-horizon planner.

Current stronger hypothesis:

```
long-horizon task reasoning
    -> nearby subgoal / candidate action
    -> bounded physical prediction
    -> action selection / verification
    -> execute
    -> reobserve / update state
```

World models should be evaluated by whether they improve physical decisions, not by visual fidelity alone.

---

## T3 — Recovery and learning are separate capabilities

**Status:** strengthening

Signals:

- DynaHarness emphasizes monitored execution, failure attribution, and recovery/replanning.
- HELM performs rollback/replanning around a verifier.
- FoldBack repairs a failed trajectory segment while preserving successful progress.
- RoboCoach uses failure localization to decide what new supervision to collect.
- FailBank turns useful runtime corrections into persistent policy updates.
- Online-ES uses failed trajectories as negative feedback.

**AURA interpretation**

A system can recover successfully and still fail to improve.

Distinguish:

- **Recovery:** survive the current failure.
- **Learning:** reduce the probability or cost of repeating it later.

AURA should test both explicitly.

---

## T4 — Embodied memory is decomposing into functional alternatives

**Status:** strengthening

Signals:

- D²-VLA: persistent history plus fast recent-state memory.
- FineART: explicit next-subtask/task-progress representation.
- RoboICL: episodic interaction memory.
- HELM: retrieved keyframe episodic memory.
- Optimus-R: reusable query-skill memory.
- FailBank: failure/correction memory.
- EvoMem-VLA: state-evolution / transition memory.
- Long-WAM: long historical context integrated directly into a causal world-action model.

**AURA interpretation**

"Memory" should not automatically mean one context buffer or one external database.

Candidate functional distinctions:

- working/recent-state memory;
- long integrated temporal context;
- task-state/progress memory;
- episodic interaction memory;
- state-evolution / action-outcome memory;
- failure/recovery memory;
- skill/procedural memory;
- longer-term semantic/world knowledge.

The architecture question is increasingly:

> **Which information should be represented explicitly, which should be compressed into learned temporal state, and which should be retrieved externally?**

---

## T5 — Transferable intelligence and embodiment-specific execution are separating

**Status:** strengthening

Signals:

- Rho: embodiment midtraining plus corrective adaptation.
- human-behavior pretraining directions such as Light-O1 / Figure.
- visual-tactile work that attempts to transfer interaction structure across embodiments.
- SCAR-style embodiment-invariant action representations.
- bimanual and multi-arm work separating shared semantics from embodiment-specific coordination.

**AURA interpretation**

A central architecture question remains:

> What manipulation knowledge should transfer across bodies, and what must remain embodiment-specific?

This should be tested with smaller controlled cross-end-effector or cross-robot experiments rather than assumed from scaling claims.

---

## T6 — Evaluation is broadening beyond first-attempt task success

**Status:** strengthening strongly

Relevant dimensions increasingly include:

- task progress;
- task-state correctness;
- failure location;
- recovery success;
- repeated-failure rate;
- adaptation efficiency;
- memory dependence;
- generalization;
- sensor robustness;
- controllability / physical consistency;
- false task-completion declarations;
- information-gathering cost;
- latency and observation age;
- cost of replanning/recovery.

Signals include RoboDojo, WorldArena 2.0, RobotWorld, RoboQuest, RawVLA-style robustness, and recovery/adaptation systems.

**AURA interpretation**

A single binary episode-success metric is insufficient for AETHER experiments.

---

## T7 — AETHER's easy novelty space is narrowing

**Status:** high priority / strengthening

The competitive picture now includes several systems overlapping AETHER themes:

- **DynaHarness:** governed physical execution, failure attribution, substitution/replanning;
- **HELM:** episodic memory, learned verification, rollback/replanning;
- **CRIS-0:** explicit task state, causal prediction, verification, retry/replanning;
- **FoldBack:** selective rollback and trajectory repair;
- **RoboCoach:** failure-localized supervision;
- **FailBank:** persistent learning from runtime corrections.

**AURA interpretation**

AETHER cannot rely on "policy + memory + verifier + recovery wrapper" as a novelty claim.

Possible differentiated research space must be established experimentally, potentially around:

- richer failure diagnosis;
- hierarchical minimum-cost recovery;
- explicit task-state / state-transition representations;
- hybrid integrated + external memory;
- recovery-to-learning;
- bounded predictive verification;
- cross-embodiment interfaces;
- latency-aware architecture selection;
- ablation-driven evidence for the smallest sufficient architecture.

**Required action**

Branch 02 should compare AETHER against DynaHarness, HELM, and CRIS-0 before making stronger architecture or novelty commitments.

---

## T8 — Task state and action outcomes are becoming first-class representations

**Status:** emerging / strengthening

Signals:

- FineART exposes subtask state.
- EvoMem-VLA records state evolution rather than isolated history.
- CRIS-0 organizes execution around task-relevant variables, predicted consequences, and outcome checks.
- RoboCoach records the first failing subtask.
- RobotWorld exposes false completion and physical-state tracking failures.

**AURA interpretation**

Long-horizon manipulation may benefit from representing not only "what do I see?" but:

```
what matters for the current task?
what changed after my action?
did the intended condition become true?
what condition must hold before the next step?
```

This is a strong candidate for controlled experiments, not yet a mandate for one fixed symbolic state representation.

---

## T9 — Long history and long prediction horizon are different resources

**Status:** new / important

Long-WAM shows substantial gains from longer **historical context** when temporal pretraining lets the policy use it effectively.

Planning-limit work simultaneously shows that reliable **future rollout horizon** can remain bounded.

**AURA interpretation**

These findings are complementary, not contradictory:

```
longer useful past
does not imply
longer reliable imagined future
```

AURA should separately measure:

- historical memory horizon;
- prediction horizon;
- planning horizon;
- action/replanning frequency.

---

## T10 — Latency is becoming an architectural constraint, not a deployment footnote

**Status:** emerging

Signals:

- Long-WAM co-designs long-context prediction with real-time runtime.
- RealtimeWAM targets one-step generation and asynchronous execution.
- ESP targets one-forward-pass multimodal action generation.
- CRIS-0 reports fast interruption / replanning in controlled demonstrations.

**AURA interpretation**

Adding reasoning, world models, verification, or memory can reduce physical reliability if the robot reacts too late.

Future AETHER evaluations should measure:

- observation age;
- action-generation latency;
- verification latency;
- perturbation-detection latency;
- replanning/recovery latency;
- total intervention cost.

---

## T11 — Aether AI creates a naming and communication collision with AETHER

**Status:** project-risk signal

Aether AI is now publicly working on causal world models, task-state reasoning, verification, recovery, and physical-agent intelligence — close to AURA's AETHER architecture territory.

**AURA interpretation**

This is not a scientific trend, but it is a serious external-communication issue:

- searchability;
- naming ambiguity;
- attribution;
- paper / presentation clarity;
- confusion between company work and AURA architecture.

**Required action**

HQ + Branch 02 should decide whether **AETHER** remains an internal codename or should be renamed before external publication. Frontier Watch does not make that decision.
