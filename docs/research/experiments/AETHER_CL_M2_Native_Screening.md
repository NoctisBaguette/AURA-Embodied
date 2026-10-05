# AETHER-CL M2 Native Development Screening

Date: 2026-10-05 (Asia/Shanghai)

Status: both original and isolated native behavior/traces audited. The original
failed archive remains preserved; the isolated rerun passes all environment and
paired-trace checks. Seed-0 development acceptance is complete.

## Source and integrity

User-supplied `aether-cl-m2-evidence.tar.gz`, 883,072 bytes, SHA-256:
`d157a2e11268a170515e4f5f36b6be5f8080a001e03b998aac500757d970e306`.
All 24 archive members are unique regular files with safe relative names; all
23 indexed file sizes/hashes match. No raw evidence was modified. See
[the compact audit](evidence/AETHER_CL_M2_Native_Audit.json).

The six nonrendered seed-0 trials record clean revision
`3ae309991542ecd01e803c0883097b8338e07fae`. The earlier rendered seed-0 shift
trial records clean `34ce567134871d7ddb04cdb61636e1a4b2e977ae`. Manifests agree on
Ubuntu/Linux environment, Python 3.10.22, Torch 2.4.1+cu121, NumPy 1.26.4,
ManiSkill 3.0.1, SAPIEN 3.0.3, Gymnasium 1.1.1, CPU physics, state observations,
GPU visibility 1, fixed controller, M2 task rules, and absence of recovery.

## Native outcomes

| Condition | Baseline task success | V1 task success | First reference failure | First V1 detection |
| --- | --- | --- | --- | --- |
| normal | true | true | none | none; final verdict passed |
| object shift | false | false | GRASP_FAILURE, step 125 | GRASP_FAILURE, step 127 |
| object drop | false | false | OBJECT_LOST, step 181 | OBJECT_LOST, step 183 |

All six trials executed all 360 steps, completed the schedule, and had no
exclusion, interruption, execution error, or cleanup error. Every normal/drop
episode first established fresh contact grasp at 102; the shifted cases never
grasped. Normal task success first became true at 206 and was true at the end;
the final cube-goal distance was 0.000458 m. Drop episodes achieved a maximum
lift of 0.161509 m before the scheduled intervention; shifted episodes never
lifted. Both disturbed cases continued the frozen empty-handed schedule as
required by passive V1.

V1 dense counts are normal TN 360; shift TP 234 / FN 2 / TN 124; drop TP 178 /
FN 2 / TN 180. There were no false-positive or uncertain frames in these three
episodes. Both detected failure labels agree with the reference, with two-step
persistence latency. These correlated frame counts do not represent hundreds
of independent failure trials or general diagnosis/perception accuracy.

## Raw-log checks

All 2,520 action records across the six trials and prior live episode were
checked. Actions replay against the frozen controller within a maximum absolute
difference of 2.98e-8; decision metadata matches exactly. The replay uses the
Panda base pose specified by the ManiSkill 3.0.1 table scene builder, with float32
pose storage. The base pose is sourced from that wheel, not recorded separately
in these manifests. This is controller replay, not independent policy-quality
validation.

Distances, lifted-height history, fresh grasp/static flags, five-observation task
stability, episode summaries, event sequences, and final results were recomputed
against raw observations. Reference and verifier replay matches every frame;
confusion counts/rates independently recomputed from recorded labels match.
All three canonical baseline/V1 traces match exactly, including actions,
observations, fresh simulator info, reference, and disturbance poses. Reset
`info` is omitted, while full reset observations remain compared, including raw
`extra.is_grasped`. The verifier ignores reset contact flags from both locations.

The earlier rendered shift trace matches nonrendered V1 exactly, including all
360 verdicts. The user-supplied viewer status equals the raw result after removing
the viewer-only frame counter. Its configured injection occurs before step 81:
world y moves from 0.05364291 to 0.17364291 m, preserving orientation and zeroing
velocities. Afterward the cube stays within 1.262 micrometres of the injected
position; no substantial additional finger-launched motion is logged in this
episode. The apparent sideways flight is explained by scripted relocation.
Drop at 181 similarly relocates world y and restores initial cube height. These
remain synthetic state perturbations, not calibrated physical push models.

## Why the original suite still failed

Every behavioral trial check and exact trace comparison passed. Only the normal
pair's `software_equal` check failed: the first manifest has the private GLVND
path alone; the second has the same path preceded by
`/home/jiangle/miniconda3/envs/aether-cl/lib/python3.10/site-packages/cv2/../../lib64`.
All other software fields agree, and the later pairs agree completely.

The acceptance runner executed all trials in one interpreter. The reviewed
OpenCV 4.11.0.86 wheel's `cv2/__init__.py` line 147 modifies
`os.environ['LD_LIBRARY_PATH']` during import. Its wheel SHA-256 is
`6b02611523803495003bd87362db3e1d2a0454a6a63025dc6658a9830570aa0d`.
This source behavior explains the observed first-import path change. Native
trajectory equality does not erase the manifest difference: preserve the
original `failed` report rather than waiving the environment check.

The corrected runner uses a fresh interpreter for each cell with a copy of the
same captured suite-start environment. It retains stdout/stderr and signals/
joins the child on interruption before archiving. Policy, runtime, verifier,
disturbance implementation, thresholds, packages, and budget are unchanged.
All 52 local tests passed, including fresh-process environment isolation,
nonzero-child evidence preservation, interrupt cleanup, and continued rejection
of differing library environments. Corrected native execution was pending at
that point; its completion is recorded below.

## Next gate

Rerun the six native checks using the corrected runner and a new archive named
`aether-cl-m2-evidence-isolated.tar.gz`. Then inspect its manifests and paired
checks. Freeze the shared policy/task/detection settings and screen fresh seeds
before M3 recovery comparisons. Prototype A remains scoped to verification and
bounded recovery; these seed-0 development cases do not establish held-out
robustness or full AETHER implementation.

## Isolated rerun completion

User-supplied `aether-cl-m2-evidence-isolated.tar.gz`, 885,102 bytes, SHA-256
`6e6c513ab126db079730351917a09e2bb481291ce68ded930121892d27ebae6e`.
All 36 unique regular archive members and 35 indexed hashes were checked.
Six clean batch manifests record `3e07c58d68290d009d9a7c175ee22104a9b51379`.
All six startup software dictionaries agree exactly, with the private GLVND
path alone. Every child stdout result equals its raw result; stderr has no
Python tracebacks. Native outcomes, first failure/detection steps, and all three
canonical trace hashes are identical to the original failed suite. The prior
rendered case and its supplied status also match as before. All trial and pair
checks pass; the original failure is retained as historical evidence.

The [isolated audit](evidence/AETHER_CL_M2_Isolated_Audit.json) records these
checks and scope. The old generic `reset_contact_flags_compared: false` label
referred to omitted reset `info`; the actual comparator retained raw reset
observations. New metadata distinguishes the two locations without changing
traces or acceptance results. This clarification affects metadata only, not
policy/verifier input boundaries.

The [frozen fresh-seed screening](AETHER_CL_M2_Frozen_Screening.md) is now
complete and audited: all 120 episodes, exact paired traces, no exclusions.
M3 recovery is implemented as a locally tested candidate with native results
pending. No further seed-0 M2 acceptance rerun is required.
