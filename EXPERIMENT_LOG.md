# AURA-Embodied Experiment Log

This document records reproductions, implementations, modifications, evaluations, and experimental findings.

Experiments should preserve not only results, but also reasoning and failure analysis.

---

# EXP-0001 Preparation

Date: 2026-10-04

AETHER-CL Prototype A asks whether explicit verification and bounded recovery
improve manipulation autonomy under disturbances with a fixed policy.

Milestone 0 prepares an isolated simulator environment, finite random-action
smoke tests, episode logging, and a browser viewer for the A100 server. This is
infrastructure preparation; it does not yet produce manipulation-policy or
verification/recovery results. Initial server validation is recorded below.

See [the milestone plan](docs/research/experiments/AETHER_CL_M0_Environment_Plan.md)
and [implementation instructions](aura-sim/prototype_aether_cl/README.md).

Deployment update (2026-10-05, project timezone): direct server retrieval was
replaced by laptop downloads and SSH transfer. User-provided output confirms the
repository arrived via Git bundle and `aether-cl` was copied offline from
`robotwin-sim`. The copied package inventory guides an incremental Linux/Python
3.10 wheel set; it does not establish successful simulator execution. Installation,
native imports, physics, and rendering remained server acceptance steps at that point.

## Server rendering and browser evidence

Date: 2026-10-05 (Asia/Shanghai; run timestamps use UTC).

User-provided output confirms successful offline installation and `pip check`,
Python 3.10.22, PyTorch 2.4.1+cu121, OpenCV 4.11.0, CUDA availability, and successful
SAPIEN/ManiSkill imports. The rendering smoke at
`runs/glvnd-smoke/20261004T215207Z-667f7f38` completed five steps with
`state: finished`. The implementation validates and saves a nonconstant RGB
frame during this path. Its task success flag was false, as expected for random
actions; this is not a manipulation-policy success-rate measurement.

Three browser screenshots show changing Panda poses and counters at episodes
1/2/3, steps 68/49/12, through loopback port 8765. The displayed run directory is
`runs/live-viewer/20261004T220709Z-55ffe904`. This establishes basic CPU physics,
GPU camera capture, browser display, and SSH forwarding on the A100 server.
The live run's final result and raw log artifacts have not been retrieved for
independent inspection. A separate camera-disabled run has not been confirmed.

Native-library issue: standard OpenCV initially failed with
`libGL.so.1: undefined symbol: _glapi_tls_Current`. Removing library environment
variables and preloading system Mesa glapi did not help. A private extracted set
of Ubuntu Jammy `libgl1`, `libglx0`, and `libglvnd0`, all version `1.4.0-1` for
amd64, resolved imports and the rendering smoke when its library directory was
selected through process-scoped `LD_LIBRARY_PATH`. No system driver replacement
was needed. This is evidence of a successful workaround, not a complete audit of
the server's system graphics installation. SAPIEN's builtin Vulkan fallback and
PyTorch's all-device RNG warning remained nonfatal; the latter does initialize
CUDA contexts on all visible devices and merits isolation before larger runs.

Scene interpretation, checked against the installed ManiSkill 3.0.1 wheel:
the red cube is the manipulated object; the green sphere is a noncolliding goal
marker. Its position is sampled on episode reset, including a height above the
table. It is fixed within each episode. Camera projection can overlap it with
the arm. PickCube success requires cube-to-goal distance at most 0.025 m and a
static robot, and does not require release onto a support surface.

Next: implement and freeze a fixed task controller before testing verification
or recovery. The current runtime samples actions randomly and has none of these
components. Define actual placement/release criteria separately from this
initial PickCube infrastructure task.

---

# Experiment Template

## Experiment ID

Example: EXP-0001

## Date

YYYY-MM-DD

## Research Question

What are we trying to understand?

## Hypothesis

What do we expect?

## Background

Existing system, paper, or baseline.

## Method

Implementation and experimental approach.

## Environment

Hardware:

Software:

Dataset:

Simulation:

## Baseline

What are we comparing against?

## Metrics

How is success measured?

## Results

## Failure Analysis

What failed?
Why did it fail?

## Lessons Learned

## Next Direction
