# AETHER CL Prototype A

This directory implements environment smoke tests, a fixed PickCube controller,
**M2 passive verification**, and **M3 bounded recovery** for AETHER-CL v0.1.
Smoke mode runs seeded random actions; fixed mode attempts grasping and transport
using simulator state and a timed sequence. M1 native baseline screening is
complete. M2 seed-0 native acceptance is complete: all six behavior checks,
paired traces, and startup environments pass after process isolation. Frozen
fresh-seed screening is complete and audited. M3 recovery is implemented and
locally tested. Corrected seed-0 native acceptance is complete and audited;
live shifted-cube recovery was observed by the operator. The original reused-
environment screening remains rejected. Its per-episode isolation correction
is now natively executed and audited: all 180 trial checks, 60 passive pairs and
60 recovery pairs pass. Normal success is 19/19 per system; shift/drop success
is 0/19 for baseline/V1 and 19/19 for V2. Seed 58 remains excluded throughout.
This replicates the original preselected seeds, rather than adding unseen seeds.

M4's [frozen magnitude sweep](../../docs/research/experiments/AETHER_CL_M4_Robustness.md#audited-native-results)
is complete and audited on new seeds 60–79: all 660 trial checks, 237,600 actions
and 640 strict paired/control comparisons pass, with no exclusions. V2 achieves
20/20 final task success at every tested point, rescuing 180 paired V1 failures.
Baseline/V1 succeeds on normal and 2 cm shift; it fails on larger shifts and all
drops. Of 180 retries, 178 complete and two 20 cm drop retries exhaust their hold
budget after already attaining task success. Costs rise with magnitude; recovery
precision remains around a centimetre. The [audited curve and paused live commands](../../docs/research/experiments/AETHER_CL_M4_Robustness.md)
keep task success separate from retry completion. The batch and live viewer run
separately. All scientific execution sources and preregistered scoring remain
unchanged.

Prototype A will test whether explicit verification and bounded recovery improve
manipulation autonomy under disturbances while keeping the manipulation policy
fixed. Its findings return to branch 02 for AETHER architecture research.

## Current engineering round — M5

