# AETHER-CL M2 Frozen Fresh-Seed Screening

Date: 2026-10-05 (Asia/Shanghai)

Status: protocol frozen and runner tested locally; native results pending.

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
