# M7 — Contact-rich insertion preregistration

Date: 2026-10-07 (Asia/Shanghai). Authority: DEC-0006 and
[02's M6R acceptance](AETHER_CL_M6R_02_Research_Review_v0.1.md) at
`145aadce249b23a49ecb899ff273e93f673dd03b`.

This protocol is frozen before any fresh-native M7 outcome. The research
question is whether explicit verification and one bounded recovery generalize
from released placement to insertion scored from the object-target relation.
No learning or model training occurs. The systems use fixed controller code.
Return to 02 after the completed frozen native evidence and independent audit.

## Commissioning evidence and design selection

Installed ManiSkill3.0.1 `PegInsertionSide-v1` provides a rigid square peg,
four-wall channel and one `panda_wristcam` arm. Peg half-length varies from85
to125mm and half-width from15 to25mm. Hole half-width exceeds peg half-width
by approximately3mm. Native CPU physics uses100Hz external steps and20Hz
control, with five samples per action. State observations are privileged;
cameras/rendering, force disturbances and custom assets are out of scope.
The installed sources, Panda URDF and simulation settings remain unchanged.

The [known-seed commissioning audit](evidence/AETHER_CL_M7_Candidates_v5_Review.json)
checks archive SHA-256
`21b58777ce05db80edd35c24457f7778dd2edbacfab729adb94005c7ff4f3f68`, all191
indexed files, eight execution-source Git blobs and child source/software/
startup identities. All43,200 actions and216,000 external physics samples
replay with zero action error, with independent physical endpoint scoring.
All34 strict physical/action/reference/sample comparisons pass. Producer
commit is `fff75c25f2b5d1dc01a224be86a4cb60b1152afb`.

| Nominal offset | Baseline | V1 | V2 | V2 recovery attempts |
| --- | --- | --- | --- | --- |
| 0 mm | 2/2 | 2/2 | 2/2 | 0 |
| 1.5 mm | 2/2 | 2/2 | 2/2 | 0 |
| 3 mm | 0/2 | 0/2 | 2/2 | 2 |
| 6 mm | 0/2 | 0/2 | 2/2 | 2 |
| 12 mm | 0/2 | 0/2 | 2/2 | 2 |
| 24 mm | 0/2 | 0/2 | 2/2 | 2 |

These are two known scenes100/101 reused across the matrix, not36 independent
scenes or confirmatory performance evidence. All36 acquire the peg and pass
injection readiness. All30 nonzero biases apply before contact. Achieved
pre-insertion object-target Y displacements track the requested family within
1.932micrometres; all pre-insertion contact forces are zero. At harder offsets,
nominal motion contacts the channel front and fails depth. V1's depth diagnosis
matches the independent reference, with12-action first-detection latency.
All eight V2 retries complete backout/realign/reinsert/verify in148–160 actions,
within existing caps. There are zero unnecessary attempts or regressions in
the four normal/easy matched pairs. The old velocity shadow fails on all36
trajectories and does not gate active motion. Original v1-v4 failures remain
unchanged, and [normal-six-v5](evidence/AETHER_CL_M7_Normal6_v5_Review.json)
remains a separate retained commissioning record.

The selected frozen family is clearance ratios0/.5/1/2/4/8, nominally
0/1.5/3/6/12/24mm. Each actual requested magnitude uses that episode's
`hole_radius - peg_half_width`; log the achieved object-target displacement
instead of assuming commanded TCP displacement is the disturbance.
No new controller, gate, threshold, recovery cap or physics change is selected
after commissioning. Development selected the design; fresh outcomes will
evaluate it without further tuning or adaptive seed replacement.

## Frozen task and systems

The independent task reference requires fresh bilateral finger contact while
the peg is at least30mm above reset height. Historical contact followed by
ungrasped flight is insufficient. It reconstructs contact acquisition from raw
finger forces/directions, independent of the environment's built-in success.

Insertion depth is peg-head X in the hole frame plus channel half-length L.
Depth must be0.8L–1.2L. Orientation error is at most0.05rad, allowing the square
peg's equivalent quarter-turn roll. The full peg cuboid clipped to the channel's
axial slab, including entry-plane edge intersections, must fit the square hole
with at most0.2mm collision slop. Head-only or TCP arrival does not establish
success. Final release is not required for this task; contact and grasp remain
logged. Success is not latched.

Require ten consecutive eligible control observations after acquisition, with
all five external100Hz physics samples per action. Every sample must satisfy
the depth/orientation/clipped-volume relation. Adjacent object-target poses
must imply speeds at most10mm/s and0.15rad/s; control-frame relation change is
at most0.5mm/0.01rad. Whole50-sample window translation/rotation diameters are
also bounded by0.5mm/0.01rad. Complete intermediate samples reject motion hidden
by identical endpoints, transient wall intersection and accumulated drift.
Raw reported solver velocities retain the old rule as a shadow. Internal
solver iterations and behavior after release are not observed. Built-in
success is logged only and enters neither control nor the independent score.

Baseline executes the commissioned fixed nominal insertion schedule. V1 adds
passive verification without changing any action. V2 adds the same verifier
and one bounded recovery. All share sustained full close, once-after-lift grasp
calibration, cached nominal target geometry and bounded transverse TCP integral
tracking. The phase schedule is80/60/30/60/100/100/60/140/80 actions,710 total.
Every episode retains all1200 actions, including terminal holding. Nominal
control consumes no evaluator, contact label, disturbance label or substep
input after calibration; the complete substeps feed verification/reference
and recovery verification only.

V2 permits one420-action episode with120/120/140/40 backout/realign/reinsert/
verify caps, minimum three stage actions and minimum80 remaining actions to
start. Backout requires the entire peg safely40mm before entry; then refresh
object/target/grasp geometry once. Realign requires acceptable object orientation
and projected fit. Reinsert requires valid insertion depth/volume/orientation.
Verify requires ten eligible observations within that phase and the complete
pose window. TCP arrival alone completes none of those stages. Earlier failure
consumes the same attempt; a later failure receives no second retry. Terminal
behavior repeats the last absolute command. Failed and zero-attempt costs stay
in the analysis.

## Fresh matrix, retained pilot and execution

Select native reset seeds140–159 only if the retained-history guard confirms
they are unused. Commissioning's final guard checks2776 retained event files,
with reset seeds0–139 only. Recheck at fresh entry; deleted or unreported runs
are outside this evidence. Do not inspect replacement seeds or replace failed
scenes. There are360 slots: six conditions ×20 common scenes ×three systems,
18 cells,20 episodes each and432,000 planned actions. These are20 common scenes
reused across conditions, not360 independent scenes. There are no exclusions.
Missed injection readiness, unsuccessful acquisition, failure, abort, false alarm
and regression are retained. Invalid infrastructure evidence stops execution
for review rather than rerunning a slot.

The first18 slots use normal,1.5mm and6mm conditions, seeds140/141 and all three
systems, in condition/seed/system order. They are already part of the360-slot
matrix and remain in final analysis. Execution automatically pauses and writes
an immutable pilot archive and external SHA-256 receipt. Its gate requires
complete replays/source identities, all16 pilot comparisons, at least one
healthy normal Baseline and the eight nonzero Baseline/V1 injections before
meaningful contact. There is no V2 success gate. A failed pilot retains every
outcome and stops for review; do not tune against these fresh outcomes or
silently restart a new seed range. Independent review precedes resume.

The remaining342 slots follow ascending condition/seed/system order, omitting
only already retained pilot slots. Every slot uses a fresh Python interpreter
and simulator. The worker requires a live sweep parent with the same selected
slot, frozen protocol and source/software/environment identity before reset.
Standalone fresh episode entry is blocked. Initial entry revalidates the
independently reviewed commissioning archive, indexed raw files, all36 replays
and34 comparisons before any fresh reset. A sweep ownership lock prevents
concurrent writers. Archive/output paths must be new; there is no slot rerun.

Resume accepts only a valid paused checkpoint with unstarted slots. It checks
the committed source/protocol, installed package/source/asset bytes, software,
child environment, exact archive/raw indexes, all prior trial replays, pairs and
aggregate reports. The pilot archive SHA and every pilot raw child/source/
protocol file remain immutable. An errored/interrupted slot blocks automatic
resume and is archived for review. History on resume excludes only this already
validated study and rejects selected-seed resets in any other retained run.

SSH/terminal process fields and `XDG_SESSION_ID` are removed from the child
environment before every launch and frozen as nonphysical provenance fields.
All remaining environment values are passed and hashed, including GPU and
native library configuration. A new SSH session therefore needs no historical
session-ID spoofing; changing physical configuration still blocks resume.
No frozen controller/scorer or installed bytes may change between pilot and
the rest of the matrix. PR stays open/draft/unmerged and main stays unchanged.

## Analysis and audit

The [machine protocol](evidence/AETHER_CL_M7_Insertion_Protocol.json) freezes
all execution source hashes, commissioning/inspection receipts, seed/condition
selection, task semantics, limits, comparison counts and resume rules. Primitive
manifest names retain their development producer identifiers; their enclosing
protocol and fresh execution flags supply frozen scope. Two shared entry/replay
functions receive optional configuration/metadata parameters; numerical
controller/reference/verifier/recovery logic is unchanged.

Audit every action, decision, raw acquisition, reference/verifier/recovery state,
independent physical endpoint, every physics sample and final result. Actions
have3e-7 reconstruction tolerance and derived scalar diagnostics1e-10; physical
pairs remain exact. Baseline/V1 compare all1200 actions; V1/V2 compare through
the observation preceding first recovery action, or the full budget if none.
Normal/disturbed Baseline pairs compare through430 actions before injection.
Final counts are120 passive,120 recovery and100 pre-injection control pairs.

Report final insertion success/depth, object-target relative pose and goal error,
acquisition, achieved offsets, contact/depth timing, failure detection/latency/
diagnosis, recovery attempts/success/abort, each effect-stage completion,
unnecessary intervention, healthy regressions, full action/TCP-path costs,
paired V2-minus-V1 costs, controller completion versus task success, old velocity
shadow and the robustness curve. Keep partial cell denominators explicit; no
partial curve is presented as the complete20-scene result. Export deterministic
episode/cell/paired CSVs and revalidate them alongside the JSON report.

The final claim remains limited to privileged state, one rigid peg/channel,
one arm and synthetic lateral waypoint bias. Physics-propagated disturbance,
non-privileged sensors, memory/world models, Prototype B/C/D, foundation models
and02W remain deferred. After frozen native M7 audit, return to02 before any
further scope.
