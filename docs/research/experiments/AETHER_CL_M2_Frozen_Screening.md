# AETHER-CL M2 Frozen Fresh-Seed Screening

Date: 2026-10-05 (Asia/Shanghai)

Status: fresh-seed native screening complete and raw logs audited.

## Accepted prerequisite

M2 seed-0 development acceptance is complete on clean native revision
`3e07c58d68290d009d9a7c175ee22104a9b51379`. Six native behavior checks, all three
paired traces, strict startup software equality, and raw-log audit pass. The
isolated evidence archive SHA-256 is
`6e6c513ab126db079730351917a09e2bb481291ce68ded930121892d27ebae6e`.
This validates the development path, not general robustness. See
[the audit](evidence/AETHER_CL_M2_Isolated_Audit.json).

## Frozen matrix

| Setting | Value |
| --- | --- |
| Reset seeds | 20-39 inclusive, original order, no replacement |
| Systems | policy-only baseline; passive V1 |
| Conditions | normal; scripted world-y shift; scripted drop/relocation |
| Episodes | 20 per cell, 120 requested across 20 unique reset seeds |
| Budget | 360 actions per eligible episode |
| Perturbation | 0.12 m, before 81 (shift) or 181 (drop) |
| Task | lifted held-cube grasp, goal tolerance 0.025 m, five static observations |
| Physics/render | CPU physics; no rendering |
| Recovery | inactive |

The [machine-readable protocol](evidence/AETHER_CL_M2_Frozen_Screening_Protocol.json)
records all policy/task/verifier settings and enforced SHA-256 of `policies.py`,
`verification.py`, `disturbances.py`, and `runtime.py`. Screening does not edit
these files. A mismatching source hash stops before any output or native trial.
Seeds 0-19 informed earlier development; this batch uses fresh
seeds. No parameters are tuned during the batch. These are still synthetic pose
perturbations on one task, not a physical realism or embodiment benchmark.

## Runner and meaning of completion

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.acceptance --screening \
    --output /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m2-screening \
    --archive /home/jiangle/aura-work/aether-cl-m2-screening-seeds20-39.tar.gz
```

Screening retains the existing fresh-process execution, identical captured
startup environments, bounded interruption/cleanup, and hashed archive. Each
cell is one fresh process containing 20 seeded resets. The archive root is
`screening/`; child stdout/stderr, manifests, events, episode results, metrics,
suite checks, and source hashes are retained. Existing archives are not replaced.

Integrity checks require clean revisions, complete original seed lists and
episode indices, every eligible episode's full action budget, zero actions for
exclusions, matching step-log lengths/sequences, correct eligible denominators
and task rates, scheduled interventions per eligible episode, and verification
step accounting. Paired canonical traces/software/policy/task rules must match.
Reset `info` is omitted but full reset observations are compared; the verifier
ignores all reset contact flags. Trace definitions are unchanged from acceptance.

`state: passed` means complete valid paired evidence. It does not mean all tasks
succeeded or all diagnoses were correct. Task failures, false alarms, uncertain
observations, and unexpected labels remain measured outcomes. Exclusions are
reported and never replaced. If integrity checks fail, all available data are
still archived for inspection and exit status is 2. An all-excluded cell cannot
pass completeness screening; its task rate remains null. The suite's local
receipt adds the final archive hash after creation.

## Analysis before recovery

Review eligible episode success per condition/system, exclusion counts and
reasons, per-episode first failures and detection latency, and dense agreement
metrics with uncertainty/coverage. Twenty matched seed pairs per condition are
the episode-level evidence; thousands of adjacent frames are not independent
failure tests. Passive V1 has identical actions and task rules, so it should not
improve task success. Any difference needs investigation before recovery.

All 58 local tests passed. Six new tests cover the 120-episode frozen fixture
matrix, original seed lists, eligible denominators with exclusions, measured
natural policy failure, corrupted seed/denominator rejection, and precise reset
comparison metadata, and rejection of changed frozen source hashes. Fixtures
validate data flow rather than native physics.

After reviewing the native batch, retain the policy/task/budget and verifier
settings for M3 bounded recovery. Recovery will consume observed state and
verifier outputs rather than disturbance identity or simulator reference labels.
Its retries/actions/cost and final outcomes will be logged against the same
baseline/V1 conditions. Prototype A findings return to 02.


## Native results and audit

Uploaded archive `aether-cl-m2-screening-seeds20-39.tar.gz`:
SHA-256 `182d9728cea439b84e6f7517a7dd829db91fc7687f940f00c998d867b8f16f16`.
All 31 indexed file sizes/hashes and the exact archive member set match.
Clean revision `472dfbaf75131d8a9b77cef21fa53435bf8e32e0` completed all 120
requested episodes and 43,200 actions, with no exclusions or execution errors.
All four frozen source hashes match. Raw replay reproduces every reference and
verifier result; policy action replay differs by at most 2.98e-8 due to the
known float32 Panda base pose. Episode summaries and child stdout/results agree.

| Condition | Baseline final task success | V1 final task success | V1 first diagnosis |
| --- | --- | --- | --- |
| Normal | 20/20 | 20/20 | No failures or false alarms |
| Object shift | 0/20 | 0/20 | GRASP_FAILURE, 20/20 |
| Object drop | 0/20 | 0/20 | OBJECT_LOST, 20/20 |

Every detected first failure followed its simulator reference by two control
steps. There were no uncertain observations or false alarms. Dense failure
recall was 0.991525 for shift and 0.988889 for drop, accounting for the two-step
detection delay per episode. Diagnosis agreement on detected positive frames
was 1.0. These are simulator-reference agreement measures, not perception
accuracy, and the correlated frames are not thousands of independent tests.

All three baseline/V1 canonical traces and startup software/policy/task
contracts are exactly equal. Passive verification changes no actions and does
not improve task success. Drop seed 33 temporarily satisfied the environment's
looser success flag at steps 133-137, before injection; it never satisfied the
strict grasp/lift/static task. Its final task outcome remains a failure.

The [compact audit](evidence/AETHER_CL_M2_Fresh_Seed_Audit.json) preserves cell
metrics, trace hashes, first-failure latencies, and this transient exception.
The evidence supports adding bounded recovery while retaining the frozen M2
policy, verifier, disturbances, and final task/budget. M3 native recovery
success remains a separate experiment.
