# AURA-Embodied Decision Log

This document records important project decisions, alternatives considered, and the reasoning behind them.

Research projects evolve. Decisions should remain traceable.

---

# DEC-0001

## Date

2026-10-04

## Topic

Interpret AETHER as an evolving capability-and-interface framework rather than a fixed linear pipeline.

## Context

The original AETHER representation used a sequential chain:

`Perception → World Understanding → Reasoning → Action → Verification → Failure Diagnosis → Recovery → Learning`.

After the first Embodied Intelligence Landscape study covering major systems including RT-1, RT-2, OpenVLA, π0/π0.5, GR00T, Gemini Robotics, and HomeBody, the project reached a more mature interpretation: embodied intelligence consists of interacting capabilities operating across different timescales, with recurrent feedback rather than a strictly one-directional pipeline.

The landscape also suggested increasing separation among semantic intelligence, physical intelligence, and embodiment-specific execution.

## Options Considered

1. Keep the original sequential AETHER pipeline as the assumed architecture.
2. Replace it immediately with a new fixed modular architecture.
3. Treat AETHER as an evolving capability/interface framework whose implementation choices remain research questions.

## Decision

Choose Option 3.

AETHER boxes represent capabilities and interfaces, not necessarily separate software modules or neural networks.

The framework should support concurrent and recurrent interaction, and architecture choices should be validated experimentally before becoming stronger project commitments.

## Reasoning

This avoids prematurely encoding assumptions such as:

- verification must happen only after action;
- failure diagnosis must be a standalone module;
- memory must be a separate subsystem;
- planning must always be explicit;
- one model cannot provide multiple capabilities;
- modularity is always superior to end-to-end learning.

Instead, AURA can compare explicit, latent, modular, unified, and hybrid implementations under controlled experiments.

## Future Re-evaluation Condition

Revisit this decision when experimental evidence supports a more specific architecture, or when a concrete AETHER prototype requires implementation-level interface commitments.

## Upstream Evidence

See `AURA-Embodied Intelligence Landscape v0.1` and the corresponding research history from branch 01.

---

# DEC-0002

## Date

2026-10-04

## Topic

Record AETHER Architecture Evolution v0.1 checkpoint.

## Context

Following deeper architecture exploration, AETHER evolved beyond a capability list into a broader research framework involving:

- multi-timescale feedback loops;
- state and uncertainty management;
- dependency-aware long-horizon intelligence;
- verification and hierarchical recovery;
- experience transformation;
- embodiment-aware transfer.

The checkpoint documents architectural evolution after comparing AETHER concepts against major embodied AI systems.

## Decision

Create `docs/research/architecture/aether/AETHER_Architecture_Evolution_v0.1.md` and associated Mermaid diagrams.

The checkpoint records:

- stable architectural principles;
- research hypotheses;
- open questions;
- experimental directions.

It does not define a final implementation architecture.

## Reasoning

The project should preserve architectural evolution rather than prematurely freezing a design.

Important conclusions:

- AETHER is a capability/interface framework, not a sequential pipeline.
- Physical intelligence requires interacting feedback loops across timescales.
- Long-horizon intelligence concerns relevant dependencies rather than unlimited context.
- Experience should become reusable capability rather than remain raw replay data.
- Embodiment should be treated as a variable with adaptation interfaces.

## Future Re-evaluation Condition

Revisit after experimental validation of candidate AETHER architectures, especially around:

- explicit versus latent state;
- memory mechanisms;
- verification and recovery systems;
- embodiment transfer.

---

# DEC-0003

## Date

2026-10-05

## Topic

Accept the first AETHER-CL engineering evidence within scope and require verification-gating attribution before broader Prototype A expansion.

## Context

06-01 completed M0–M4 of AETHER-CL on one privileged-state held-cube ManiSkill task. M4 audited 660 eligible trials and showed that V2 (passive verification plus one verifier-gated bounded recovery attempt) rescued 180 matched V1 failures with no observed final-task regressions. Passive V1 alone detected failures but deliberately did not alter behavior or task success.

The experiment did not include a blind/scheduled recovery comparator. Therefore the combined intervention is supported, but the necessity or causal value of explicit verification gating is unresolved.

## Options Considered

1. Treat M4 as sufficient to close Prototype A and advance to memory/state/embodiment work.
2. Broaden immediately to new tasks, perception or realistic disturbances without isolating the current causal ambiguity.
3. Run a verifier-independent recovery control first, then broaden Prototype A only after attribution is clearer.

## Decision

Choose Option 3.

The next 06-01 round is **M5 Verification-Gating Attribution**. Keep the current nominal controller and M4 scientific assumptions frozen. Add a preregistered recovery-only control using the same bounded recovery capability without verifier/failure-classifier gating.

Prototype A remains open. Broader closure still requires support placement/release, insertion, at least one physically propagated disturbance protocol, and at least one non-privileged verification protocol.

## Reasoning

The strongest current unresolved question is causal attribution. M4 demonstrates that adding a gated recovery pathway can rescue the tested failures, but it does not show that explicit verification is needed rather than simply granting a refreshed-target retry. Resolving that ambiguity before changing tasks, motion or perception preserves interpretability and prevents AETHER from attributing recovery success to the wrong architectural mechanism.

## Future Re-evaluation Condition

Return to 02 immediately after M5 audited evidence. Reassess H3 (verification-centered autonomy), H4 (recovery as intelligence), the remaining Prototype A closure sequence, and whether a 02W investigation is justified.

## Notes

