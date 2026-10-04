# AETHER CL Milestone 0 Environment Plan

Status: implementation prepared; A100 validation pending.

## Objective

Establish one reproducible simulator run, actual offscreen camera rendering,
browser viewing through SSH, and inspectable episode logs. This is infrastructure
validation for Prototype A, not a manipulation-policy result.

Prototype A's research question is whether explicit verification and bounded
recovery improve manipulation autonomy under disturbances with a fixed policy.
02 owns architecture evolution; 06-01 implements this scoped experiment.

## Hardware and deployment decision

Primary runtime is the available Ubuntu 22.04 server with four A100 80GB PCIe
GPUs. Long-term availability favors this server. The 4090 is a fallback only if
a concrete compatibility or capability test requires it.

Use a separate `aether-cl` Python 3.10 Conda environment and the implementation
directory `aura-sim/prototype_aether_cl/`. Run a single CPU physics environment
and explicitly select a GPU for offscreen raster rendering. Start the browser
viewer on loopback port 8765, with a matching local SSH tunnel. Port 8000 is
already used by LingBot. GPU availability and both local/server port availability
must be checked at launch; no GPU reservation is assumed.

The existing RoboTwin environment uses Python 3.10.22, PyTorch 2.4.1+cu121, and
SAPIEN 3.0.0b1. LingBot inference uses a separate Python 3.12.14 environment.
ManiSkill 3.0.1 requires stable SAPIEN on Linux, so its environment is independent.

Server network access is not dependable for GitHub/package retrieval. The
deployment route is GitHub to the connected laptop, then a Git bundle and
Linux CPython 3.10 wheels transferred over SSH. The repository transfer and an
offline `--copy` clone into `aether-cl` were confirmed by user-provided server
output. The clone retains PyTorch 2.4.1+cu121 and NumPy 1.26.4. Its initial
`pip check` reports SAPIEN's missing `opencv-python` distribution because only
the headless variant was present. The incremental offline installer resolves
the wheel set before replacing that variant in the copy. Simulator runtime and
camera acceptance are still pending; cloning an environment is not that evidence.

## Acceptance evidence

1. A command without camera capture completes bounded episodes and writes valid logs.
2. A rendering command produces a nonconstant RGB frame on the A100 server.
3. The browser shows actual changing simulation frames through a separate tunnel.
4. Logs record seeds, actions, observations, episode boundaries, runtime versions,
   code revision, errors, and termination/truncation conditions.

Server acceptance is pending until the commands are actually run. Random-action
task failure is expected and does not count as simulator failure. PickCube's
standard goal criterion does not require object release; a full placement
criterion must be defined before the policy baseline.

The local dependency resolution and logging/HTTP tests passed. An attempted
local CPU-physics run could not complete: this workspace has no available SAPIEN
rendering device, and PickCube constructs render materials even with camera
capture disabled. This does not validate or reject the A100 setup; actual
simulator execution remains a server acceptance check.

## Experimental controls to resolve before policy evaluation

- Define whether verification is passive or changes execution; passive
  verification alone should preserve baseline behavior.
- Fix policy weights, inputs, execution settings, and recovery/episode budgets.
- Distinguish observation-derived verification from privileged simulator checks.
  Evaluation success flags and injected disturbance labels are evaluator data,
  not automatic verifier/recovery inputs.
- Compare targeted recovery with a simple retry control under matched budgets.
- Treat the initial failure categories as symptoms unless causal diagnosis has
  independently validated evidence.

## Research boundary

Do not implement long-term memory, learned experience abstraction, embodiment
transfer, a full planner, world models, or foundation-model training here.
Episode logging preserves evidence for future work without introducing a memory
or learning intervention into this prototype.
