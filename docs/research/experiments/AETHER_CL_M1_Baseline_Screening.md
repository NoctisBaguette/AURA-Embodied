# AETHER-CL M1 Native Baseline Screening

Date: 2026-10-05 (Asia/Shanghai)

The fixed controller completed the native screening batch without execution
errors. ManiSkill reported success in all 20 episodes. One reset was already
successful without manipulation; the other 19 episodes each acquired a grasp,
lifted the cube, and reached the environment's success condition. This accepts
the controller as an engineering baseline for the current PickCube task, while
exposing evaluation requirements to resolve before research comparisons.

## Evidence and method

Source: user-uploaded `aether-cl-m1-evidence.tar.gz`, SHA-256
`dd740a3868398826a8d48307a39e6633ad0902925ef9302e5e0e79cf660af6e2`.
The archive contains the rendered seed-0 episode and a nonrendered batch for
seeds 0 through 19, including both manifests, results, and complete event logs.
Raw event logs remain in that archive; compact source records and derived audit
data are linked below. No logs were reconstructed from screenshots.

Both manifests record code revision
`bfd144646187bb4985e5d6678320651e3b94b022`, a clean worktree, CPU physics,
Panda `pd_ee_pose`, privileged state observations, and action-space shape `(7,)`.
The server reports Python 3.10.22, Torch 2.4.1+cu121, ManiSkill 3.0.1,
SAPIEN 3.0.3, and `CUDA_VISIBLE_DEVICES=1`. The live run used process-local
`cuda:0` rendering. Rendering was disabled for the batch, so its unused default
`render_device: cuda:1` did not select a renderer. Controller inputs/settings,
seeds, and the 360-step episode cap were unchanged. No disturbances,
verification, or recovery were active.

## Findings

| Measure | Result |
| --- | --- |
| Recorded/completed batch episodes | 20/20 |
| Environment-reported final success | 20/20 |
| Initially successful resets | seed 8 only |
| Initially unsolved episodes reaching success | 19/19 |
| Initially unsolved episodes grasping after reset | 19/19, first grasp at step 102 |
| Logged batch actions | 4,042 |
| Logged rendered seed-0 actions | 202 |
| Execution/cleanup error events | none |
| Median steps among initially unsolved episodes | 238 |
| Sum of batch episode execution time | 16.95 s, excluding initialization/reset |
| Rendered/nonrendered seed-0 trajectory | exact equality in actions, observations, info, decisions, and evaluator records |

The batch ended during approach once, lift once, transport eight times, and
lower ten times. Every episode ended before schedule completion because the
environment terminated on success. This is consistent with the runtime's
termination contract, not a skipped-loop error.

### Already-solved reset

Seed 8's initial cube-to-goal distance was 0.014820819850455023 m, inside the
0.025 m success tolerance. Reset info already reported success. The controller
issued four open-gripper approach actions; none of their post-action states
reported grasping or meaningful cube lifting. On step 4, the robot was static
enough for the environment to terminate successfully again. Its final distance
was 0.014820088672419058 m.

Preserve this as a raw environment success, but do not label it a successful
manipulation. The 19/19 result is an explicitly post-hoc description of the
initially unsolved subset, not a replacement benchmark denominator selected
after observing outcomes. Future comparisons need the same predeclared reset
eligibility rule in Baseline/V1/V2, preserving excluded/reset seed records.

### Loose task semantics and early success

All 19 initially unsolved episodes showed a grasp after reset and at least
0.01 m of cube lift in the logs; that lift threshold is an exploratory audit
description, not a frozen success metric. Seed 2 reached success during lift
at step 128 after only 0.01153 m maximum lift because its goal was nearby.
The present task accepts target proximity and robot static state, while still
holding the cube. It does not certify a full transport distance, sustained hold,
or release onto a supported surface. Final research criteria must state which
of these behaviors the experiment requires.

### Reset grasp flags

Eighteen batch resets reported `is_grasped: true`, followed by
`is_grasped: false` on their first action. This occurs after previously grasping
episodes and is consistent with stale reset/contact information, but the cause
has not been verified in native simulator internals. The policy ignores that
flag, so it does not alter this fixed baseline. A future verifier must not treat
the reset flag alone as proof of a newly established grasp. Validate fresh
post-action evidence and reset/contact handling before using it for diagnosis.

## Audit checks

Read every supplied event record. Recomputed episode step counts, sequence
continuity, final/ever success, aggregate denominator, and cube-goal distances.
Checked that action shapes were seven finite values, gripper commands and
phase progression followed the fixed schedule, goal positions stayed constant,
and success matched the logged placement/static predicates. Checked terminal
flags, episode summaries, final run records, and absence of failure/cleanup
events. Compared all 202 seed-0 trajectory records across live and batch runs.
These checks establish internal evidence consistency; they do not reconstruct
unlogged contact forces or independently rerun physics in this workspace.

## Decision and next engineering step

Retain controller code/settings at `bfd1446` as the current nominal PickCube
baseline. The batch supplies no failure cases and no evidence for verification
or recovery benefits. Do not interpret 20/20 as disturbance robustness or as
proof of the AETHER hypothesis.

Next work is M2 verification, alongside a shared task/evaluation contract:
exclude already-solved starts by a predeclared rule, define required manipulation
and persistence behavior, validate fresh verification observations, and add
controlled disturbances that generate inspectable baseline failures. Any shared
evaluation or termination change requires rerunning the baseline under that
contract; preserve the present evidence as historical screening. Keep the same
policy in Baseline/V1/V2. A rendered demonstration should accompany later batch
evaluation so behavior remains inspectable in the browser.

## Saved records

- [Audit data and per-file hashes](evidence/AETHER_CL_M1_batch_audit.json)
- [Live manifest](evidence/AETHER_CL_M1_live_seed0_manifest.json)
- [Live result](evidence/AETHER_CL_M1_live_seed0_result.json)
- [Batch manifest](evidence/AETHER_CL_M1_batch_seeds0_19_manifest.json)
- [Batch result](evidence/AETHER_CL_M1_batch_seeds0_19_result.json)
