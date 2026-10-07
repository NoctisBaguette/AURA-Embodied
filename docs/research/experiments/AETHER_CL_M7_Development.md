# M7 development — PegInsertionSide-v1

Date: 2026-10-07 (Asia/Shanghai).

Status: normal-six-v3 evidence passes with 0/6 insertion successes. Seed100
meets geometric insertion but fails velocity-based stability; seed101 remains
at the entry with residual interference. Bounded transverse TCP tracking,
a calibrated holding aperture and read-only substep logging are locally tested;
normal-six-v4 native commissioning is pending. No fresh-native M7 protocol or
result is frozen.
Authority remains [02's M6R acceptance / DEC-0006](AETHER_CL_M6R_02_Research_Review_v0.1.md)
at `145aadce249b23a49ecb899ff273e93f673dd03b`.

## Installed-source selection

The operator returned `m7-task-inspection.json`: 406,401 bytes, SHA-256
`901a789c374e203d8ad59a9e012ca6364ee0ae8a6c557a324545ebed0e7ea828`.
All embedded source byte counts and hashes verify. The clean native measurement
checkout was `9ac5439e003f2ed65ecf2ea02f59a6186c7b6714`, with Python 3.10.22,
ManiSkill 3.0.1, Sapien 3.0.3, NumPy 1.26.4, SciPy 1.10.1, Torch 2.4.1+cu121
and Gymnasium 1.1.1. Inspection created no environment and reset no seed.

Select installed `PegInsertionSide-v1`, using its supported `panda_wristcam`
single arm, state observations, CPU physics and `pd_ee_pose` control. No camera
observations enter control or verification. The installed Panda-v3 URDF is
present and hashed. No task assets, reset poses, collision shapes, physics or
installed package bytes are changed. The native registration has a 100-step
TimeLimit; development explicitly sets a 1,200-action budget without modifying
the task itself.

The peg is a rigid box: half-length 85–125 mm and square half-width 15–25 mm.
Four rigid box walls form a channel along the target's local X axis. Its axial
half-length equals the peg half-length; its square hole half-width equals the
peg half-width plus 3 mm. The peg, target yaw and hole offset are randomized.
This is a simpler single-peg relation than the installed two-prong PlugCharger
with 0.5 mm clearance or a multi-shape kit task. The existing task fits the
authorized question, so no custom environment is required.

The installed built-in test uses only the peg-head position: head X at least
-15 mm and head Y/Z within the hole radius. It has no explicit upper depth,
orientation, acquisition or persistence requirement. This is logged separately
and never used as controller input or the independent task score.

The [inspection receipt](evidence/AETHER_CL_M7_Installed_Inspection.json) retains
all source hashes, versions and seed provenance. Native preflight requires those
exact package/source/URDF bytes. The original full inspection report is copied
into every development archive, alongside the new execution source snapshot.

## Development contract and matched systems

These numerical candidates may change on development evidence before fresh freeze.
They are not confirmatory preregistration.

Independent acquisition requires fresh bilateral finger contact while the peg
is at least 30 mm above its reset height. Contact history alone plus a later
ungrasped flight does not satisfy acquisition. Raw finger forces and directions
are retained and independently checked against the native contact label.

Insertion depth is the peg-head center's local X plus channel half-length L.
The candidate final interval is 0.8L–1.2L, around nominal depth L. Orientation
error must be at most 0.05 rad, allowing equivalent quarter-turn roll of a square
peg but rejecting reversed entry. All vertices of the peg volume clipped to the
channel's axial slab must fit its square cross section, with 0.2 mm collision
slop. Checking clipped edge intersections at the entry plane rejects a tilted
peg whose head is centered but whose inserted body intersects a wall.

Require ten consecutive fresh stable observations: linear speed at most
10 mm/s, angular speed at most 0.15 rad/s, frame translation at most 0.5 mm and
frame rotation at most 0.01 rad. Final release is not required for this insertion
task; grasp/contact status is logged. Final success is not latched forever.

| System | Nominal motion | Verification | Recovery |
| --- | --- | --- | --- |
| Baseline | Fixed task-specific insertion schedule | Disabled | Disabled |
| V1 | Exact same controller | Passive pose/velocity/attachment proxy | Disabled |
| V2 | Exact same controller until confirmed failure | Same verifier | One bounded episode |

The nominal schedule is approach/descend/close/lift/carry/prealign/offset/insert/
settle, with durations 80/60/30/60/100/100/60/140/80 actions (710 total). Grasp
the peg 60 mm behind its center. Close fully during acquisition, then once
at the first lift cache a holding command from measured finger qpos minus
4 mm per finger. Map through the installed -10/+40 mm target range; invalid
aperture proxy retains the closed command and its outcome. Refresh the actual TCP-in-peg grasp transform
once after lift. Cache the target and insertion poses; only TCP feedback enters
the nominal servo after that calibration. No contact, score or verifier output
enters nominal action selection. Translation/rotation limits are 12 mm/0.06 rad
per command, with independent 4 mm axial and 4 mm transverse-norm bounds during insertion
and settling (maximum combined norm 5.657 mm). A long remaining axial distance
does not reduce height/lateral correction. The cached target frame and TCP are
the only inputs to this nominal servo. A transverse TCP integral correction
(gain 0.1 per action, 6 mm norm cap, learn only within 6 mm transverse error)
compensates persistent tracking bias. It never integrates axial insertion error.
The same cached holding command and bounded transverse compensation are used
by recovery; evaluator contacts/success remain absent from these inputs.

V2 has one 420-action recovery episode, stage caps 120/120/140/40 for backout/
realign/reinsert/verify. Phase progression requires the physical effect:
entire peg safely before the entry plane by 40 mm; acceptable orientation and
projected cross-section alignment; valid inserted depth/clearance; then ten
stable observations. Refresh object/target/grasp geometry after safe backout.
TCP arrival alone completes none of those stages. An earlier acquisition or
attachment failure consumes the episode and aborts if a held peg is unavailable;
it does not grant a second acquisition/insertion retry. Failure and costs remain
retained. Terminal recovery repeats the last absolute command.

## Synthetic misalignment commissioning

The development injector biases cached nominal offset/insert/settle waypoints
along target-local positive Y after nominal prealignment, before meaningful
contact. The arm carries the held peg laterally, then executes the nominal
axial insertion. This is a synthetic waypoint-induced misalignment, not a
force disturbance or a teleport of the object out of its gripper. It introduces
no new controller branch and never passes a disturbance label to verification
or recovery. Recovery uses freshly observed object/target geometry.

Candidate ratios are normal plus 0.5/1/2/4/8 times the installed 3 mm clearance:
1.5/3/6/12/24 mm. They are a development search series, not frozen magnitudes.
Angular perturbations remain deferred. Injection requires valid acquisition,
actual prealignment, the entire peg at least 40 mm before entry and peg-box
contact force at most 0.05 N. Missed preconditions remain recorded, not excluded
or replaced. Record actual pre-insertion object-target error and force, first
positive depth and first peg-box contact. Commissioning must establish that
the requested bias produces the intended physical misalignment before choosing
the final family. Requested waypoint offset is not assumed to equal peg offset.

## Local validation

All 31 focused tests pass in the primary runtime (20.851 s) and with Python
3.10.21 / NumPy 1.26.4 / SciPy 1.10.1 (15.852 s). New counterexamples
exercise transverse bias correction without axial windup, installed negative
gripper lower-bound mapping and once-only holding calibration, and diagnostic
hook chaining/restoration plus rejection of missing/altered substep data. The
full matched fixture reconstructs 3,600 endpoints and checks exact paired raw
observations and selected substeps, with tamper rejection. Python 3.10 parsing
and unchanged M0–M6R preflight pass. These fixtures establish software behavior,
not native grip stability or insertion viability.

## First development failure and repair

At `a1cab433f33755641c4113557cf666b37c0c5418`, native normal-six stopped during
the first Baseline seed-100 episode after its first action returned. The other
five slots did not launch. The [failure receipt](evidence/AETHER_CL_M7_Development_Failure.json)
verifies all 16 indexed files and exact archive membership. Archive SHA-256:
`0043f87ba74dd6aa2b23bf293cab660d2eb8b4718ee3fae9d39d2cc69f248c8f`.
Only run_started/reset/run_failed events exist: the failing observation was
checked before it could be logged. Its actual target/geometry delta is unknown.
The SAPIEN Vulkan fallback warning preceded a successful environment reset and
action; the fatal exception came from our target identity guard.

The old guard demanded bitwise equality of a composed floating-point target
pose. The repaired development guard compares physical translation and SO(3)
rotation, accepting at most 1 micrometre and 1 microradian relative to the reset
anchor. Quaternion sign and normalization are handled by the existing pose
rotation conversion. Dimensions and hole radius remain exact. This is a fixed
target identity roundoff bound, separate from task readiness/scoring and exact
matched raw traces. Every reference frame logs raw equality and physical deltas;
recovery uses the same physical check. Larger changes stop the run. Reference,
verifier or recovery-check exceptions now retain the raw post-action observation,
info, action, decision, reward and termination flags before raising.

Floating-point representation is a plausible cause, not proved by the missing
frame. The new native record must resolve it. Keep the original failed directory,
archive and log intact. Do not resume or rewrite them. Repaired commissioning
uses `m7-development-normal6-v2` as a new run/output/archive/log, still known seeds
100/101 only. Nominal motion, success thresholds, recovery effects/budget and
M0–M6R remain unchanged.

## Completed normal-six-v2 review and shared servo repair

[Independent review receipt](evidence/AETHER_CL_M7_Normal6_v2_Review.json) retains
all six endpoint/replay outcomes, matched boundaries and diagnostic samples.
Archive SHA-256:
`aad7c51ee7df126ef8a4a279e7da831b6a25848fa1e40d1d3d096b1dd033fb07`.
All 41 indexed files and exact membership verify. All 7,200 actions/decisions/
reference/verifier/recovery states replay against archived source using
NumPy 1.26.4 and SciPy 1.10.1, with zero action error; all 7,200 independent
raw-force/geometry/stability endpoints agree. Four strict pairs pass: 1,200
actions each for Baseline/V1, then 646 and 642 for V1/V2 before recovery.
A newer SciPy runtime chooses the equivalent opposite-sign pi Euler
representation on one action, so strict action replay uses matching numerical
versions, without relaxing raw pairing or replay bounds.

All six runs acquired/lifted the peg. At step 490, normal head alignment was
within the channel capture band. By step 530, before entry, head lateral/Z
error reached 12.0/-17.7 mm for seed100 and 19.3/-29.5 mm for seed101.
The desired TCP Z remained 137.385/77.741 mm, but commanded Z had fallen to
120.814/49.864 mm. The original servo limited the norm of the entire remaining
position error to 4 mm: long forward travel scaled away transverse correction,
allowing the requested height to follow the observed downward drift. Both
pegs then contacted the front face without meaningful insertion. Both V2
attempts completed physical backout and realignment, then hit the 140-action
reinsert cap, retaining failure and costs. These are failed healthy development
controls, not evidence that insertion recovery generalizes.

The shared slow servo now separates cached target-axis error from its
perpendicular component, bounding them independently at 4 mm and 4 mm norm.
This changes the combined maximum step norm to 5.657 mm and is explicitly
recorded in nominal/recovery manifests. It applies to nominal insert/settle and
recovery backout/reinsert/verify; other motion, rotation limits, phase criteria,
budgets, scoring, disturbance semantics and old measurement sources stay fixed.
No evaluator, object-contact or failure label enters nominal servo feedback.

The repaired target identity checks stayed within about 15 nm and
0.08–0.12 microradian on the first observations, with unchanged dimensions.
This supports the target-guard repair; the missing observation from the
original error archive is still unavailable. Keep both previous development
archives, directories and logs unchanged. Launch known-seed normal-six-v3
in a new output/archive/log. Do not launch misalignment commissioning until
normal insertion behavior has been independently reviewed.

## Normal-six-v3: two remaining failure mechanisms

[Independent v3 review](evidence/AETHER_CL_M7_Normal6_v3_Review.json) verifies
all 41 indexed files, exact membership and all 7,200 replayed actions/endpoints.
Archive SHA-256:
`67e7da8b67994e1659627d41797beaa7befb8470c16228df81bf98f9ae77c272`.
Four strict comparisons pass: Baseline/V1 at 1,200 each, V1/V2 at 642 each.
All records acquired/lifted the peg and retained failure.

Seed100 ends at depth 106.248 mm with orientation error 0.00356 rad and positive
1.048 mm channel margin. Geometric insertion passes, but reported linear/angular
speeds remain 0.02059 m/s and 0.54740 rad/s, above unchanged 0.01/0.15 limits.
Success is false. Consecutive final poses differ by only 0.300 micrometre and
2.218 microradian; these control-frame data cannot resolve intra-step motion
versus a physics velocity discrepancy. V2 completes reinsert, then times out
at the 40-action verify cap. Do not call this a stable success or weaken scoring
to accept it. Seed101 head Z is -3.775 mm with -0.394 mm channel margin: it
clips the entry and fails depth. Its V2 completes backout/realign and times out
during reinsert.

Installed Panda finger targets span -10 to +40 mm. Continuing action -1 after
grasp requests -10 mm while held fingers sit near +16/+19 mm; measured loads
are roughly 26/29 N. Closing overdrive is a plausible contributor to velocity
behavior, not established causation. The next development controller caches a
post-close holding aperture with 4 mm overdrive per finger, and adds bounded
transverse TCP integral correction. Both systems remain matched; grip loss,
missed disturbance readiness and score failures are retained. Scorer, thresholds,
phase effects/durations, single-attempt limits and old sources remain unchanged.

Selected physics substeps now record raw peg pose and velocities immediately
after chaining the original CPU simulation hook. Sampling covers steps
170/230/430/490/530/630/640/710, final10 and each recovery verify action. The
original hook is restored at cleanup. Samples enter neither motion nor scoring.
Audit requires full selected counts, exact final-substep/observation agreement,
and exact matched prefix samples. This diagnoses the sampling discrepancy
without modifying installed task/physics bytes.

Retain all three earlier development archives/directories/logs. Run new
normal-six-v4 on known100/101 only and review before misalignment commissioning
or any fresh freeze. Native improvement is unverified.

## Repaired native operation: normal-six only

Run the focused M7 test file on the inspected server first. Then execute six
fresh-process development slots: known seeds 100/101, normal condition,
Baseline/V1/V2. Each child receives one 1,200-action episode. Its source,
software and startup-environment digest must match the parent. Replay every
action, decision, verifier/recovery/reference state, raw-force acquisition,
independent physical endpoint and final report. Compare Baseline/V1 exactly
through the full budget, and V1/V2 exactly through the preceding observation of
the first retry action, or the full budget when no retry occurs.

The installed inspection checked 2,715 retained event logs (reset range 0–139).
After normal-six-v3, history checked 2728 event logs and again found no
preferred-seed 140–159 overlap. The development entry accepts only 100/101 and checks retained
history before/after execution. It offers no fresh-native entry. History must
be checked again at final freeze/entry; deleted or unreported runs are outside
this guard's scope. No adaptive seed replacement is allowed.

Use the published development commit supplied in the command block. Transfer
a Git bundle from the laptop over SSH port 2221, fetch it on the offline server,
check the worktree clean and detach at that exact commit. Then:

```bash
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
python -m unittest discover -s tests -p test_m7.py -v
```

After tests pass, launch normal-six detached from SSH:

```bash
nohup python -u -m aether_cl.m7_development \
  --output runs/m7-development-normal6-v4 \
  --archive /home/jiangle/aura-work/aether-cl-m7-development-normal6-v4.tar.gz \
  > /home/jiangle/aura-work/m7-development-normal6-v4.log 2>&1 < /dev/null &
echo "M7 development PID: $!"
tail -f /home/jiangle/aura-work/m7-development-normal6-v4.log
```

`M7_DEVELOPMENT_EVIDENCE_VALID` means valid matched development evidence, not
successful insertion or recovery. A child/evidence error stops later slots and
still archives partial evidence; nothing is overwritten or rerun. Ctrl+C stops
`tail`, not the detached runner. Return the archive/log for independent review.
Run the optional candidate series only after the normal behavior is understood.
Freeze the task contract, controller/recovery, offsets and fresh matrix after
development commissioning and before any fresh native M7 outcome.

Return to 02 after frozen native M7 evidence before further scope.
Physics-propagated disturbance, camera verification, memory/world models,
Prototype B/C/D, foundation models and 02W remain deferred. PR stays draft,
open and unmerged; Prototype A stays open.
