# AETHER-CL M3 Frozen Fresh-Seed Recovery Screening

Date: 2026-10-05 (Asia/Shanghai)

Status: protocol frozen and runner prepared before native fresh-seed execution.
The native batch completed but its recovery comparison was rejected; see the
[audit and episode-isolation amendment](AETHER_CL_M3_Isolated_Screening.md).
That separate correction replication now passes native trial and strict paired
checks on the same selected seeds. This original batch remains rejected;
its source, protocol and failed archive are preserved.
The original protocol below remains preserved. This is a bounded single-task screening experiment,
not the full Prototype A benchmark or a robustness curve.

## Prerequisite and operator observation

Corrected M3 seed-0 acceptance on clean `2d1c063` passes all nine trial and
four paired checks. Raw audit verifies all 3,240 actions and file hashes;
normal succeeds for all systems, and shift/drop fail for baseline/V1 but
succeed for V2 within the same total action budget. See
[the corrected audit](evidence/AETHER_CL_M3_Corrected_Native_Audit.json).

The operator reports observing the live shifted-cube run: the controller
located the relocated cube, regrasped it and transported it to the green goal.
They also observed slow staged motions and an initial unnecessary empty grasp.
This is a visual operator observation, not a new raw-log audit. Rendered drop
inspection remains pending. The baseline's cached target/timed closure explains
why it still closes before the late grasp checkpoint; M3 interrupts from the
confirmed diagnosis. These design limits are preserved for causal comparison.

The viewer was paced at five displayed control steps per wall-clock second.
This deliberate pacing adds delay; it is not evidence of model reasoning
latency. The controller is rule based. Simulation-time steps and motion
limits remain fixed. Optimizing the policy during this comparison would change
the baseline and require a separate experiment.

## Frozen matrix

| Setting | Value |
| --- | --- |
| Reset seeds | 40–59 inclusive, original order, no replacement |
| Systems | Baseline; passive V1; verification + bounded recovery V2 |
| Conditions | Normal; object shift; object drop |
| Requested episodes | 20 per cell; nine cells; 180 total |
| Shared budget | 360 actions per eligible episode |
| Disturbance | 0.12 m world-y relocation before action result 81/181 |
| Task | PickCube-v1; lifted held cube, fresh contact grasp, static goal persistence |
| Observations | Privileged simulator state; no camera perception |
| Physics/render | CPU physics; no rendering during batch |
| Retry | One attempt, at most min(230, remaining episode actions) |

Seeds 0–19 informed earlier baseline development; 20–39 were already used for
M2 screening. Seeds 40–59 are selected here before running any M3 native
fresh-seed trial. No parameters are tuned during this batch. Results apply to
these matched resets of this scene and disturbance magnitude.

The [machine-readable protocol](evidence/AETHER_CL_M3_Frozen_Screening_Protocol.json)
records all settings and SHA-256 of eight accepted source files: policy,
verifier, disturbance, M2 runtime, recovery, M3 runtime, M3 entry point, and
subprocess/archive helper. The runner checks all hashes and exact committed
protocol/settings before making an output directory or launching a child.
All eight remain byte-identical to accepted `2d1c063`. The new screening code
and documents do not change execution or physics.

## Evidence checks and causal comparisons

Each cell runs in a fresh Python process using the same captured startup
environment. Each process performs the original 20 resets in seed order.
The archive includes the protocol, suite, raw manifests/events/results,
child stdout/stderr, and every file's size/SHA-256. The archive is created
exclusively; existing evidence is never replaced. Errors or Ctrl+C retain
available evidence in a failed/interrupted archive. Exit 0 means valid evidence;
exit 2 means an integrity failure or interruption.