See `docs/research/experiments/AETHER_CL_02_Research_Review_v0.1.md`. PR #1 remains draft/unmerged unless separately reviewed.

---


# DEC-0004

## Date

2026-10-06

## Topic

Accept M5 verification-gating attribution and advance Prototype A to support placement/release.

## Context

M5 compared verifier-gated V2 against a preregistered verifier-independent V3
using the same bounded recovery capability. Fresh seeds 80–99 produced 960
eligible isolated episodes, 345,600 actions and 1,160 strict comparisons.

V2 avoided all 60 unnecessary V3 attempts on baseline-success controls. On the
healthy drop-family control, scheduled V3 recovery destroyed a valid grasp and
failed 20/20 while V2 preserved nominal 20/20 success. In all 180 disturbed
cases requiring recovery, V2/V3 triggers aligned and their complete physical
traces, costs and outcomes were identical, with 177/180 final successes.

## Options Considered

1. Treat M5 as evidence that explicit verification universally improves
   recovery success.
2. Treat M5 as evidence only for selective intervention gating and proceed to
   the next Prototype A task-semantic closure dimension.
3. Stop Prototype A and activate memory/state/embodiment work.
4. Optimize the existing held-cube motion/precision before adding a new task.

## Decision

Choose Option 2.

M5 satisfies its causal-attribution objective. Update H3 so that verification's
demonstrated value is selective recovery invocation rather than universal
recovery necessity. Update H4 so that recovery benefit is conditional on
appropriate invocation. Record first bounded empirical support for H7's
adaptive capability-allocation idea.

The next authorized 06-01 round is **M6 Support Placement and Release** under a
new matched task-specific baseline. Success must require actual release and
stable support in the target region. Include a controlled placement-phase
failure family and one bounded verification-gated recovery opportunity.

V3 does not continue as a default system; it served the M5 attribution control.

## Reasoning

The current held-cube task does not yet test a completed placement state.
Support placement/release is the smallest next task-semantic extension that
meaningfully changes the desired physical state transition while preserving the
ability to isolate verification/recovery effects.

Insertion, physics-propagated disturbances and non-privileged verification
remain required before Prototype A scientific closure, but introducing them
simultaneously would confound the interpretation.

## Future Re-evaluation Condition

Return to 02 immediately after M6 audited evidence. Reassess whether the
closed-loop findings transfer to a released/stably-supported outcome and then
decide whether to proceed to contact-rich insertion or revise the sequence.

## Notes

See `docs/research/experiments/AETHER_CL_M5_02_Research_Review_v0.1.md`.
PR #1 remains draft/unmerged unless separately reviewed.

---


# DEC-0005

## Date

2026-10-06

## Topic

Accept negative M6 placement-recovery evidence and authorize an effect-aligned recovery-transition repair.

## Context

M6 validly extends Prototype A from held-cube target reaching to actual release
and stable table support. Baseline/V1/V2 all succeed on normal and small-shift
controls, but V2 rescues none of 62 failed placements.

All 62 V2 attempts successfully regrasp, lift and move the cube near the target,
then abort during the recovery lower phase before release. The object is already
within task-level horizontal tolerance and table-supported, while the recovery
controller still requires a dedicated 3 mm TCP vertical residual. The nominal
placement controller advances through this same semantic boundary by phase time
rather than the recovery arrival gate.

## Options Considered

1. Treat M6 as evidence that verification/recovery does not transfer to placement
   and proceed directly to insertion.
2. Relax the 3 mm threshold or increase lower duration using the observed M6
   residual range.
3. Run a narrow fresh-seed experiment replacing only the recovery lower-phase
   vertical gate with a task-relevant placement-ready state condition.
4. Abandon Prototype A and activate later memory/world-model/embodiment work.

## Decision

Choose Option 3.

Accept M6 as valid negative evidence and preserve the failed V2 unchanged.
Authorize **M6R Effect-Aligned Lower-to-Release Transition**.

V2R keeps the M6 motion/recovery capability fixed and changes only the lower
phase completion contract: retain the existing general distance, rotation,
minimum-step and attachment checks; replace the dedicated 3 mm vertical
residual requirement with controller-visible placement readiness
(`supported_geometry` plus the frozen horizontal task tolerance).

Evaluate Baseline, V1, frozen V2-old and V2R on fresh preselected seeds after
the repair is frozen. Already-observed M6 seeds may be used only for engineering
commissioning.

## Reasoning

M6 localizes the failure to a mismatch between an end-effector-space phase gate
and the task-relevant physical state. Simply tuning the 3 mm threshold to the
observed residuals would overfit the failed sample. Proceeding to insertion
would carry a known recovery-contract defect into a harder task.

The narrow V2-old/V2R comparison can test whether task-effect-aligned phase
completion is the missing interface while preserving all other recovery motion
and verification behavior.

## Future Re-evaluation Condition

Return to 02 immediately after M6R audited fresh-seed evidence. If V2R reaches
release and recovery succeeds, reassess readiness for insertion. If it fails,
use the newly localized downstream failure rather than post-hoc threshold tuning
to define the next decision.

## Notes

See `docs/research/experiments/AETHER_CL_M6_02_Research_Review_v0.1.md`.
PR #1 remains draft/unmerged unless separately accepted.

---

# Decision Template

## Decision ID

Example: DEC-0004

## Date

YYYY-MM-DD

## Topic


## Context

Why does this decision need to be made?

## Options Considered


## Decision


## Reasoning

Why was this direction selected?

## Future Re-evaluation Condition

When should this decision be reconsidered?

## Notes

