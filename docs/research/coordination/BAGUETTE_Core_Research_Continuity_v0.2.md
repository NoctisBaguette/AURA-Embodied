# BAGUETTE Core Research Continuity v0.2

Date: 2026-10-19  
Status: **current routing checkpoint**  
Public identity: **AURA-Embodied / AURA**  
Historical experiment codename: **AETHER / AETHER-CL**  
Provisional internal Core codename: **BAGUETTE**

## 1. What changed since v0.1

The old v0.1 checkpoint said the next move was a 02W investigation before M9.
That is now stale.

The experiment branch records that the user returned a 02W M9 decision package
and explicitly moved the project onto M9a. Engineering has since started only
the package's narrow commissioning/preregistration work. No fresh M9a scientific
evaluation has been accepted or completed.

Current experiment branch:
`06-01/aether-cl-m0`

Current inspected branch head:
`cd8185dbe36676c1edd90031e13a105795b617d5`

Important current records:

- `docs/research/experiments/AURA_M9a_Commissioning_Start_v0.1.md`
- `docs/research/experiments/AURA_M9a_Camera_IO_Commissioning_v0.1.md`
- `AGENTS.md`
- `tools/m9_vulkan_diagnostic.py`

## 2. Current route

```text
BAGUETTE Core
    ↓
02W M9 design package (already returned)
    ↓
06-01 M9a commissioning / preregistration  ← CURRENT
    ↓
camera/render/sensor I/O neutrality + commissioning evidence
    ↓
return to BAGUETTE Core
    ↓
Core accepts/freezes executable fresh-evaluation protocol
    ↓
06-01 fresh M9a native evaluation
    ↓
return to Core
```

Therefore:

**Do not create another 02W for the same M9a design question now.**

**Do not start a new experiment family now.**

Resume the existing 06-01 M9a commissioning scope, subject to the current
operator's explicit decision to continue.

## 3. What M9a is isolating

M9a keeps the accepted M8 released-placement task, force family, executor,
recovery, scorer, phase limits and action budget fixed while replacing the
verification information boundary with non-privileged sensing.

The proposed sensor-verifier boundary allows only:

- RGB;
- depth + validity;
- measured robot/proprioceptive state;
- calibration/static priors;
- declared task target;
- permitted command/task context;
- timestamps.

It excludes privileged simulator masks/truth, object ground-truth state,
contact/grasp flags, environment success/reward, evaluator/reference output,
disturbance/force labels, seed-identifying information, cached recovery geometry
and recovery completion.

The executor itself remains privileged in M9a. M9a is a verifier-boundary study,
not a fully sensor-driven manipulation system.

## 4. Current engineering state

Source-only sensor inspection completed and retained evidence for:

- installed camera/render interfaces;
- retained seed history;
- software/package identities;
- GPU/storage capacity;
- available MP4 tooling.

Camera I/O commissioning has been prepared around five known-scene modes:

1. unrendered;
2. render idle;
3. capture only;
4. record without live view;
5. record with live view.

The commissioning contract requires exact action/physics equality against the
unrendered accepted controller. Actual simulator camera output, raw RGB/depth,
MP4 and local-browser viewing must not perturb scientific execution.

Two reporting/integration defects were retained rather than hidden:

- NumPy boolean JSON serialization after the first completed unrendered slot;
- wrong terminal-summary field name in the reporting continuation.

Corrections are reporting-only and preserve the original completed native
episode. No camera-neutrality claim follows until the continuation finishes and
is independently reviewed.

The latest branch also adds a read-only Vulkan inventory because native rendering
prerequisites still require diagnosis. This is diagnostic preparation, not proof
that camera rendering or M9a has passed.

## 5. Immediate next engineering objective

Return to **06-01** and finish the already-authorized M9a commissioning/repair
path.

The next useful evidence should establish, in order:

1. current native rendering/Vulkan prerequisite status;
2. actual simulator camera output from the retained/authorized commissioning
   setup;
3. local-browser tunnel access;
4. saved MP4 and lossless RGB/depth/validity packets;
5. exact neutrality versus the accepted unrendered control;
6. measured capture/stream/record latency, drops, storage and resource cost;
7. observability/calibration/uncertainty measurements needed for the candidate
   sensor verifier;
8. an executable M9a protocol returned to Core before fresh evaluation.

Do not spend fresh evaluation seeds merely to debug rendering, recording or
reporting.

## 6. Frontier Watch integration through 2026-10-19

05's current radar explicitly says **do not reset M9a development**.

New high-value themes are:

### Evidence freshness / state invalidation

REMM, TacitVLA and task-context caching work strengthen the question:

> Which task beliefs must remain fresh, and what evidence invalidates them?

Frontier Watch currently proposes this as the strongest **next** research
candidate after the sensing baseline is accepted.

It should not be inserted into M9a's frozen scientific scope.

### Intervention value

RESCUE/ForkCast-like work suggests comparing the cost/value of:

- continue;
- observe/reobserve;
- intervene/recover.

This remains an alternative next experiment after M9a, not an extra M9a arm.

### Efficient learned-policy baselines

Two distinct FastVLA directions are now reproduction-feasibility candidates.
They should be evaluated in isolated environments and must not replace the
current fixed executor during M9a.

### Action-aware retrieval / reusable experience

Robota-Embed and related work remain conceptually relevant, but implementation
should wait for a suitable episode corpus/interface and a later memory/experience
research scope.

## 7. Next research checkpoint after sensing baseline

If M9a's non-privileged sensing baseline is accepted, Core should normally choose
**one** next discriminating question rather than starting many branches.

Current Frontier Watch ordering:

1. evidence freshness / task-state invalidation — strongest current proposal;
2. intervention-value / continue-vs-observe-vs-recover comparison — strong
   alternative;
3. explicit transfer experiment — still central to AURA and must not be
   forgotten;
4. learned-policy baseline feasibility — engineering/reproduction support, not
   necessarily the immediate architecture experiment;
5. memory/retrieval/world-model expansions — deferred until a narrower question
   justifies them.

This ordering is a proposal, not a new architecture decision.

## 8. Stable architecture constraints

Current AURA/BAGUETTE architecture remains:

- task-relevant physical state transition as the common analysis abstraction;
- planning feasibility distinguished from execution reliability;
- planning and verification should use compatible transition semantics;
- verification is selective, temporal and uncertainty-aware;
- local recovery has a bounded corrective envelope;
- minimum-change / dependency-aware recovery remains a hypothesis beyond the
  lower-level evidence already obtained;
- migration is central, but M0-M8 are not formal transfer evidence;
- RGB and RGB-D are collaborative sensing sources;
- AURA is the public identity; BAGUETTE remains provisional internal naming.

## 9. Branch/history warning

`main` and `06-01/aether-cl-m0` remain diverged.

Do not issue conflicting global DEC numbers or rewrite experiment history while
M9a commissioning is active.

Main contains the current architecture/frontier/coordination memory.
The experiment branch contains the authoritative M0-M8 evidence and newer M9a
engineering records.

Reconcile histories deliberately after a stable M9a/Core checkpoint.

## 10. Successor-chat startup order

For a future BAGUETTE Core rollover, read:

1. this file;
2. `ARCHITECTURE.md`;
3. `docs/research/architecture/aura/AURA_State_Transition_Architecture_v0.2.md`;
4. `docs/research/frontier_watch/CURRENT.md`;
5. latest dated Frontier Watch issue;
6. M9a commissioning records on `06-01/aether-cl-m0`;
7. latest experiment return / Core acceptance;
8. relevant decision logs.

Do not reconstruct current routing from old chat text when GitHub records are
newer.
