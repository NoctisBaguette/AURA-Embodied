# AETHER-CL M8 — physics-propagated placement results

Reviewed 2026-10-09 (Asia/Shanghai). The frozen 360-episode native matrix and independent evidence audit are complete. **This is the 06-01 return to 02, not 02 acceptance or authorization for another round.** Measurement remains `e8184217dc4b3c205666787441b87b13ba8a489c`; this publication adds evidence only.

## Result and supported claim

The accepted placement verification/recovery pattern remains useful when a disturbance is applied through the simulator's rigid-body force API. Baseline and passive-verification V1 succeed in 70/120 condition episodes each; V2 succeeds in 115/120. V2 attempts all 50 matched Baseline failures and rescues 45 (90%). All 70 matched Baseline-success cases remain successful with no recovery. Five unsuccessful retries remain in the result and denominators.

The supported claim is narrow: **in this privileged-state, single-arm released-placement task, verification-gated one-episode recovery rescues 45/50 failures caused by the frozen engine-force disturbance family while preserving the 70 matched Baseline-success outcomes.** The pattern transfers from synthetic relocation to this physics-propagated disturbance setting. M8 does not isolate the lower-phase predicate as its sole cause, prove universal recovery, or establish sensor or real-robot robustness.

| Frozen condition | Commanded world +Y force (N) | Baseline | Passive V1 | Recovery V2 | Matched rescues | Failed retries |
| --- | --- | --- | --- | --- | --- | --- |
| normal | 0 | 20/20 | 20/20 | 20/20 | 0 | 0 |
| force-easy-v1 | 0.418684 | 20/20 | 20/20 | 20/20 | 0 | 0 |
| force-probe-1 | 1.857689 | 7/20 | 7/20 | 20/20 | 13 | 0 |
| force-probe-2 | 2.322111 | 9/20 | 9/20 | 19/20 | 10 | 1 |
| force-probe-3 | 2.902638 | 7/20 | 7/20 | 18/20 | 11 | 2 |
| force-probe-4 | 3.628298 | 7/20 | 7/20 | 18/20 | 11 | 2 |

Whole-matrix success increases from 58.333% to 95.833%, a descriptive gain of 37.5 percentage points. Across the four harder conditions, success increases from 30/80 to 75/80. These are **20 common fresh scenes reused across six conditions and three systems**, not 360 independent scenes. The 45 rescues occur across 14 distinct scenes; failures occur on scenes 172 and 178. No seed is replaced and no initial-goal exclusion occurs.

## Frozen task, systems and disturbance

Authority is DEC-0007 / 02's M7 acceptance at `4d477da2a583717b773b3a1c746996a3c2127e40`. The [preregistration](AETHER_CL_M8_Placement_Preregistration.md) and [machine protocol](evidence/AETHER_CL_M8_Placement_Protocol.json), SHA-256 `3e67b43747b4d52b73b39c64d2b1f159a855f91cde012b8a5ceffbaf6c40a031`, precede the fresh outcomes. Exact force vectors were selected through independently audited development on reused scenes 100/101, then frozen before seeds 160–179. Development success is not pooled into the fresh result.

Installed ManiSkill 3.0.1 `PickCube-v1` uses one Panda arm, one rigid cube, unrendered CPU physics and privileged `state_dict` observations. The accepted placement task preserves sampled target XY and projects target Z to the cube center on the designated table. Independent success requires historical acquisition/lift, current release and non-grasp, valid table support/contact, task XY error within 25 mm, gripper opening/TCP clearance, and five consecutive fresh stable task observations. Built-in environment success does not define this placement score or drive recovery.

Baseline runs the unchanged fixed placement controller. V1 adds passive verification with the same physical motion. V2 adds the accepted effect-aligned recovery (legacy V2R) and at most one 400-action episode within the same 800-action total budget. It refreshes geometry once, retracts/reacquires, transports, establishes placement readiness, releases, retracts and settles. Recovery retains its original phase deadlines. There is no second attempt.

At action 296, during active nominal retract, the disturbance requires an already released, supported, ungrasped cube with designated-table vertical contact force at least 0.01 N. `PhysxRigidBodyComponent.add_force_torque` applies the frozen world +Y force with zero torque for five 100 Hz substeps (0.05 s). There is no cube pose/velocity overwrite or displacement target. Every nonzero-force episode meets the frozen application precondition: 300 episodes, 1,500 force calls. Normal applies zero calls. No missed precondition is retimed or replaced.

