# AURA Frontier Watch — Trend Ledger

This file tracks persistent research patterns relevant to AURA-Embodied. It should evolve more slowly than `CURRENT.md`.

## T1 — From action prediction to governed manipulation-agent loops

**Status:** strengthening

Independent signals increasingly add capabilities around a foundation policy:

- task/subtask state;
- memory;
- bounded execution;
- verification;
- failure attribution;
- replanning;
- recovery;
- persistent adaptation.

Representative signals include DynaHarness, RoboCoach, FineART, RoboICL, FailBank, and D²-VLA.

**AURA interpretation**

The VLA/policy increasingly looks like one powerful capability inside a larger physical-intelligence loop rather than the entire agent.

**Open question**

Which surrounding capabilities must be explicit, and which can remain latent inside learned models?

---

## T2 — World models are becoming bounded and operational

**Status:** strengthening strongly

Signals:

- Planning Limits: useful predictive ranking degrades beyond the model's practical horizon; nearby subgoals and feedback help.
- RoboCoach: world-model imagination is used for targeted failure diagnosis.
- Magic-W0: structured physical transition modeling is coupled to control.
- CtrlWAM: action/future supervision is made physically consistent.
- ATI-VLA: predictive representations are explicitly aligned with action generation.

**AURA interpretation**

A world model should not be assumed to be the long-horizon planner.

Current stronger hypothesis:

```
long-horizon task reasoning
    -> nearby subgoal
    -> bounded physical prediction
    -> action selection / verification
    -> execute
    -> reobserve
```

World models should be evaluated by whether they improve physical decisions, not by visual fidelity alone.

---

## T3 — Recovery and learning are separate capabilities

**Status:** strengthening

Signals:

- DynaHarness emphasizes monitored execution, failure attribution, and recovery/replanning.
- RoboCoach uses failure localization to decide what new supervision to collect.
- FailBank turns useful runtime corrections into persistent policy updates.
- Online-ES uses failed trajectories as negative feedback.

**AURA interpretation**

A system can recover successfully and still fail to improve.

Distinguish:

- **Recovery:** survive the current failure.
- **Learning:** reduce the probability or cost of repeating it later.

AURA should test both.

---

## T4 — Embodied memory is decomposing into multiple functional classes

**Status:** emerging / important

Signals:

- D²-VLA: persistent history plus fast recent-state memory.
- FineART: explicit next-subtask/task-progress representation.
- RoboICL: episodic interaction memory.
- Optimus-R: reusable query-skill memory.
- FailBank: failure/correction memory.

**AURA interpretation**

"Memory" should not automatically mean one context buffer or one database.

Candidate functional distinctions:

- working/recent-state memory;
- task-state/progress memory;
- episodic interaction memory;
- failure/recovery memory;
- skill/procedural memory;
- longer-term semantic/world knowledge.

This taxonomy is not frozen. The research question is which distinctions improve manipulation reliability and adaptation.

---

## T5 — Transferable intelligence and embodiment-specific execution are separating

**Status:** strengthening

Signals:

- Rho: embodiment midtraining plus corrective adaptation.
- cross-embodiment human-action work such as Light-O1 / Figure's human-behavior pretraining direction;
- tactile/visual-tactile work that tries to transfer interaction structure across human and robot embodiments;
- bimanual and multi-arm work that explicitly separates shared semantics from embodiment-specific coordination.

**AURA interpretation**

A central architecture question remains:

> What manipulation knowledge should transfer across bodies, and what must remain embodiment-specific?

This should be tested with smaller controlled cross-end-effector or cross-robot experiments rather than assumed from scaling claims.

---

## T6 — Evaluation is broadening beyond first-attempt task success

**Status:** strengthening

Relevant dimensions increasingly include:

- task progress;
- failure location;
- recovery success;
- repeated-failure rate;
- adaptation efficiency;
- memory dependence;
- generalization;
- sensor robustness;
- controllability and physical consistency;
- cost/latency of replanning.

Signals include RoboDojo, WorldArena 2.0, RawVLA-style sensor robustness, and recovery/adaptation papers.

**AURA interpretation**

A single binary episode-success metric is insufficient for AETHER experiments.

---

## T7 — DynaHarness narrows the easy novelty space for AETHER

**Status:** new / high priority

DynaHarness overlaps with a major AETHER theme: a strong policy embedded inside an execution-governance loop with monitoring, grounding, failure attribution, substitution/replanning, and recovery.

**AURA interpretation**

AETHER cannot rely on "policy + verifier + recovery wrapper" as a novelty claim.

Possible differentiated research space must be established experimentally, potentially around:

- richer failure diagnosis;
- hierarchical minimum-cost recovery;
- task state and multi-timescale memory;
- recovery-to-learning;
- bounded predictive verification;
- cross-embodiment interfaces;
- ablation-driven architecture selection.

**Required action**

Branch 02 should compare AETHER against DynaHarness before making stronger architecture or novelty commitments.
