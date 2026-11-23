# M8 physics-propagated placement preregistration

Date: 2026-10-08 UTC. Frozen before any fresh native M8 outcome.
Authority: 02's DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40`.
Scope: physics-propagated disturbance of the accepted M6R released-support
placement task only. Research question: does the privileged-state AETHER-CL
verification/recovery pattern retain useful recovery behavior when a controlled
disturbance changes object motion through physics and contact rather than a
synthetic state relocation?

The [machine protocol](evidence/AETHER_CL_M8_Placement_Protocol.json), SHA-256
`3e67b43747b4d52b73b39c64d2b1f159a855f91cde012b8a5ceffbaf6c40a031`, is the
executable contract. Entry reconstructs that JSON from the exact current source
and receipt bytes and rejects any difference. Measurement Git head is supplied
explicitly and must be clean. The native Python, packages, installed simulator
source/binaries, assets, hardware driver and library environment must match the
independently reviewed 36-run commissioning identity; only the newly published
wrapper revision differs. Historical accepted and commissioning source files
remain byte-for-byte unchanged. The [matched development review](AETHER_CL_M8_Matched_Commission_Review_v1.md)
and its original retained archive are prerequisites, replayed again before any
fresh reset.

## Task and systems

Use installed ManiSkill 3.0.1 PickCube-v1, Panda, unrendered CPU physics, one
environment, state_dict observations and pd_ee_pose commands. Native physics
runs at 100 Hz, five substeps per 20 Hz action. Budgets are 800 total actions and
one recovery episode of at most 400 actions. There is no model training.

Baseline is the unchanged FixedPlacement controller. V1 uses that identical
controller with passive PlacementVerifier. V2 adds the accepted
EffectAlignedRecovery (legacy V2R); it retains the accepted invocation rule,
phase progression, bounded retry and physical-effect-aligned lower completion
gate. No V2-old, additional system, second recovery or motion primitive is
introduced. The accepted m6r_runtime.run remains the sole motor-command
authority. Independent instrumentation reconstructs the current controller
phase, checks exact action equality before native stepping and logs complete
decisions/verdicts/recovery states for independent audit.

Independent success retains valid prior acquisition/lift, release/open gripper
with no grasp, designated table support with geometry/contact agreement,
object-target XY error at most25 mm, TCP retraction at least 80 mm, and five
stable observations under the frozen velocity bounds. Built-in environment
success is retained only. Controller completion is reported separately from
physical task success. The unchanged initial-at-goal exclusion is the only
eligibility exclusion; it stays in the requested denominator and receives no
replacement. All other initial failures, missed disturbance preconditions,
failed attempts and later failures remain outcomes.

## Frozen force family

| Point identifier | World +Y force (N) |
| --- | --- |
| normal | 0 |
| force-easy-v1 | 0.41868388652801514 |
| force-probe-1 | 1.857688546180725 |
| force-probe-2 | 2.322110652923584 |
| force-probe-3 | 2.9026384353637695 |
| force-probe-4 | 3.628298044204712 |

These are exactly the six inputs evaluated in matched development. Normal/easy
controls and all four geometric probes are retained, including probe2's
nonmonotonic healthy development case. Labels designate commanded inputs, not
displacement targets. No force is retuned using fresh outcomes.

At action 296, after computing the accepted action, apply world[0,F,0] N with
zero torque in mode="force" using the inspected rigid-body add_force_torque
binding before each of five native physics advances. Actual timestep is
0.009999999776482582 s; nominal pulse duration is 50 ms. Cube mass, friction,
support, installed physics hooks and environment initialization are unchanged.
The gate requires the active controller phase to be nominal retract, released
and supported geometry, no grasp, and designated table contact Z force at
least 0.01 N. Early recovery cannot be mistaken for nominal retract. If the gate
fails, record non-application at this fixed boundary; do not retime the pulse or
replace the scene. No cube pose/velocity overwrite, kinematic pusher or
controller-aware adaptive force is used.

Log every before-force, immediately-after-call and after-physics state,
including cube pose/velocities and table/finger contact forces. Independent
audit verifies fixed timing/vector/duration, complete five-substep sampling,
no immediate state overwrite, physical continuity and native endpoint
agreement. Input and measured effect remain separate. Commissioned
physical_effects span the entire post-pulse episode and can include recovery;
new read-only diagnostics separately report pulse displacement/delta-velocity
and peak displacement/speed/support loss through the action before the first
recovery action, or through episode end if no retry starts. Neither diagnostic
enters the controller or scorer.

## Fresh matrix and review boundary