The accepted runner supplies every motor action. An independent controller-state replay gates instrumentation by the actual phase and must match each action before physics stepping and each recorded decision/verdict afterward. It does not supply commands or consume the independent task score. The M6R synthetic disturbance field remains `none`, meaning that the old relocation mechanism is disabled; the external M8 force is logged separately.

## Causal controls and selective invocation

All 120 Baseline/V1 pairs match for the full 800 actions and external physics samples. Verification alone does not improve placement success. All 120 V1/V2 pairs match through the justified recovery boundary; 70 healthy pairs remain identical for the full episode. The 50 failed pairs share physical/verification history through action 342 and diverge only when V2 acts at 343. All 100 normal/disturbed Baseline pairs match through the 295-action pre-force prefix. This supports attributing matched improvement to the recovery system after the disturbance, rather than different initial conditions or nominal motion.

For both V1 and V2, all 50 episode-first reference failures are `PLACEMENT_TARGET_NOT_REACHED` at 340; all are confirmed at 342 with the same diagnosis. Latency is two control actions (0.1 simulated seconds). No detected first onset precedes or lacks a reference onset. There are zero unnecessary attempts and zero final regressions among the 70 Baseline-success pairs, including all normal/easy controls.

Frame-level metrics are retained, not substituted for these episode counts. V1 records 22,950 true positives, 100 false negatives and zero false positives over 96,000 observations; V2 records 55 true positives, 100 false negatives and zero false positives. V2 changes recovery phases and therefore reference exposure after invocation. These frame ratios are not directly comparable static-classifier performance or independent perception accuracy. This verifier still uses privileged geometric state.

All 120 Baseline/V1 controllers complete their schedules despite 50 final task failures. Physical task verification remains necessary to distinguish motion completion from placement success.

## The five retained recovery failures

All five retries abort before closing/grasping. Four fail the 60-action approach phase; one fails the 35-action descend phase. At the first abort, position error exceeds the frozen 20 mm arrival gate while orientation passes its 0.15 rad gate. None reaches lower readiness, release or recovery retraction. None exhausts the overall 400-action recovery budget or times out in lower.

| Scene | Condition | Failed phase | Abort action | TCP-to-phase-target error at abort | Final task XY error |
| --- | --- | --- | --- | --- | --- |
| 172 | probe 2 | descend | 414 | 24.810 mm | 176.843 mm |
| 172 | probe 3 | approach | 422 | 89.878 mm | 323.453 mm |
| 178 | probe 3 | approach | 412 | 131.054 mm | 413.206 mm |
| 172 | probe 4 | approach | 405 | 290.294 mm | 453.054 mm |
| 178 | probe 4 | approach | 408 | 282.995 mm | 565.124 mm |

The retained traces establish the immediate failure: the bounded retry does not establish target arrival before its phase deadline. Larger force responses can leave the object far from the recovery's current TCP state. This is evidence of a movement/phase-budget limit in the available corrective strategy, not a proof that the targets are kinematically unreachable, nor a unique diagnosis of joint limits, contact dynamics or servo behavior. No repair or deadline tuning is made after observing these outcomes.

## Force inputs, physical response and costs

Force magnitudes are monotonic; contact-mediated outcomes need not be. Baseline success rises from 7/20 at probe 1 to 9/20 at probe 2. Scene 175 fails probe 1 and succeeds probe 2, and fails probe 3 while succeeding probe 4; scene 179 fails probe 1 and succeeds probe 2. All transitions remain retained. Contact/trajectory records support a state-dependent physical response; M8 does not isolate a single contact as the unique cause.

As descriptive Baseline diagnostics, median post-pulse peak XY displacement is 10.081 mm for easy and 34.355/38.908/62.068/131.774 mm for probes 1–4. Corresponding maxima are 10.112/163.322/189.284/413.002/564.921 mm. These are observed responses to forces, not commanded offsets. Diagnostics distinguish the five-substep pulse, the window before first V2 intervention, and whole-episode response that can include recovery. The exact windows and all values are retained in [diagnostics](evidence/AETHER_CL_M8_Diagnostics.json).

All 45 successful retries complete effect-aligned lower readiness, release, retraction and stable placement, using 120–227 actions (mean 152.867). Across all 50 attempts, including failures, the mean is 144.6 actions with range 63–227. Retry actions occupy the existing 800-action episode budget rather than increasing episode length.

