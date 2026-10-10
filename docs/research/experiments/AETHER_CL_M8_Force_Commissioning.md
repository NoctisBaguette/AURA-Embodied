# M8 development force-response commissioning

02's DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40` authorizes
physics-propagated placement disturbance using the accepted M6R task,
privileged verifier and one effect-aligned recovery episode. This engineering
batch establishes the disturbance mechanism before the matched Baseline/V1/V2
commissioning and fresh M8 freeze. It is a development-only Baseline batch;
neither fresh execution nor a final force family is available in this entry point.

## Independently reviewed installed inspection

The returned v2 archive is 119,282 bytes, SHA-256
`b0b0169d01ed0e8bdb898999d6ab08e82bf1f4a66466e59b6be0b91266063c80`.
Its file index, report and executed inspector bytes verify. The executed source
matches the clean native inspection revision
`6a375b2b05abd93c9cd90410dc60123ef8ee2d1c`. Eight accepted placement source
hashes, twelve embedded installed source hashes and inherited installed/asset
identities verify against the retained earlier installation. Native inspection
passed all eleven guard tests. The compact [inspection receipt](evidence/AETHER_CL_M8_Installed_Physics_Inspection.json)
retains these identities, binding docs, hook source and physical properties.

The cube is a 40 mm rigid box with mass `0.06400000303983688 kg`. Cube and table
static/dynamic friction are both `0.30000001192092896`; restitution is zero.
The CPU simulator runs at 100 Hz and the controller at 20 Hz, with five external
physics steps per control action. The actual native timestep is
`0.009999999776482582 s`. Source-verified gravity is `[0, 0, -9.81] m/s²` and is
checked on the actual environment during commissioning. The installed SAPIEN
binding explicitly supports `add_force_torque(force, torque, mode="force")`.
The empty task hooks run immediately before and after each actual engine step.

The retained-history scan checked 3,136 event files and 5,639 reset/controller
reset records, including 2,179 legacy controller records linked to the later
seeded reset in their same file/episode. Recorded evaluation/development seeds
cover 0–159; seeds100/101 are already observed. Fresh160–179 have no overlap in
this capture. Their availability must be checked again at a future frozen
fresh entry. The constructor's known initialization reset uses2022; the explicit
inspection reset used100. Inspection executed zero controller actions and zero
force commands, so it establishes interface/provenance rather than force response.

## Force input and timing

The adapter calls the cube body's engine binding with a world-frame horizontal
`[0, +F, 0]` force in newtons, zero world torque, and only `mode="force"`.
No application-point offset is supplied, so this is a net force without an
added torque. It repeats the force immediately before each of the five physics
steps of action296, the accepted nominal post-release retract boundary. The
nominal window is 50 ms; the recorded command integral uses the actual timestep.
No pose setter, velocity setter, impulse mode, acceleration mode or
velocity-change mode is called by the adapter. The force call's immediate
pose/velocity readings must remain identical to its pre-call readings; changes
must occur through the engine step. An unexpected immediate change is logged
and blocks further execution without a substitute mechanism.

At the fixed boundary, the previous observation must have nominal `retract`
phase, open/released geometry, designated-table support geometry, no built-in
grasp and an upward table contact force of at least the unchanged task's0.01 N
support threshold. A missed precondition applies no force and remains retained;
there is no retiming or scene replacement. Normal controls execute no force
API calls, including no zero-force calls that might wake the body.

The first six development candidates use measured mass and friction to estimate
Coulomb sliding. For duration T, coefficient μ, gravity g and post-pulse speed v,
the simple model is `d = v*T/2 + v²/(2*μ*g)`, giving
`F = m*(μ*g + v/T)` for nonzero doses. The estimated drift series comes from the
existing task's25 mm XY tolerance,40 mm cube and0.4 m workspace bound. This
model omits contact transitions and solver details; its distances are dose
identifiers and development estimates, never desired actor poses or guaranteed
physical displacement. The finite force inputs are encoded as float32.

| Candidate | Estimated drift only | Force +Y (N) | Planned command integral (N·s) |
| --- | ---: | ---: | ---: |
| normal | 0 mm | 0 | 0 |
| model-drift-010mm | 10 mm | 0.41868388652801514 | 0.02093419385848505 |
| model-drift-040mm | 40 mm | 0.7223591804504395 | 0.03611795821522268 |
| model-drift-080mm | 80 mm | 0.9775553345680237 | 0.04887776563589796 |
| model-drift-120mm | 120 mm | 1.1740388870239258 | 0.058701943039105586 |
| model-drift-200mm | 200 mm | 1.486150860786438 | 0.07430754137841888 |

This fixes only the development plan. Independent review of actual displacement,
velocity, support/contact behavior and failure onset will determine whether the
mechanism is reproducible and whether these or revised development doses form
a useful normal/easy/multiple-harder family. Final selection remains unfrozen.

## Unchanged runner and evidence