Cell checks enforce exact configurations, clean revisions, requested seeds,
episode indices, eligible full budgets, zero-action exclusions, log/summary
consistency, task denominators, scheduled relocation geometry and ordering.
Reference/verifier verdicts, first-failure summaries, latencies and dense
agreement metrics are replayed from the observations and evaluator info.
V2 additionally checks trigger timing from the preceding first confirmed
verdict, one-attempt/remaining-budget limits, action counts, transport gates,
observed TCP path costs, final recovery snapshots and task success, and
unchanged command holding after completion/abort. Recovery metric denominators
and costs are recomputed from eligible episodes, including unsuccessful attempts.

For each condition, baseline and V1 must have exact full canonical traces and
software/policy/task equality. V1 and V2 must share the full reset observation
and eligibility, software/policy/task/verifier/disturbance rules, and every
canonical step and verdict through the first recovery intervention. If V2
never intervenes, its entire trace must match V1. No normal-success assumption
is imposed: a natural failure can trigger recovery in an unperturbed episode.

Injection poses must match before an intervention. If natural recovery starts
before the scheduled disturbance, later poses may legitimately differ because
V2 has already changed the trajectory. The scheduled step/magnitude/mechanism
and within-cell relocation checks still apply. Such later pose differences are
not treated as a broken paired experiment.

Exclusions remain in all original lists and are not resampled. An all-excluded
cell cannot pass the screening's requirement for eligible evidence, and its
task rate remains null. False alarms, uncertainty, natural policy failures,
missed diagnoses, unsupported/late diagnoses, failed retries and aborts are
measured outcomes, not grounds to discard an episode or force a retry to pass.

## Prespecified analysis

Primary comparison is episode-level final task success, V2 versus V1 for each
condition. The suite records counts for both failing, only V2 succeeding,
only V1 succeeding, and both succeeding, plus the matched success-rate
difference. Normal-condition regressions are retained. Baseline/V1 equality
provides the passive-verification control.

Report eligible/excluded counts, first failure categories and diagnosis latency,
no-failure false alarms and uncertainty coverage, conditional recovery success
among attempted episodes, abort/decline reasons, and retry actions/TCP path.
Include failed attempts in cost summaries. Conditional recovery success alone
cannot substitute for the matched final-task comparison: diagnosis/attempt
selection can change its denominator. Dense frame agreement is correlated and
is not thousands of independent failure trials. Twenty seeds reused across
conditions are not 180 independent scene samples.

Do not increase budgets, replace seeds, tune thresholds, or hide unsuccessful
cells after seeing results. Any later optimization uses a new protocol and fresh
seeds, while retaining this batch and its reasons. A broader disturbance-magnitude
sweep and other task types are subsequent work; this one-magnitude screening
cannot supply the required final robustness curve.

## Running and next live inspection

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.m3_screening \
    --output runs/m3-screening-seeds40-59 \
    --archive /home/jiangle/aura-work/aether-cl-m3-screening-seeds40-59.tar.gz
```

This command is a nonrendered measurement batch and does not open a viewer.
After it finishes, inspect live V2 drop on the A100 using `aether_cl.m3 --live`
and port 8765. It publishes the initial preview and waits for Enter before
movement. Batch outcomes require raw-log review before any broader claims or
new policy/scene changes. Findings return to 02.

## Local validation

The existing 78 tests and ten new screening regressions pass: an 87-test full
run plus the subsequently added missing-TCP regression. The screening fixture
executes all 180 requested episodes and verifies exact cell configuration,
seed order, paired outcomes and every archived hash. Other cases cover natural
normal-condition failure, failed retries, exclusions/null attempt rates,
corrupt costs/budgets/transport evidence, pretrigger action changes, source or
protocol drift, errors/interruption, early natural recovery before a later
injection, unsupported diagnoses, and missing sensors/uncertainty.

The final screening checks also pass all nine existing native pilot cells and
three V1/V2 causal comparisons, including replay and cost validation. This
reuses existing native evidence; it does not run new seeds in native physics.
Python 3.10 syntax and CLI help are checked. Fixtures do not validate new native
contacts, physics, rendering, or fresh-seed success.