**06-01 is active again for M5 Verification-Gating Attribution only.**
[02's review](../../docs/research/experiments/AETHER_CL_02_Research_Review_v0.1.md)
and DEC-0003 accept M0–M4 within scope and require a scheduled V3 control before
broader Prototype A expansion. The [M5 plan](../../docs/research/experiments/AETHER_CL_M5_Attribution.md)
freezes first retry actions at 128/184 in separate shift/drop families, with
corresponding normal controls and fresh seeds 80–99: 960 isolated trials.
Baseline/V1/V2 and all prior scientific sources remain unchanged. V3 reuses
recovery execution without consuming verifier/failure output. Implementation
and preregistration are prepared; native outcomes remain pending.

The [earlier return-to-02 handoff](../../docs/research/experiments/AETHER_CL_06_01_Return_to_02.md)
closed only M0–M4; it is historical, not the current chat status. Prototype A
remains open and the PR stays draft/unmerged. After audited M5, return to 02
again before further implementation. Motion, new tasks, perception and 02W
are not authorized in M5.

## Current milestone

- A single `PickCube-v1` environment, Panda arm, CPU physics, state observations.
- GPU offscreen raster rendering, with the render device chosen explicitly.
- Finite episodes with deterministic reset/action seeds and step limits.
- A read-only browser viewer bound to `127.0.0.1:8765`.
- Run metadata, action/observation events, episode results, and the latest frame.
- Opt-in M2 task rules, passive verification, diagnosis, and cube shift/drop tests.
- M3 baseline/V1/V2 runs with one bounded observed-state recovery attempt.

`PickCube-v1` tests reaching a goal with the cube and a static robot. It does not
require releasing the cube onto a support surface. Use it as an infrastructure
smoke test; the research pick-and-place task needs an explicit placement/release
condition before policy evaluation.

The red cube is the manipulated object. The green sphere is a noncolliding
target marker, sampled at each reset and fixed during the episode. It may float
above the table or overlap the robot in the camera image. The random controller
does not attempt to reach it. Basic A100 rendering and live browser display were
confirmed by user-provided output/screenshots on 2026-10-05; see the experiment
log for the evidence and limits.

## Fixed controller candidate (Milestone 1)

The controller reads the initial cube pose and goal from simulator state, then
executes approach (60 steps), descend (40), close (25), lift (45), transport (60),
lower (40), and hold (50). Phase changes depend only on elapsed control steps.
It caches the initial cube/goal and uses current TCP pose only for low-level
Cartesian servoing. It does not consume evaluator success or grasp flags,
retry, observe again, or change its task sequence when the grasp fails.

The Panda uses `pd_ee_pose`: absolute translation and intrinsic XYZ Euler angles
in the robot base frame, plus normalized gripper control. This is a scripted
**privileged-state baseline**, not a learned policy or a perception result.
Its NumPy/SciPy dependencies already exist in the copied environment. No new
wheel download is needed for this increment.

After activating `aether-cl` and supplying the private OpenGL setting if needed,
expose only the selected physical GPU. ManiSkill documents that visible GPU 1
then becomes process-local `cuda:0`:

```bash
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.baseline --render-device cuda:0 --episodes 5 --seed 0 --max-steps 360 --output runs/baseline
```

Inspect one episode in the viewer first:

```bash
python -m aether_cl.viewer --controller fixed_pick_cube --render-device cuda:0 --episodes 1 --seed 0 --max-steps 360 --fps 10 --port 8765 --output runs/baseline-live
```

The viewer shows the current phase, ground-truth cube-to-target distance, and
environment success flag. Red is the object; green is its goal marker. These
displayed diagnostics do not feed the policy. The run's `result.json` reports
final-step and any-step success rates separately; interrupted runs have null
aggregate success rates. `state: finished` means execution finished, not that
the cube reached its goal.

The 320-step sequence requires `--max-steps` at least 320; 360 leaves extra hold
time. Runtime errors remain errors rather than failed-task episode scores.
Controller settings and input boundaries are saved in `manifest.json`, and
every action logs its phase and expected/commanded TCP positions. The native M1
screening reported 20/20 environment successes, including one already-solved
reset; the other 19 episodes grasped and lifted. The current controller is
retained as the nominal baseline. See [the M1 protocol](../../docs/research/experiments/AETHER_CL_M1_Fixed_Controller.md)
and [raw-log audit](../../docs/research/experiments/AETHER_CL_M1_Baseline_Screening.md).

## Passive verification (Milestone 2)

M2 adds a state-based verifier and two controlled interventions while retaining
the exact M1 controller implementation/settings. The verifier reports outcomes
without changing actions, stage progression, or the action budget. Recovery is
not active. A passive verifier is expected to improve failure visibility; it
cannot improve task success if actions and termination rules remain identical.

Both M2 baseline and V1 use the same revised task contract: exclude resets where
the cube already lies within 0.025 m of its goal, run the full 360-step budget
despite intermediate environment success, require at least 0.05 m cube lift,
and require a fresh contact grasp plus five consecutive static goal observations
at the episode end. Exclusions stay in the logs with a reason; task-rate
denominators include eligible episodes only. Release is not required. These
stricter results must not be compared directly with the old M1 success rates.

The verifier consumes post-action cube/TCP/goal geometry and Panda joint
position/velocity, ignoring reset grasp flags and all evaluator/contact info.
It checks deadlines for grasp (125), lift (170), and target arrival (320), with
three-step failure persistence. Final failure checks need no additional budget.
Its labels are `GRASP_FAILURE`, `OBJECT_LOST`, `TARGET_NOT_REACHED`,
`STATE_MISMATCH`, and `UNCERTAIN`; confidence is explicitly uncalibrated.
The separate simulator reference supplies contact-based task/failure labels for
agreement metrics. This is privileged-state engineering evaluation, not visual
perception accuracy.

`object_shift` relocates the cube along world y before action 81; `object_drop`
relocates it along world y and to its initial height before action 181. Default
displacement is 0.12 m. These are one-time pose interventions, not physical push
models. Orientation is preserved and velocities are zeroed. Timing, magnitude,
and before/after poses are logged. The user-supplied native shift run detected
`GRASP_FAILURE` with a two-step persistence delay. Its sudden sideways jump is
scripted relocation, not a simulated physical push. Raw events now confirm that
the cube stayed within 1.3 micrometres of the injected position afterward.
No extra packages or system changes are needed.

Example batch commands after environment activation:

```bash
python -m aether_cl.experiment --system baseline --no-render --episodes 20 --seed 20 --max-steps 360 --disturbance object_shift --output runs/m2-baseline-shift
python -m aether_cl.experiment --system v1 --no-render --episodes 20 --seed 20 --max-steps 360 --disturbance object_shift --output runs/m2-v1-shift
```

For native acceptance, inspect a live seed-0 trial first:

```bash
python -m aether_cl.viewer --controller fixed_pick_cube --protocol m2 --verification --disturbance object_shift --render-device cuda:0 --episodes 1 --seed 0 --max-steps 360 --fps 10 --port 8765 --output runs/m2-v1-live
```

The browser shows environment success, separate M2 task success, verification,
failure diagnosis, and intervention status. The final result includes eligible
task rates, first reference/detected failure steps, conditional diagnosis latency,
and step-level detection/diagnosis agreement counts. Missing denominators and
incomplete-run rates are null; uncertainty and coverage are explicit.

Forty local tests passed, including action equality between baseline/V1 under
all three conditions, budget/denominator/cleanup handling, freshness, uncertainty,
and checkpoint logic. Replaying the verifier on 4,038 eligible M1 normal-state
observations produced no alarms; those old episodes ended early and cannot
validate the new full-horizon success contract. See [the M2 protocol](../../docs/research/experiments/AETHER_CL_M2_Verification.md).

### Matched native acceptance and evidence collection

The acceptance runner executes six seed-0, 360-action, nonrendered trials:
normal/shift/drop, each with policy-only baseline and passive V1. It checks the
expected task/detection outcomes and compares reset geometry, every action,
post-action observation, controller decision, simulator info, reference, and
intervention record between each pair. Reset `info` is omitted, while the full
reset observation remains compared, including its raw `extra.is_grasped` flag.
The verifier does not consume reset contact flags from either location.
It also requires recorded clean revisions and matching software/policy/task
contracts. Exact equality is a check to perform, not an assumed native result.

```bash
python -m aether_cl.acceptance --output runs/m2-acceptance
```

The printed archive includes manifests, raw events, results, suite checks, and
file hashes. `--live-run /absolute/path/to/prior/run` adds the earlier rendered
trial; `--archive /absolute/path/to/evidence.tar.gz` sets the transfer filename.
Existing archives are never overwritten. Execution errors or Ctrl+C produce a
failed/interrupted report and retain available evidence; exit status is 2.
A failed task in a disturbed trial can be an expected outcome, while an
execution error cannot count as acceptance. An excluded reset cannot pass and
is never replaced with a different seed.

The original 48 local tests passed, including eight acceptance-runner checks for trace
drift, wrong outcomes, errors, interruption, exclusions, dirty revisions, archive
hashes, and missing evidence. These tests use state-flow fixtures, not native
physics. See [the acceptance procedure](../../docs/research/experiments/AETHER_CL_M2_Acceptance.md)
for the interpretation and next-stage gate. The fixed policy, verifier,
disturbances, and runtime are unchanged by this runner.

The [first native raw-log audit](../../docs/research/experiments/AETHER_CL_M2_Native_Screening.md)
confirmed all six expected outcomes and three exact pair traces, but the original
suite remains `failed`: importing OpenCV during the first trial modified the
process's `LD_LIBRARY_PATH`, so the second manifest had different startup values.
The runner now starts a fresh Python interpreter for each cell from the same
captured suite-start environment and retains child stdout/stderr in the archive.
It signals and joins the active child on Ctrl+C before archiving. Library-path
equality stays strict. All 52 local tests passed, including fresh-process
isolation, nonzero child exits, interrupt cleanup, and rejection of real library
environment differences. This prompted a native rerun with a new archive;
the prior failed archive is preserved. The isolated rerun has now been audited:
all 35 indexed hashes, six expected native outcomes, and three paired traces
pass, with identical startup software records. M2 seed-0 development acceptance
is complete; this does not establish broad robustness.

### Frozen fresh-seed screening

```bash
python -m aether_cl.acceptance --screening --output runs/m2-screening
```

This fixes seeds 20-39, 20 episodes per cell, normal/shift/drop baseline/V1,
360 actions per eligible episode, and 0.12 m perturbations: 120 requested
episodes across 20 unique reset seeds. Policy, task rules, verifier thresholds,
runtime, and disturbances remain frozen. Accepted source hashes are enforced
before any trial. Each cell
uses a fresh process with the same startup environment.

Screening checks data integrity, full budgets, original seed order, exclusions,
eligible-only denominators, and paired traces. Task failures, false alarms,
uncertainty, and unexpected diagnoses remain measured outcomes rather than
automatic rejection of evidence. `state: passed` means valid paired evidence,
not perfect manipulation/detection. Existing raw metrics and all per-episode
records are archived. There is no resampling or threshold tuning on these seeds.
See [the frozen screening plan](../../docs/research/experiments/AETHER_CL_M2_Frozen_Screening.md).
All 58 M2 local tests passed, including seed coverage, measured policy failure,
exclusions, denominator checks, and precise reset-comparison metadata. Native
screening completed all 120 episodes without exclusions: normal 20/20 success
per system, shift/drop 0/20, all first failures identified after two steps.
All paired canonical traces and startup contracts match exactly.

## Offline deployment through a connected laptop

The target server cannot reliably retrieve GitHub and package downloads. Use a
connected laptop for downloading and transfer the Git repository and wheels over
SSH. The laptop does not need to run the simulator.

The current offline path starts from a separate copy of the existing
`robotwin-sim` environment. The confirmed copy uses Python 3.10.22,
PyTorch 2.4.1+cu121, and NumPy 1.26.4. Clone with Conda's `--offline --copy`
options into `aether-cl`; never install into the original environment.

`requirements-offline.txt` is an **incremental wheel set for that copied
environment**, not a complete environment lock. It includes the missing and
changed simulator dependencies, including ManiSkill's Linux-only mplib pin.
Existing compatible packages, PyTorch, and CUDA libraries are reused. A
different starting environment may need additional wheels; the server dry run
must resolve successfully before installation.

On the connected laptop, from this directory:

```powershell
py -3 scripts/download_offline.py --output C:\Workspace\AURA-Deploy\aether-wheelhouse --archive C:\Workspace\AURA-Deploy\aether-wheels-cp310-linux.tar
```

The script downloads explicitly pinned Linux x86_64 / CPython 3.10 or portable
wheels, creates a SHA-256 manifest, and archives the selected wheels. It installs
nothing. `--no-deps` is used only for downloading the reviewed incremental list;
the server install performs normal dependency resolution.

Transfer the archive with `scp -P SSH_PORT`, alongside a Git bundle made with
`git bundle create PATH --all`. On the server, clone from the uploaded bundle or
fetch the branch from it and merge with `--ff-only`. No server GitHub connection
is needed. Extract the wheel archive into its own directory and activate
`aether-cl`, then run:

```bash
python scripts/install_offline.py --wheelhouse /absolute/path/to/extracted/wheels
```

The installer checks the environment identity, core package versions, and wheel
checksums. It uses `--no-index` and performs a dry run before changing packages.
It replaces the copied `opencv-python-headless` with the pinned `opencv-python`
required by SAPIEN, so only one distribution supplies `cv2`. It then installs the
incremental pins, runs `pip check`, and saves the resulting package inventory.
Native imports, physics stepping, and camera rendering still need server checks.
If a later installation step fails, inspect the copied environment before retrying;
installation is not an atomic transaction.

Do not use `scripts/setup.sh` on this network-restricted server: it is the
alternative online installation path described below.

## Alternative online server environment

Initial target: Ubuntu 22.04 and the available A100 server. The existing
`robotwin-sim` and `lingbotvla` environments are useful references but have
different dependencies. The following commands create a separate environment.

From an SSH terminal, enter the repository and this directory, then run:

```bash
bash scripts/setup.sh
conda activate aether-cl
```

The setup script stops on failure and refuses to reuse an existing `aether-cl`
environment. It activates and checks the new environment before installing
packages. If `aether-cl` already exists, inspect it before reusing it. SAPIEN 3.0.3 satisfies ManiSkill 3.0.1's Linux
requirement `sapien>=3.0.0`; RoboTwin's SAPIEN 3.0.0b1 does not.

These pin the main runtime packages, not every transitive dependency. Record the
installed environment after successful resolution. The setup script writes
`runs/installed-packages.txt` for that purpose.

## Separate physics and rendering checks

First run a short test without camera capture:

```bash
python -m aether_cl.smoke --no-render --max-steps 5 --output runs/physics
```

Then test offscreen rendering on an available GPU:

```bash
nvidia-smi
python -m aether_cl.smoke --render-device cuda:1 --max-steps 5 --output runs/render
```

`cuda:1` is an explicit example for this server, not a reserved GPU. Check
availability and any local allocation rules before running. Device numbering can
change when `CUDA_VISIBLE_DEVICES` is set. The run log records the selected
SAPIEN render device and visibility setting. This milestone uses CPU physics;
GPU physics and multi-GPU execution are not required.

Success means the command exits successfully and writes `result.json` with
`state: finished`. The rendering test must also produce a nonconstant
`latest.jpg`. Random actions usually do not complete the task; an environment
success flag of false is not a smoke-test failure.

This skips frame capture, not every graphics dependency: ManiSkill's task
construction can create SAPIEN render materials even when camera rendering is
disabled. A failure during scene construction must be distinguished from a
failure while capturing a camera frame.

If stepping works but camera capture fails, preserve the complete traceback and inspect
the Vulkan/renderer configuration before changing simulator or hardware. A
missing `vulkaninfo` utility does not establish whether Vulkan rendering works.
No system driver changes are performed by these commands.

### Process-scoped OpenGL workaround observed on the target server

The copied environment's standard OpenCV initially failed with
`libGL.so.1: undefined symbol: _glapi_tls_Current`. Clearing `LD_LIBRARY_PATH`
and `LD_PRELOAD`, and preloading system Mesa glapi, did not resolve it. Matching
Ubuntu 22.04 amd64 packages `libgl1`, `libglx0`, and `libglvnd0`, all `1.4.0-1`,
were downloaded on the laptop from the official Ubuntu archive, transferred,
and extracted into an AETHER-only directory using `dpkg-deb --extract`.

Selecting that extracted `usr/lib/x86_64-linux-gnu` directory via
`LD_LIBRARY_PATH` for the AETHER process resolved imports and GPU camera capture.
Supply this setting again when launching smoke or viewer commands; a subshell's
setting does not persist after it exits. Keep the override local to the process
rather than modifying global shell configuration or replacing system libraries.
The packages are available under
<https://archive.ubuntu.com/ubuntu/pool/main/libg/libglvnd/>.

SAPIEN used its builtin Vulkan loader successfully despite a missing-system-loader
warning. PyTorch warned that RNG initialization touched all visible CUDA devices;
this was nonfatal but is not proof that execution is isolated to one GPU.

## Live browser viewer

After both smoke tests pass, run in the server terminal:

```bash
python -m aether_cl.viewer --render-device cuda:1 --episodes 3 --fps 5 --port 8765
```

In a separate **local PowerShell** terminal:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -L 127.0.0.1:8765:127.0.0.1:8765 YOUR_SERVER_ALIAS
```

Replace `YOUR_SERVER_ALIAS` with the configured SSH destination, or supply
`-p SSH_PORT USER@HOST`. Open <http://127.0.0.1:8765>. This run uses a separate port from the current
LingBot service on 8000. Check local port availability as well as server port
availability. If needed, choose another port in both commands.

The viewer starts one finite run and remains available with the final frame.
Ctrl+C stops the process. If a browser continues polling through the tunnel
afterward, SSH may print `connect failed: Connection refused`; close the viewer
tab to stop those requests. It provides no robot-control endpoints. An occupied
port is detected before creating the simulator. Camera rendering is observational
and introduces no changes to policy behavior; the viewer adds wall-clock pacing
for visibility, which is recorded in the run configuration.

## Output and interpretation

Each invocation creates a new UTC/UUID directory under `runs/` containing:

- `manifest.json`: runtime packages, code commit/dirty state, seeds, backends,
  action/observation modes, and controller/protocol/verification labels.
- `events.jsonl`: resets, per-step actions and observations, termination flags,
  errors, selected rendering device, and episode boundaries.
- `result.json`: final run state and per-episode outcomes, distinguishing success
  at the final step from success at any earlier step.
- `latest.jpg`: the latest actual simulator frame, when rendering is enabled.

`runs/` is excluded from Git. M0 smoke results establish infrastructure; the M1
and M2 sections describe their separate policy/task evidence. CPU tests of logging
and HTTP behavior do not validate GPU rendering; native server runs supply that
evidence. M2 adds reference/verifier records and logs its shared task contract.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m aether_cl.smoke --help
python -m aether_cl.viewer --help
```

## Next implementation milestones

1. Accept the new M2 task/verifier/disturbance behavior on the target server.
2. Measure matched baseline/V1 pairs with the shared task contract.
3. Add rule-based recovery within a fixed total action budget.
4. Compare policy-only, passive verification, verification/recovery, and a
   budget-matched simple retry control on matched disturbance schedules.

Long-term memory, learned experience abstraction, embodiment transfer, a full
planner, world models, and foundation-model training remain outside Prototype A.

## Upstream references

- [ManiSkill 3.0.1 dependency definitions](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/setup.py)
- [ManiSkill installation and Vulkan troubleshooting](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html)
- [PickCube task definition](https://github.com/mani-skill/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pick_cube.py)


## M3 bounded recovery candidate

M2 fresh-seed screening is complete: 120 episodes across 20 unique seeds,
normal success 20/20 per system, shift/drop success 0/20, all first failures
correctly diagnosed with two-step latency. See
[the audited results](../../docs/research/experiments/AETHER_CL_M2_Frozen_Screening.md).

M3 adds one bounded observed-state retry for `GRASP_FAILURE` or `OBJECT_LOST`.
It reuses the unchanged fixed-policy motion primitives and retains the same
360-step episode, task, verifier, and scripted disturbance. Recovery phase
transitions use observed arrival and grasp/lift evidence. An attempt can abort;
its completion is not task success. The first native suite recovered both seed-0 disturbed cases but failed strict
configuration matching because FPS was not forwarded. The correction retains
strict matching; the corrected archive passes all nine trial and four paired
checks and reproduces the original raw traces exactly. The operator observed
live shifted-cube recovery, and live drop completion is visible in a supplied
screenshot. The larger disturbed comparison is
rejected; its correction is documented below.
The original four frozen M2 source files remain byte-identical. The process
runner gains an optional entry module; its M2 default behavior is unchanged.

A nine-cell native development suite runs baseline/V1/V2 in normal/shift/drop
conditions, each in a fresh process. It checks nominal trace equality, causal
prefixes, trigger timing, transport gates, and bounded evidence. Disturbed V2
success or failure is measured, not forced by the acceptance gate.

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.m3_acceptance \
    --output runs/m3-acceptance \
    --archive /home/jiangle/aura-work/aether-cl-m3-evidence.tar.gz
python -m aether_cl.m3 --system v2 --live --seed 0 --episodes 1 \
    --disturbance object_shift --max-steps 360 --render-device cuda:0 \
    --fps 5 --port 8765 --output runs/m3-v2-shift-live
```

For drop inspection, stop the viewer with Ctrl+C, then run the same live
command with `--disturbance object_drop --output runs/m3-v2-drop-live`.
Use a distinct archive path for a rerun; existing evidence is never replaced.
The next larger paired benchmark follows native development review, with
parameters frozen before choosing fresh evaluation seeds.


### M3 preview and FPS correction

The first native M3 archive remains failed because requested FPS 5 differed
from recorded CLI default 10. The subprocess now explicitly forwards FPS;
all other settings and scientific behavior are unchanged. See
[the audit and correction](../../docs/research/experiments/AETHER_CL_M3_Recovery.md).
Use a new archive such as `/home/jiangle/aura-work/aether-cl-m3-evidence-fps-fixed.tar.gz`
for corrected acceptance; do not overwrite the original failed evidence.

`--live` now renders an initial frame and prints an explicit browser address
and Enter prompt. Open `http://127.0.0.1:8765`, confirm the preview is visible,
then press Enter in the server terminal. The arm stays paused until that input.
Ctrl+C cancels safely during the preview or ends the viewer after the run.

### Frozen M3 fresh-seed screening

The [preregistered protocol](../../docs/research/experiments/AETHER_CL_M3_Frozen_Screening.md)
uses seeds 40–59 across baseline/V1/V2 and normal/shift/drop: 180 requested
episodes, each eligible episode retaining the same 360-action budget. Eight
accepted source hashes and all settings are checked before output or execution.
The original policy, verifier, disturbances, runtime, and recovery remain frozen.

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

This batch does not render or open a viewer. Each cell prints its condition,
system, and final evidence/task summary. A passing suite means valid matched
evidence, including failed/aborted retries, uncertainty and natural policy
failures. It compares baseline/V1 full traces and V1/V2 prefixes through the
first intervention, or full traces when there is none. Matched outcome counts
include any recovery regressions. Existing archives are never replaced;
interrupted/error runs retain available evidence. Native fresh-seed results
were rejected by the strict recovery-pair checks. Keep the original archive;
use the per-episode process correction below rather than relaxing the checks.

### M3 per-episode process correction

The [native audit and correction](../../docs/research/experiments/AETHER_CL_M3_Isolated_Screening.md)
verify all 61,560 batch actions but reject disturbed V1/V2 comparisons: reused
resets differ in grasp flags, and four drop seeds physically diverge before
recovery. The original failed archive and original protocol remain preserved.

```bash
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1
python -m aether_cl.m3_isolated_screening \
    --output runs/m3-screening-isolated-seeds40-59 \
    --archive /home/jiangle/aura-work/aether-cl-m3-screening-isolated-seeds40-59.tar.gz
```

Every condition/system/seed now runs in a fresh interpreter and simulator with
one episode. All settings and nine source hashes stay frozen; full-reset and
causal-prefix equality remain strict. The same preselected seeds are retained,
including zero-action exclusions. This is a correction replication of already
observed seeds, not additional held-out evidence. Progress prints all 180
trials. Native startup makes this slower. This measurement command runs
independently; launch live viewing separately from batch success/failure.

The uploaded isolated native archive is now fully audited: all 902 indexed
hashes, 180 resets/171 eligible episodes, and 61,560 actions verify on clean
`c4a9b304`. Full reset observations and preintervention traces/injections match
exactly in all 60 recovery pairs; all 60 passive traces also match. Recovery
rescues 19/19 shift and 19/19 drop cases, with no normal-condition retries or
regressions. First disturbed diagnoses retain their two-step latency. See the
[accepted correction results](../../docs/research/experiments/AETHER_CL_M3_Isolated_Screening.md#corrected-native-results)
and [machine audit](../../docs/research/experiments/evidence/AETHER_CL_M3_Isolated_Screening_Audit.json).
The current result covers one held-cube task and one synthetic magnitude.
Next measure a robustness curve on newly selected seeds with the controller
still frozen. Motion/precision changes need their own subsequent comparison.
