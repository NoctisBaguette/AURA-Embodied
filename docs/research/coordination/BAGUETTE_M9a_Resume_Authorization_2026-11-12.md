# BAGUETTE Core — M9a Commissioning Resume Authorization

Date: 2026-11-12 (Asia/Shanghai)

Status: **AUTHORIZED TO RESUME EXISTING M9a COMMISSIONING SCOPE**

## Basis

BAGUETTE Core reviewed:

- current AURA `main` through 2026-11-12;
- experiment branch `06-01/aether-cl-m0`, still at
  `cd8185dbe36676c1edd90031e13a105795b617d5`;
- October 29 Frontier Watch / HQ-Core handoff;
- November 5 Frontier Watch / current radar;
- existing M9a commissioning-start and camera-I/O commissioning records.

Both recent Frontier Watch checkpoints explicitly recommend **continuing the
already-authorized M9a Vulkan/rendering/camera/sensor-I/O commissioning**, while
making no change to the scientific scope.

The user/operator has now explicitly indicated that the pause should be lifted
and the existing experiment should continue.

## Core decision

**Resume 06-01 M9a commissioning now.**

This authorization covers only the previously approved commissioning and
reporting-repair path needed to establish a trustworthy non-privileged sensor
interface.

It does **not** authorize fresh M9a scientific evaluation yet.

## Authorized immediate work

06-01 may:

1. inspect and resolve the current Vulkan/rendering prerequisite;
2. complete the retained reporting-only continuation/repair path;
3. run the already-defined known-scene camera-I/O commissioning cases;
4. establish actual simulator camera output;
5. establish browser access through the documented SSH tunnel;
6. save real renderer MP4 plus lossless RGB/depth/validity packets;
7. verify exact rendered-vs-unrendered action/physics/controller neutrality;
8. measure capture/stream/record latency, drops, throughput, storage and resource
   cost;
9. evaluate camera observability/calibration/uncertainty needed for the candidate
   sensor verifier;
10. prepare the complete executable M9a fresh-evaluation protocol and return it
    to BAGUETTE Core.

## Still forbidden without a new Core gate

Do not:

- spend fresh M9a evaluation seeds;
- change the accepted M8 task, force family, controller, recovery, scorer,
  thresholds, phase deadlines or 800-action budget;
- add evidence-freshness/state-invalidation mechanisms to M9a;
- add continue/reobserve/recover intervention arms;
- add transfer evaluation;
- replace the fixed executor with FastVLA/VLA/WAM or another learned policy;
- add memory/world-model systems;
- silently rerun, replace or discard retained failed commissioning attempts.

## Frontier Watch handling

The 2026-10-29 and 2026-11-05 watches both say **continue existing M9a scope**
and nominate zero new experiments.

The next Frontier Watch may update prior-art interpretation. It does not
automatically invalidate this commissioning authorization unless it uncovers a
material safety, scientific-validity or scope conflict requiring Core review.

Current post-M9a candidate remains evidence freshness / task-state invalidation,
with intervention-value evaluation and explicit migration/transfer as competing
later questions.

## Required return to Core

Before fresh M9a native evaluation, 06-01 must return:

- latest exact branch head;
- native rendering/Vulkan status;
- retained commissioning/repair evidence;
- actual-camera live-view evidence;
- MP4/raw sensor evidence;
- neutrality audit;
- latency/drop/storage/resource measurements;
- observability/calibration/uncertainty findings;
- proposed final M9a protocol;
- fresh-seed allocation/history guard;
- explicit statement of any unresolved blocker.

Core will then decide whether to freeze and authorize fresh M9a evaluation.
