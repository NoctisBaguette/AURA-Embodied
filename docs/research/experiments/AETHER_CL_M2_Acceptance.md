# AETHER-CL M2 Native Acceptance Procedure

Date: 2026-10-05 (Asia/Shanghai)

Status: M2 seed-0 development acceptance complete. The original startup mismatch
was corrected, and all isolated native trial/pair/software checks pass.

## Purpose and boundary

Before M3 recovery, accept M2's native task contract, passive verification, and
controlled disturbance path. The seed-0 rendered object-shift trial supplied by
the user detected grasp failure. Its raw evidence and the first six-cell native
archive have now been audited; see the report linked below. Six matched
nonrendered runs supply the normal and dropped-object checks and compare
baseline/V1 traces under identical settings.
The manipulation policy, verifier, runtime, and disturbance modules are unchanged.

| Condition | Baseline | V1 expectation |
| --- | --- | --- |
| none | complete held-cube lift/goal-stability task | same task outcome; passed verification; no failure alarm |
| object_shift | miss the moved cube and fail the task | same task outcome; GRASP_FAILURE; two-step persistence delay |
| object_drop | lose the previously lifted cube and fail the task | same task outcome; OBJECT_LOST; two-step persistence delay |

These are expected outcomes to test, not assumed native findings. A different
physical outcome or detection latency fails this development gate for review;
the runner does not silently tune thresholds or manufacture the expected label.
An already-solved start is recorded as excluded and cannot pass. No seed is
replaced. Both interventions remain synthetic pose relocations with zeroed
velocities; this procedure does not establish physical push realism.

## Execution

Use the already prepared server environment and private GLVND directory. Stop
the finished AETHER viewer with Ctrl+C in its terminal before updating the repo.
The acceptance batch uses CPU physics with no rendered frames; no browser tunnel,
4090, downloads, or new environment packages are needed.

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m unittest discover -s tests -v
python -m aether_cl.acceptance \
    --output /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m2-acceptance \
    --archive /home/jiangle/aura-work/aether-cl-m2-evidence-isolated.tar.gz \
    --live-run /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m2-v1-live/20261005T020329Z-d194299a
```

The existing live viewer must be finished before collecting its files. The
runner validates that its manifest, result, and event log exist before starting
any new trials. Existing archives are not overwritten; for a later rerun, choose
a new filename. A failed acceptance check or interrupt exits with status 2 after
retaining available evidence. Initialization or cleanup exceptions remain errors,
not failed-task scores. Ordinary cell errors allow the remaining cells to run;
Ctrl+C stops the suite and collects partial evidence. Every cell now starts in a
fresh interpreter with the same captured suite-start environment. Child stdout
and stderr are archived. On Ctrl+C the suite signals and joins the child before
collecting its files; a ten-second grace period is followed by forced termination
if it cannot exit. The initial native failed archive is retained for audit.

## Evidence and checks

`suite.json` records every planned/executed cell, configuration, result summary,
individual checks, and three pair comparisons. Each native run retains its
ordinary manifest, result, and events. The suite requires clean recorded Git
revisions and compares software, policy settings, task rules, and task outcome.

Canonical paired traces contain reset seed/geometry/eligibility, each applied
intervention, and every action, observation, controller decision, fresh simulator
info, reward, termination flag, and reference output. Times, wall duration,
verification output, and output paths are not compared. Reset `info` is omitted;
the complete reset observation, including `extra.is_grasped`, remains compared.
The verifier ignores all reset contact flags. Comparison metadata now names
these two locations explicitly; canonical traces themselves are unchanged.
First differing record/field/step and trace SHA-256 values are reported. Exact
equality is demanded for this narrow deterministic development gate; any native
difference needs inspection rather than an automatic change to policy/settings.

`archive_index.json` lists archived file sizes/hashes. The gzip tar contains the
suite, all six run directories' evidence, and the optional earlier live manifest,
result, events, and latest image. A separate local `receipt.json` adds the archive
SHA-256 after archive creation; the archive's own suite cannot include its final
hash. Failed checks still produce an archive. Acceptance does not independently
audit the prior live run; collecting it enables the subsequent raw-log review.

## Validation and next stage

The initial 48 local tests passed. Eight acceptance tests establish that trace drift, incorrect
task outcomes, execution errors, interruption, exclusions, dirty revisions, and
missing prior evidence cannot pass, and that archived content hashes match.
The earlier runtime/verifier/controller tests remain intact. Local fixtures
test data flow and failure handling; they do not model native contacts/physics.

The initial native suite's expected outcomes and all three canonical traces
passed, but the normal pair's startup library environment differed because
OpenCV amended `LD_LIBRARY_PATH` in the shared runner process. Library equality
is not waived. The corrected runner executes each cell in a new process.
All 52 local tests passed, including four regressions for import-side environment
mutation, nonzero child exits, joined interrupt cleanup, and continued rejection
of differing library environments. See [the audit](AETHER_CL_M2_Native_Screening.md).
The corrected native suite has now been audited successfully. All 35 indexed
file hashes, six native trials, and three canonical pair traces pass; all six
startup software records agree exactly. Its trace hashes reproduce the original
suite. See [the isolated audit](evidence/AETHER_CL_M2_Isolated_Audit.json).

After native evidence passes and the earlier live run is audited, freeze the
settings and run matched fresh-seed screening before recovery comparisons.
M3 will add bounded rule-based action intervention while keeping the baseline
policy and shared evaluation budget fixed. Recovery may reopen/reapproach/retry
after confirmed failure; it must not receive disturbance identity or reference
labels. The eventual baseline/V1/V2 matrix will measure episode outcomes and
recovery cost alongside detection/diagnosis. Prototype A findings return to 02.
