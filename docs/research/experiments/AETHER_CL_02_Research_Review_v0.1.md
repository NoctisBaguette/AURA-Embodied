# AETHER-CL Prototype A — 02 Research Review and Next Scope

Date: 2026-10-05 (Asia/Shanghai)

Status: **02 accepts the 06-01 held-cube engineering round as valid evidence within its frozen scope. Prototype A remains scientifically open.**

This review uses the audited M2–M4 evidence returned by 06-01 at commit `21d74f135beebc2d2dea045e56df7fe0c74a935b`. It does not merge PR #1, widen the claim beyond the measured task, or activate Prototype B/C/D.

## 1. Evidence accepted by 02

02 accepts the following bounded findings:

1. The fixed nominal controller succeeds on the normal held-cube target-reaching task.
2. Passive verification (V1) preserves the baseline physical trace and detects the tested failures, but does not change task success because it does not intervene.
3. Verification-gated one-attempt recovery (V2) rescues all 180 matched V1 failures in the audited M4 sample, with no observed final-task regressions.
4. Recovery cost increases with disturbance magnitude.
5. Final task success, recovery-controller completion, precision and cost are distinct outcomes and must remain separately reported.
6. Strict fresh-process isolation, pre-intervention trace matching, rejected-evidence retention and machine replay are necessary parts of this experiment's validity.

The accepted M4 scope is finite: one Panda/cube simulator task, privileged simulator observations, synthetic cube relocations, 2.5 cm target tolerance, no release/support placement and no insertion.

## 2. Hypothesis update

### H3 — Verification-centered autonomy

Previous working hypothesis:

> Reliable autonomy requires knowing whether intended physical effects occurred.

**Updated status: partially supported as an observability/coordination hypothesis, not yet established as a causal necessity for task success.**

Evidence now shows that passive verification can detect the tested deviations with bounded latency, and V2 uses a confirmed failure to gate recovery. However, passive verification alone does not improve success, and no recovery-without-verification comparator has been run. Therefore the current evidence does **not** establish that explicit verification is necessary, superior to an ungated retry, or the source of V2's success improvement.

The next experiment must isolate the value of verification as a recovery gate.

### H4 — Recovery as intelligence

Previous working hypothesis:

> Recovery capability may be more meaningful than first-attempt success.

**Updated status: supported within the current synthetic held-cube scope.**

With the nominal controller held fixed, one bounded observed-state retry converts 180 matched V1 failures into final task successes in M4. The result demonstrates that final autonomy can exceed first-attempt policy success through recovery. It does not yet establish general recovery across tasks, perception, embodiments or realistic physical disturbances.

### H1 — Multi-level feedback

**Updated status: weak/partial support only.**

Prototype A demonstrates one useful skill/task-level closed loop. It does not yet validate the broader AETHER claim of interacting feedback loops across control, skill, task and experience timescales.

## 3. What the current result does not prove

The following claims are explicitly unsupported:

- explicit verification is necessary for recovery;
- V2 is better than a blind or scheduled retry policy;
- recovery generalizes to placement/release or insertion;
- recovery handles physically applied force/contact disturbances;
- camera-based perception can support the same verification loop;
- the current controller is precise or efficient;
- memory, world models, explicit task state or embodiment transfer are needed;
- Prototype A as originally scoped is complete.

The current result should be described as:

> **Observed-state verification plus one bounded, verification-gated retry improves final task success under the tested synthetic relocations while the nominal controller remains fixed.**

## 4. Scientific closure criteria for Prototype A

02 will not declare Prototype A scientifically complete until the following four closure dimensions are addressed.

### A. Causal attribution

Isolate the contribution of verification gating from the contribution of simply granting a refreshed-target retry.

Required comparison:

- baseline: fixed policy only;
- V1: fixed policy + passive verification;
- V2: fixed policy + verification-gated bounded recovery;
- V3: the same bounded recovery primitive under a preregistered ungated/scheduled trigger that does not consume verifier/failure-classifier output.

The exact V3 schedule must be frozen before evaluation and must not be selected from evaluation outcomes. V3 is an experimental causal control, not a proposed autonomous architecture.

### B. Task-semantic coverage

The original Prototype A scope included manipulation beyond held-cube target reaching. At minimum, add:

1. **support placement/release** — success requires release onto a support/target, not merely reaching while holding; and
2. **contact-rich insertion** — success requires geometric/contact alignment and insertion.

Each task requires its own frozen matched baseline and disturbance protocol. Current M4 results must not be silently reused as evidence for these tasks.

### C. Disturbance realism

At least one Prototype A task must be tested with a disturbance caused through simulator physics rather than direct object teleportation, for example a preregistered impulse/contact perturbation, obstacle/contact event, or other physically propagated disturbance.

