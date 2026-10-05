# AETHER-CL M4 Frozen Magnitude Robustness Sweep

Date: 2026-10-05 (Asia/Shanghai)

Status: implementation/preregistration prepared and all 98 local tests pass.
Native M4 results are pending. This extends Prototype A evaluation; no policy
or recovery tuning.

## Question and accepted basis

How does the fixed nominal policy, passive verification and bounded recovery
perform as the scripted disturbance magnitude increases? Where, within the
tested range, do recovery completion and costs deteriorate?

The [accepted M3 isolation replication](AETHER_CL_M3_Isolated_Screening.md#corrected-native-results)
verified all 180 trial checks and strict pairs on the original selected seeds.
Normal success was 19/19 per system, shifted/drop baseline/V1 0/19, and V2
19/19 for both. These same-seed correction results motivate a new protocol,
not additional tuning on the accepted sample. Original failures are retained.

## Frozen matrix

New preselected native seeds: **60–79**, used for every point/system. There is
no adaptive seed selection or replacement. Unit fixtures do not observe these
native simulator resets. All systems retain the accepted M3 configuration.

| Point family | Magnitudes | Injection | Systems | Selected trials |
| --- | --- | --- | --- | --- |
| Normal | No injection | None | Baseline / V1 / V2 | 60 |
| Object shift | 2, 4, 8, 12, 20 cm | World-Y relocation before step 81 | Baseline / V1 / V2 | 300 |
| Object drop | 2, 4, 8, 12, 20 cm | Initial cube height plus World-Y relocation before step 181 | Baseline / V1 / V2 | 300 |

Total: **660 selected one-episode native children**, 33 system/point cells,
220 baseline/V1 full pairs, 220 V1/V2 causal pairs and 200 normal-baseline
versus disturbed-baseline pre-injection controls. Each eligible episode has
360 actions, so 237,600 actions is the maximum before exclusions/errors.
There are 20 distinct seeds, not 660 independent initial scenes. The same
seeds across magnitudes provide matched comparisons; dense frames and these
repeated conditions are correlated.

The existing runtime permits 0.02–0.20 m magnitudes. M4 stays within that
range and leaves its validation unchanged. The 12 cm point is an anchor on new
seeds. If no recovery failure occurs up to 20 cm, report that limited result;
do not extrapolate a failure threshold or claim unrestricted robustness.

Normal is a separate no-injection control. Its native config retains the
unused 0.12 m field because the frozen config rejects zero. The report gives
its actual magnitude as null. It must not be plotted as a zero-displacement
drop: dropping also changes height, even without a horizontal shift.

The [machine protocol](evidence/AETHER_CL_M4_Robustness_Protocol.json) freezes
the matrix, order, scoring, settings, ten accepted execution/helper hashes and
the new runner's hash. Both earlier protocols and hashes are checked too.
All are verified before output/launch and before each new trial. Controller,
verifier, physics, task tolerance, budgets, timestamps and injection direction
stay unchanged. M4 uses the existing `aether_cl.m3` child CLI. Manifest purpose
and schema remain M3 execution; the parent records M4 evaluation scope.

## Isolation and fair comparisons

Order: normal, ascending shift magnitudes, ascending drop magnitudes; inside
each point, seed 60–79 and baseline/V1/V2. Every child is a fresh interpreter
and fresh simulator with exactly one reset. GPU 1 stays process-local cuda:0;
CPU physics and state observations remain unchanged. There is no rendering
or wall-clock viewer pacing in the measurement batch.

Full reset observations remain strict, including grasp flags. Baseline/V1
full action/state/reference traces must match exactly. V1/V2 reset, verifier
and action/state prefixes must match through the first recovery trigger, or
for the whole run if no intervention occurs. Preintervention injections must
also match. Each disturbed baseline must match the same-seed normal baseline
reset and trace through step 80 for shift or 180 for drop. This additional
control verifies that magnitude comparisons start from identical trajectories.

The unchanged episode checker replays shared task/reference/verifier metrics,
injection geometry/order, first diagnosis/latency, recovery trigger/gates,
budgets, terminal holding, snapshots and TCP path cost. Native manifests must
also match the parent suite's complete recorded software/startup contract.
A passing suite means comparable complete evidence, not successful recovery.

## Outcomes and curve

`suite.json` records every selected trial and paired/control check. `curve.csv`
contains 33 cell rows with magnitude, system, completeness/comparison validity,
eligible denominators, task success, attempts, conditional recovery success,
action/path costs and final distance. `validated_curve_success_rate` is null
unless the point's triplets and controls are complete and valid. Individual
task rates are descriptive evidence; they do not override failed comparisons.

Cell JSON additionally records aborted attempts/declines, first failure
categories/latencies and aggregated confusion counts, detection precision/
recall, diagnosis agreement and uncertainty/coverage. Counts aggregate raw
reference agreement, not independent perception accuracy. Failed attempts
contribute to costs. Zero attempts produce null conditional metrics. Errors
and incomplete cells produce null rates; no unavailable outcomes are invented.

Matched V1/V2 counts distinguish both failed, recovery-only success,
passive-only success and both succeeded. Invalid/incomplete pairs have a null
paired effect. Normal failures and recovery regressions remain outcomes;
they are not filtered or used to pick new seeds. Reset ineligibility is logged
with zero actions and remains present in every relevant denominator table.

The archived raw dataset supports a later externally audited robustness plot.
Do not treat correlated per-step detection counts as hundreds of thousands
of independent trials. No final curve or scientific result exists before the
native data has been uploaded and audited.

## Long runs and continuation

Use a fixed new study directory, an archive outside it and the isolated
`aether-cl` environment. The runner uses an OS-held study lock to prevent two
writers. First launch refuses an existing study/archive. Launch it through
`nohup` so SSH disconnection does not stop the experiment. The final archive
includes all raw logs, recorded file hashes, protocol, report and CSV.

`--stop-after N` pauses gracefully after N new trials and produces a uniquely
named partial archive. `--resume` with the same output/final archive verifies
protocol, source, recorded software, normalized startup environment, original
trial order/configs and every prior raw hash; completed checks replay again.
It continues only unstarted slots. It never reruns failed/interrupted slots,
changes a seed or overwrites an earlier raw file/archive. A child interrupted
midtrial stays invalid, so continuation cannot turn it into accepted evidence.
An unfinished checkpoint after abrupt process termination fails closed.

Only ephemeral SSH/terminal/shell keys listed in the protocol are removed
from the child environment. Every child in a session receives the same
captured normalized environment. Its complete digest is stored, rather than
the contents of possibly sensitive environment variables; continuation must
match that digest. The native library, CUDA, package and source settings
remain checked. Older partial archives retain their original indices/hashes;
only the generated working archive index is refreshed for the next snapshot.

Keep this repository revision unchanged until the batch finishes. Changing
Git revision, libraries or environment during continuation is rejected.
Native results are pending; no extra packages or 4090 are required.

### First launch on the server

After transferring the published bundle and updating to the exact supplied
revision, the operator commands first run three selected native trials with
`--stop-after 3`, check their integrity, then start the same study in the
background with `--resume`. Those first three remain part of the 660 selected
trials; they are not extra samples or tuning data. The direct background
first-launch command is:

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
nohup /home/jiangle/miniconda3/envs/aether-cl/bin/python -u -m aether_cl.m4_robustness \
    --output /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m4-robustness-seeds60-79 \
    --archive /home/jiangle/aura-work/aether-cl-m4-robustness-seeds60-79.tar.gz \
    > /home/jiangle/aura-work/aether-cl-m4-robustness-seeds60-79.log 2>&1 < /dev/null &
```

Watch progress with `tail -f` on that full log path. Ctrl+C in the log viewer
stops only that viewer. This batch does not open a browser. Live viewing is
launched separately with the existing preview/Enter gate after selecting a
useful case from the audited curve.

### Continue a gracefully paused study on the server

Run only after the original process has exited and no final archive exists:

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
nohup /home/jiangle/miniconda3/envs/aether-cl/bin/python -u -m aether_cl.m4_robustness \
    --resume \
    --output /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m4-robustness-seeds60-79 \
    --archive /home/jiangle/aura-work/aether-cl-m4-robustness-seeds60-79.tar.gz \
    >> /home/jiangle/aura-work/aether-cl-m4-robustness-seeds60-79.log 2>&1 < /dev/null &
```

## Local validation

All 98 tests pass (143.703 seconds), including the six M4 tests. The complete
660-slot wiring fixture verifies exact magnitudes/order/configuration, one
episode per fresh child call, identical normalized startup environments,
pause/continue without rerunning slots, all 33 cells/640 comparisons, excluded
seeds and failed-retry costs, CSV rows and every final/partial archive hash.
Earlier partial archives remain byte-identical and their index is not
duplicated during continuation. Error/interruption slots stay invalid on
continuation; partial rates/effects remain null.

Separate tests reject changed protocol/source/environment, raw tampering and
competing writers. Thirteen actual runtime fixture episodes cover both small
and large shift/drop magnitudes, three systems, strict episode replay and
normal-control prefixes; a deliberate pre-injection observation change is
rejected. Aggregated diagnosis counts are independently checked against
VerificationMetrics with misdiagnoses, uncertainty and incomplete rates.
Python 3.10 grammar, CLI help, exact protocol/source guards and documentation
links verify. Fixtures do not validate native contacts or produce M4 findings.

## Scope and next decisions

This is a finite synthetic magnitude curve on one held-cube target-reaching
task with privileged observations. It is not force-disturbance validation,
camera perception, release/support placement, insertion, embodiment transfer
or full AETHER. After audit, compare failure modes and cost trends, select
live cases, and return findings to 02. Motion speed/precision variants or more
realistic task/perception protocols remain separate subsequent experiments.