Each native episode uses the accepted `m6r_runtime.run` with its original Baseline
controller, task scorer, reset/observation adapters and800-action budget. A
dependency-injected environment proxy passes through the original action object
and wraps the inspected pre/post-physics hooks. It does not replace controller
motion or task semantics. The original goal-site Z projection is retained as
task setup; there is no cube-state disturbance write.

The imported M6R configuration uses `disturbance="none"` to disable its historical
synthetic relocation branch. This legacy field and the legacy episode's
`disturbance_applied` describe only that disabled synthetic injection. External
M8 force commands are explicitly represented by `m8_manifest.json`,
`physics.jsonl`, `physics_audit.json` and the primary `m8_result.json` field
`physical_force_applied`. A physical M8 pulse must never be reported as absent
just because the legacy synthetic field is false. Manifests identify this carrier
relationship explicitly. The full scientific matrix will use task-specific M8
condition bookkeeping after mechanism review.

All eligible episodes run the complete800 actions; accepted initial-in-goal
exclusions retain their zero-action outcome. Every imported action, decision,
reference endpoint, verifier/recovery state and terminal summary is reconstructed
with the accepted M6R auditor. Separately, each instrumented action records
five pre-physics, immediate-post-force and post-physics states: cube pose,
linear/angular velocity, designated table contact force and both finger contact
forces. It records requested and executed world force/torque, mode, timestep,
substep and fixed support precondition. The physical audit checks continuous
state, control/physics endpoint equality, exact input window and call count,
and absence of immediate pose/velocity overwrite. It derives actual application
duration, command integral, before/after pulse state, peak displacement/speed,
final drift and sampled support loss. These are mechanism diagnostics; final
success remains the accepted independent placement scorer.

## Fixed20 development batch

Each child uses a separate interpreter and native CPU environment. Only
seeds100/101 are allowed; source/native/package/asset identity and clean pinned
Git are checked before native construction and after every child.

| Group | Runs | Purpose |
| --- | ---: | --- |
| Original no-hook Baseline normal | 2 | Reference for possible recording effects |
| Six candidates × two seeds | 12 | Actual force response and unchanged task outcomes |
| Repeat normal/80 mm/200 mm estimates × two seeds | 6 | Exact same-seed native reproducibility |

Eighteen exact comparisons cover two full zero-force/no-hook pairs, ten full
pre-force prefixes through action295 and six full repeated physical traces.
Repeats also require identical complete physics-sidecar bytes. The batch's
`M8_FORCE_COMMISSION_VALID` marker means all development evidence/replay/pair
checks passed. It is not a performance threshold, a claim of successful recovery
or approval to run fresh seeds. Failed placements, misses, non-application and
initial-goal exclusions do not disappear because of this marker.

The parent writes each started slot before launching its child. A caught error
or600-second child timeout retains the started record, partial output and stdout.
The parent stops, indexes all retained files and creates the exclusive archive;
it does not replace or automatically rerun a slot. Existing study/archive paths
are refused. Source snapshots and the inspected receipt accompany the evidence.

## Native execution and return

Use the established offline Git-bundle transfer from the Windows laptop and
the newly supplied exact commissioning commit. Preserve both inspection bundles,
v1/v2 archives and logs. Activate the existing `aether-cl` environment with the
established GLVND path and `CUDA_VISIBLE_DEVICES=1`; no dependency update or
session-ID override is needed. Run the twelve new force tests from the prototype
and the eleven inspection guard tests from the repository root before starting.

From `aura-sim/prototype_aether_cl`, the batch command is:

```bash
python -u -m aether_cl.m8_force_commission \
  --expected-head EXACT_COMMISSIONING_COMMIT \
  --output runs/m8-force-commission-v1 \
  --archive /home/jiangle/aura-work/aether-cl-m8-force-commission-v1.tar.gz
```

The supplied deployment block runs it under `nohup` with a separate log so an
SSH disconnect does not stop the parent. `suite.json` records running/finished
state and started/completed slots. The parent log prints `START`/`END` for each
slot and the final archive SHA. Return the archive and log, including an error
archive, for independent review before further engineering/freezing. Do not
start another native experiment concurrently or fetch GitHub from the server.

Twelve focused force/evidence tests and eleven inspection tests pass locally;
the force tests include a simulated timeout and a tampered physical record,
without invoking native physics. Python3.10 syntax and CLI help checks pass.
Native force-response evidence remains pending until this fixed20 batch returns.

After physical-mechanism review, commission the matched Baseline/V1/V2 systems
using accepted M6R V2R behavior. Freeze force family and complete protocol before
fresh native outcomes; recheck retained history for160–179. Preserve one bounded
recovery episode and all denominators. If supported force behavior is unusable,
return to02 before redesigning the environment or substituting a disturbance.
After frozen native M8 evidence and independent audit, return to02. No training,
RGB/RGB-D verification, memory/world models, Prototype B/C/D, foundation-model
integration or02W is part of this batch. Actual arm/camera rendering remains
deferred by the user.