Synthetic relocation remains valid for controlled causal tests, but is insufficient by itself for broader robustness claims.

### D. Verification observability

At least one frozen task/disturbance protocol must be replicated with **non-privileged observation used for the agent's verification decision** (for example RGB/RGB-D or another realistic sensor path), while privileged simulator state is retained only for scoring/audit.

This is required before claiming that Prototype A's verification mechanism is deployable beyond privileged simulator state.

Physical-robot validation is desirable later but is not required to close the simulation Prototype A research instrument. Any real-world claim requires a separate physical validation protocol.

## 5. Immediate next experiment — M5 Verification-Gating Attribution

02 selects causal attribution as the next engineering round because it is the strongest unresolved inference in the current evidence and can be tested without changing the nominal policy, task, verifier, motion primitives or task tolerance.

### Research question

> Does explicit failure-gated recovery provide measurable value over the same recovery capability invoked without verifier gating?

### Systems

- **Baseline** — unchanged fixed policy.
- **V1** — unchanged passive verification.
- **V2** — unchanged verifier-gated one-attempt recovery.
- **V3** — recovery-only causal control: same target refresh, recovery primitive, action limits and task scoring, but the recovery attempt is invoked by a preregistered schedule/phase checkpoint rather than by V1/V2 verifier or failure-classifier output.

### Comparator design rule

Because the existing shift and drop perturbations occur in different task phases, V3 may use separate preregistered phase schedules for the shift-family and drop-family attribution subprotocols. Those schedules must be fixed before new native seeds are observed, must not depend on the injected magnitude or runtime failure labels, and must also run on their corresponding normal controls. This makes V3 a causal control for **selective gating**, not a deployable recovery policy.

If engineering finds that a fair verifier-independent trigger cannot be constructed without leaking failure information or changing recovery opportunity, return to 02 before running native M5 rather than inventing a looser comparator.

### Frozen constraints

M5 must not change:

- nominal controller motions;
- V1/V2 verifier logic;
- V2 recovery primitive;
- simulator physics;
- task success tolerance;
- action budget/terminal semantics;
- disturbance definitions;
- reference scoring;
- audit pairing tolerances.

Any desired motion/precision improvement is a separate protocol with a new matched baseline.

### Evaluation

Use fresh, preselected seeds. Prefer a full matched magnitude curve if engineering cost remains modest; otherwise preregister representative normal/easy/medium/hard points before any native result is observed.

Required outputs include:

- final task success;
- unnecessary-recovery rate on normal/easy-success cases;
- V2 vs V3 paired success effect;
- retry action/path cost;
- regression rate;
- recovery-controller completion;
- final goal error;
- trigger timing;
- complete passive/causal trace audits.

### Interpretation table

- **V2 and V3 same final success, V2 lower cost/fewer unnecessary retries:** evidence that verification is valuable primarily as selective recovery gating.
- **V2 outperforms V3:** evidence that verifier-gated timing/information contributes to recovery effectiveness.
- **V3 matches V2 in both success and cost:** current task provides little evidence that explicit verification adds value beyond retry availability.
- **V3 outperforms V2:** current verifier/gating logic is likely constraining recovery and H3 must be weakened or redesigned.

## 6. Deferred, not forgotten

The following are intentionally deferred until after M5 attribution:

- motion/precision optimization;
- support placement/release;
- insertion;
- physically applied disturbances;
- camera/RGB-D verification;
- memory/experience learning;
- Prototype B/C/D;
- foundation models/world models.

The observed slow motion, high clearance and 1.11–1.34 cm recovered median goal error are important engineering findings, but changing motion now would confound M5. Precision pressure should be revisited when placement/release and insertion are introduced.

## 7. 02W decision

**Do not activate 02W for M5.**

The immediate causal question is bounded and the required control is clear enough for 06-01 engineering. A likely future 02W trigger is the non-privileged verification round, where a deeper comparison of visual/VLM/state-estimation verification approaches may materially affect experimental design.

## 8. Engineering routing

Return to **06-01 — AETHER-CL** for one new engineering round only:

> **M5 Verification-Gating Attribution**

06-01 must return to 02 after M5 evidence is frozen and audited. It must not automatically proceed to placement/release, insertion, perception, Prototype B/C/D or motion redesign.

PR #1 remains open/draft/unmerged unless separately reviewed and accepted. This 02 decision does not merge it.

## 9. Prototype A planned sequence after M5

Subject to evidence:

1. M5 — verification-gating causal attribution;
2. support placement/release task;
3. contact-rich insertion task;
4. physically propagated disturbance replication;
5. non-privileged verification replication;
6. final 02 Prototype A scientific review.

The order after M5 may change if evidence exposes a more important limitation. AETHER architecture remains evidence-driven.