| Condition | Mean V2 recovery actions over all 20 outcomes | Mean total TCP-path change V2 − V1 over all 20 outcomes |
| --- | --- | --- |
| normal | 0 | 0 mm |
| easy | 0 | 0 mm |
| probe 1 | 88.35 | +343.938 mm |
| probe 2 | 74.65 | +293.209 mm |
| probe 3 | 91.95 | +358.564 mm |
| probe 4 | 106.55 | +430.007 mm |

Across all 120 V2 outcomes, mean retry activity is 60.25 actions and mean added TCP path is 237.620 mm. The supplementary rescue-conditioned mean added path is 605.790 mm; it excludes failed and untouched cases and must not replace the all-outcome cost. All-outcome mean final XY error is 59.391 mm for Baseline/V1 and 24.170 mm for V2; the failed endpoints remain included.

## Independent audit and reproducibility

Final archive: `aether-cl-m8-placement-seeds160-179.tar.gz`, **194,587,248 bytes**, SHA-256 `667c043859f9d639bbff79e3456c4a608d4ef336806f94b77acccde40870924c`. Safe extraction verifies 5,066 unique regular-file/directory members and all 3,983 indexed file sizes/hashes. All 21 source/protocol/receipt/history-guard snapshot Git blobs match the measurement tree. Every selected slot, child configuration, source/software identity and normalized startup environment matches the frozen parent. No environment values are republished.

The original [first18 pilot](AETHER_CL_M8_First18_Review.md) remains immutable at SHA-256 `535218e74854326946a157f8aa620aa1ca41db78351097074074702cd49d295c`. Its 221 indexed files verify; all 219 source/child files retained in the final archive are byte-identical. The original 18 trial records and pilot gate are unchanged. The resume log has exactly 342 ordered start/end pairs, the evidence-valid marker and matching final archive hash.

Full read-only reconstruction passes all 360 accepted-runner, physics and instrumentation audits: **288,000 actions with zero maximum replay error; 1,440,000 external physics samples; 288,000 matched controller-gate actions; 1,500 engine force calls**. All original per-child audit JSON regenerates exactly. All 340 strict matched comparisons pass (120 passive, 120 recovery, 100 pre-force). The final gate, physical diagnostic windows, aggregate JSON and original cell CSV byte stream regenerate exactly. Action tolerance remains 3e−7 and physical pairs remain exact; no tolerance is widened after outcomes.

The recorded retained-history scan checks 3,216 event files and 5,719 reset records, with no selected-seed overlap outside the validated own study. Entry/resume retain the same external-history fingerprint `f330e9f28c1398fbe4e552ffef96048075b1647a1e959af9995f122b8fc6b586`. This upload includes the guard record and pinned guard source, not the entire remote historical event corpus. Commissioning prerequisites match the previously independently reviewed 36-episode archive, report and review hashes.

Local replay uses Python 3.10.21 / NumPy 1.26.4 / SciPy 1.10.1 against native Python 3.10.22 with matching NumPy/SciPy arithmetic. It does not execute the native simulator. The frozen implementation's focused fixtures passed 15/15 before native execution; this evidence-only publication changes no measurement code. Full replay, artifact cross-checks and Python 3.10 syntax validation are the relevant checks.

Evidence: [machine audit](evidence/AETHER_CL_M8_Native_Audit.json), [all episodes](evidence/AETHER_CL_M8_Episode_Outcomes.csv), [all matched pairs](evidence/AETHER_CL_M8_Paired_Outcomes.csv), [all cells](evidence/AETHER_CL_M8_Cell_Outcomes.csv), [failure/response/cost diagnostics](evidence/AETHER_CL_M8_Diagnostics.json), [executed full review](evidence/AETHER_CL_M8_Executed_Review.py) and [executed analysis](evidence/AETHER_CL_M8_Executed_Analysis.py).

## Return to 02 and application milestone

M6R and M7 are already accepted under DEC-0006/0007. M8 now supplies completed, independently audited evidence for the planned physics-disturbance dimension. **02 decides acceptance and Prototype A closure status.** Non-privileged sensor verification remains open. The intended next sequence is return to 02, then 02W verifier design/scope and M9 only if authorized. No model training, optimizer update, sensor verifier, physical robot experiment, new rendering, memory/world model or Prototype B/C/D is introduced here.

For the 零点计划 application, the defensible milestone is a functioning simulation prototype with accepted placement/insertion studies and completed M8 evidence under independent review. It demonstrates that physical task verification plus bounded corrective action can improve manipulation outcomes and identifies concrete failure limits. Describe the 45 rescues as matched scene-condition outcomes on 20 shared scenes, distinguish simulation from real-world validation, and retain the sensing gap as a next research objective. PR #1 remains open, draft and unmerged.
