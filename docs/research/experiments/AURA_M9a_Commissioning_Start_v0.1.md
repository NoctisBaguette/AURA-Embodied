# AURA M9a commissioning start

Date: 2026-10-10, Asia/Shanghai.

M9a studies sensor-based verification on the accepted M8 released-placement
task. The first engineering step is a source-only inspection of the installed
camera/depth interface, retained reset history and available storage/tooling.
It constructs no simulator, resets no scene and executes no controller action.

The user returned the 02W M9 decision package with the instruction that the
project is now onto M9. Engineering interprets that handoff as authorization
for the package's narrow commissioning/preregistration scope. This does not
authorize the proposed fresh evaluation or imply that its numerical protocol
has already been accepted by Core.

Decision-package source SHA-256:
`8f0c53429aa738324cce6b9ce9adbb1131d0700174294ac87f75827fe611536b`.
The unchanged uploaded DOCX remains the source; this note does not replace the
02W package or create a Core acceptance record.

## Reconciled repository identities

- Current main and package architecture head:
  `285943968977361f118473cceded55c72a5a5423`.
- Current experiment and package accepted head:
  `e7664349af37001c043ff7891e4c1cdd214df1c2`.
- M8 frozen native measurement:
  `e8184217dc4b3c205666787441b87b13ba8a489c`.
- M8 evidence publication:
  `4a6396a8ef8fc33fb543f37638f0ba7a81a784ea`.

There were no intervening changes at either live head when this handoff was
read. Both branch histories remain separate. No global DEC ID is added. Public
naming uses AURA; historical AETHER-CL paths remain unchanged.

Engineering read the current main architecture, roadmap, AURA state-transition
v0.2 checkpoint and BAGUETTE Core continuity protocol. The accepted M8 review,
live-view requirement, placement protocol and preserved executor/verifier
sources supply the experiment boundary.

## What changes and what stays frozen

The sensor verifier will receive only allowlisted RGB, depth/validity, measured
robot state, calibration/static priors, declared task target, permitted command
context and timestamps. It must not receive simulator masks, object truth,
contact/grasp flags, reward/success, evaluator output, force or condition labels,
seed-identifying paths, cached recovery geometry or recovery completion.

FixedPlacement, EffectAlignedRecovery, independent scoring, the original force
family, CPU 100 Hz physics, 20 Hz control, phase deadlines, 800 actions and the
single recovery episode remain frozen. This isolates a non-privileged verifier
around a still-privileged executor; it is not a fully sensor-driven system.

S0 uses the legacy three-observation failure and five-observation success rules.
ST differs only by requiring five failure observations. Per-effect outcomes
are true/false/unknown; not-yet-due is pending. Missing/stale evidence does not
become a failure at the terminal boundary. Unknown requests no new recovery and
does not change the accepted executor.

The exact sensor configuration, uncertainty bounds, deadlines and delivery
schedule remain commissioning candidates. No threshold is relaxed to accommodate
sensor error. No learned policy, memory/world model, force regulation, transfer
evaluation or new recovery behavior is included.

## First source-only inspection

`tools/m9_sensor_inspection.py` verifies the clean requested checkout and all
frozen source/evidence hashes from the M8 protocol. It reuses the preserved
history reader without importing the simulator. It reports collisions in the
proposed calibration seeds 180–199 and evaluation seeds 200–239; it never
selects replacement seeds or freezes an allocation.

It reads installed ManiSkill 3.0.1 camera/sensor/render/FK source, the pinned
Panda URDF, SAPIEN binding source, package versions, GPU inventory, ffmpeg
availability and free storage. Source bytes and failed inspections are retained
in an indexed archive outside the checkout. The installed-camera API is reviewed
before creating a separately versioned camera adapter.

This probe does not show a live camera, record a native video, measure estimator
accuracy or authorize reset/rollout. Its ready marker means source evidence is
available, not that the camera or verifier passed commissioning.

## Camera and evaluation gates

The next camera commissioning step must supply actual robot/object renderer
output at a working local browser URL through an SSH tunnel, and save actual
camera MP4 plus lossless replayable RGB/depth/validity and frame timing.

Before a protocol freeze, measure rendering, capture, recording and streaming
neutrality using the existing action/physics equality rules on known development
scenes. Measure observability, geometric/motion uncertainty, stale/unknown
behavior, one-tick delivery feasibility, latency distributions, frame drops,
compression, storage throughput and resource use. Rendering must not silently
change the experiment's physical behavior.

The package proposes 40 scenes × six M8 force conditions × six arms: B, P
passive, P active, S passive, S0 active and ST active. The proposed 36-slot
integrity pilot is retained in the eventual 1,440-episode denominator. These
counts and seed allocations are not frozen by this engineering start.

At 640×480, RGB8 + depth16 + complementary RGB8 requires 2,457,600 bytes per
observation set before validity. A byte-per-pixel validity mask increases this
to 2,764,800 bytes, 55,296,000 bytes/s at 20 Hz, and 3,185,049,600,000 bytes over
1,440 × 800 observations before compression. Reset frames, development and
calibration, metadata, MP4 and archive copies add further storage. These are
arithmetic estimates, not measured throughput or a chosen final archive format.

Return to Core with measured commissioning evidence and the complete executable
protocol before any fresh evaluation. M9b and physical deployment need separate
decisions. The package's retained-rescue/selectivity/coverage criteria are
proposals awaiting that freeze.

## Connection continuity

```text
ssh -p 2221 jiangle@166.111.59.11
scp -P 2221
Repository: /home/jiangle/aura-work/AURA-Embodied-offline
Prototype: aura-sim/prototype_aether_cl
Conda: /home/jiangle/miniconda3, environment aether-cl
```

Use offline Git-bundle transfer when GitHub access on the native server is
unavailable. Keep the existing environment and library settings. The actual
camera-service port will be reported by its adapter; no viewer port is invented
by this source-only step.