Preselect reset seeds 160–179. Reuse the pinned retained-history parser, including
failed/stopped and legacy controller reset records, immediately before fresh
construction. Require all 20 selected seeds unused outside this study. The
constructor initialization reset 2022 is separately identified by installed
inspection. Missing/malformed history or any selected overlap blocks entry;
the parser's suggested next range is never adopted automatically.

The fixed matrix is 20 scenes × six forces × three systems = 360 requested
episodes, 18 cells with 20 episodes per cell. Each slot has a fresh interpreter
and environment. The analysis unit is the 20 common scenes: 360 episodes and
multiple rescues across conditions are not 360 independent samples. Report
per-force matched success counts/rates and V2-minus-Baseline differences, with
requested and eligible denominators explicit; keep the same scene pairing
across the curve. No significance claim or global architectural conclusion is
preregistered from this bounded setting.

Execute first 18 on normal/easy/probe2 × seeds 160/161 × Baseline/V1/V2 in that
point/seed/system order. Pause and archive for independent integrity review.
This gate requires complete replay, identity, fixed force provenance and the
16 exact pilot comparisons (six passive, six recovery, four pre-force). It
contains no success-rate, healthy-case, difficulty or V2-rescue performance
criterion. Those 18 outcomes remain in the final matrix. No outcome-based
exclusion, family retuning, seed replacement or controller repair occurs after
fresh execution. An evidence-integrity failure stops and returns for review;
task failure alone never blocks commissioning validity.

After independent pilot review, resume exactly 342 unstarted slots in
point/seed/system order, skipping only the already completed pilot slots. The
resume command requires the independently reviewed pilot SHA-256. Verify all
pilot raw bytes and snapshots against the immutable archive, full 18 replays,
original gate/summary, exact current source/protocol/native identity,
non-volatile environment and paths before omitting this study's own validated
history. SSH/session-only variables, including XDG_SESSION_ID, are explicitly
normalized; no old session ID is spoofed. External selected-seed use still
blocks resume. Failed, interrupted or pending-child checkpoints cannot resume.

Pending slots are atomically recorded before launching a child. The child
requires its live parent's selected slot and identity before environment
construction. Each child is limited to 600 wall-clock seconds; timeout or
termination stops the child process group and retains partial evidence. No
rerun, fallback or adaptive replacement occurs. Archives use exclusive new
paths; errors retain indexed evidence. Before the final archive, revalidate the
unchanged first 18 raw evidence and original archive digest.

## Audit and measures

Final integrity requires 360 accepted-runner/physics/controller-gate replays and
340 exact comparisons: 120 full passive pairs, 120 recovery common-prefix/full
healthy pairs, 100 pre-force Baseline controls. Only the commissioned physical
auditor's development-seed membership predicate changes to the frozen selected
fresh-seed predicate; every physical check, action tolerance 3e-7 and exact pair
requirement remains intact. Failure at these checks retains evidence.

Retain final task, release, support stability and retraction success; final
horizontal error; reference/verifier first failure, diagnosis, onset latency,
agreement counts/confusion and precision/recall; recovery invocation/attempts,
successful recovery episodes, strict matched rescues, unnecessary attempts,
final regressions, phase progress, lower transition/release/retraction events,
recovery action cost and observed TCP travel. Added travel is V2 minus V1 for
each matched pair, including zero-attempt and failed cases. Successful recovery
episodes are distinct from counterfactual rescues and unnecessary retries.
Record controller completion separately, pulse commands/calls/integral,
physical response and missed force preconditions. Preserve raw endpoint and
100 Hz substep evidence, originals, snapshots, all-outcome cell/pair summaries
and cells.csv. A partial pilot has no completed 20-scene cell success rate; those
rates remain null until the complete matrix, without treating 2/20 as a result.

Validation before native entry: 15 frozen scheduling/checkpoint/replay fixtures
in Python 3.10 with NumPy 1.26.4/SciPy 1.10.1, including 800-action accepted fresh
seed fixtures, tampered raw/parent metadata, exact pairing, full 18+342
scheduling, immutable archive retention, history/identity/source guards,
zero-action/excluded denominators, interruption/timeout handling and pulse
versus intervention diagnostics. Fixture endpoint perturbations are testing
mechanics, not native force-response evidence. The original 36 native episodes
also pass the new prerequisite validation unchanged.

After complete frozen native M8 evidence and independent audit, return to 02
before any further scope. Non-privileged RGB/RGB-D verification, memory/world
models, Prototype B/C/D, foundation-model integration, rendering and 02W remain
deferred. Prototype A remains open and PR #1 stays draft, open and unmerged.
