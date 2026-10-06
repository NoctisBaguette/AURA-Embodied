# AURA-Embodied Research Documentation

This directory stores stable research knowledge extracted from discussions, experiments, and decisions.

## Structure

- `intelligence_landscape.md`
  - VLM, VLA, world models, memory, planning, existing systems

- `manipulation.md`
  - manipulation intelligence, skills, policies, affordances

- `long_horizon.md`
  - task decomposition, memory, verification, recovery

- `architecture/`
  - AETHER architecture evolution

- `experiments/`
  - experiment reports and analysis

- `meetings/`
  - advisor/team discussion records when applicable

Documentation should be created when knowledge becomes stable enough to preserve.


## Current engineering handoff

[AETHER-CL v0.1: 06-01 return to 02](experiments/AETHER_CL_06_01_Return_to_02.md)
records completion of the current held-cube experiment, accepted results,
remaining original task scope and research decisions for the next round.


## Latest engineering return

[02 review and DEC-0003](experiments/AETHER_CL_02_Research_Review_v0.1.md)
authorize [M5 Verification-Gating Attribution](experiments/AETHER_CL_M5_Attribution.md)
in the existing 06-01 chat. M0–M4 closure is historical; Prototype A remains open.

M5 native execution and independent audit are complete. The
[M5 return to 02](experiments/AETHER_CL_M5_Return_to_02.md) records selective
invocation benefits, identical aligned recovery traces and retained large
disturbance failures. Prototype A remains open; further scope requires 02.

## Active engineering round

[02's M5 acceptance and DEC-0004](experiments/AETHER_CL_M5_02_Research_Review_v0.1.md)
authorize [M6 Support Placement and Release](experiments/AETHER_CL_M6_Placement.md)
only. M6 native execution and [independent audit](experiments/AETHER_CL_M6_Results.md)
are complete: all 360 trials and 340 comparisons pass evidence checks, but
all 62 V2 placement retries abort before release, with no rescues.
The [M6 return to 02](experiments/AETHER_CL_M6_Return_to_02.md) was
[accepted under DEC-0005](experiments/AETHER_CL_M6_02_Research_Review_v0.1.md).
[Fresh M6R native evidence](experiments/AETHER_CL_M6R_Results.md) is
[accepted by 02 under DEC-0006](experiments/AETHER_CL_M6R_02_Research_Review_v0.1.md):
70 paired rescues and no observed healthy regressions. The active round is
[M7 contact-rich insertion](experiments/AETHER_CL_M7_Inspection.md), beginning
with [installed PegInsertionSide selection and normal-six development commissioning](experiments/AETHER_CL_M7_Development.md). Earlier return documents remain historical checkpoints.
Prototype A stays open. Return to 02 after M7; physics-propagated disturbances,
non-privileged verification, memory/world models, B/C/D and 02W remain deferred.
