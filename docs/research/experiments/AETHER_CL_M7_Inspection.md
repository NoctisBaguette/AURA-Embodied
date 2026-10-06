# AETHER-CL M7 — Contact-Rich Insertion: Installed-Task Inspection

Date: 2026-10-06 (UTC).

Status: authorized scope; installed-task inspection pending. No M7 native
outcomes or numerical protocol have been produced or frozen.

Authority: [02's M6R acceptance](AETHER_CL_M6R_02_Research_Review_v0.1.md),
DEC-0006 at `145aadce249b23a49ecb899ff273e93f673dd03b`.
PR #1 remains open, draft and unmerged; Prototype A remains open.

## Research question

Does the AETHER-CL verification/recovery pattern generalize from released
placement to contact-rich insertion, where success depends on the object-target
physical relation rather than end-effector pose?

Prefer an existing rigid single-arm insertion task in installed ManiSkill 3.0.1.
Official [task documentation](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/index.html)
and [API documentation](https://maniskill.readthedocs.io/en/latest/api/mani_skill/index.html)
identify `PegInsertionSide-v1` as a candidate with randomized peg/hole geometry,
3 mm hole clearance and Panda wrist-camera robot support. This is a candidate,
not selection based on locally installed source. Read the exact server version
and collision geometry first. If no suitable installed task exists, return to
02 before creating a custom environment or changing the question.

## First action: static inspection

[`tools/m7_task_inspection.py`](../../../tools/m7_task_inspection.py) uses only
Python's standard library and installed distribution metadata. Run it in the
existing native Python 3.10 `aether-cl` environment. It collects:

- Registered task IDs, candidate task source bytes and SHA-256 hashes.
- Supporting simulator/controller/Panda sources and available Panda URDF/SRDF assets.
- Native package versions, measurement checkout identity and dirty status.
- Available `runs/**/events.jsonl` reset history, preferred 140–159 overlap and
  the first unused contiguous 20-seed range starting at 140.

The script never imports ManiSkill/Sapien, creates an environment or resets a
seed. It does not modify the native checkout. Missing reset history fails;
freshness only covers retained available history, not deleted/unreported runs.
The guard must run again immediately before fresh entry. Reports are created
exclusively; an existing report is retained rather than overwritten.

```bash
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
python -u /home/jiangle/aura-work/m7_task_inspection.py \
  --output /home/jiangle/aura-work/m7-task-inspection.json
```

## Development and freeze requirements

Create a new task-specific matched Baseline/V1/V2 system. Baseline has a fixed
insertion controller; V1 adds passive verification; V2 uses the same nominal
controller and verification-gated single bounded recovery. The placement
implementation and V2-old/V2R comparator do not carry forward.

Independent success must require valid acquisition, acceptable object-target
orientation and entry/lateral alignment, geometry-derived insertion depth and
stable final relation for a frozen number of observations. Log built-in success
separately; it neither drives control nor substitutes for the independent score.
Recovery progression follows the physical effects needed by its next phase.

One recovery episode may retreat/back out to a safe pre-insertion pose, refresh
object/target geometry, realign, reinsert once and verify. An earlier failure
consumes that opportunity; later failure remains recorded.

Commission a synthetic lateral misalignment family on previously observed
development seeds. Inject after nominal prealignment and before meaningful
contact/insertion. Select normal, easy/inside capture and four harder offsets
from actual geometry and development evidence. Freeze exact magnitudes, scorer,
stage conditions, timing, budgets, seed range and audit protocol before fresh
native outcomes. Angular perturbation is deferred unless lateral offsets cannot
produce a clean failure family. Never adaptively replace seeds or outcomes.

Retain M3–M6R process isolation, source identity, environment capture, raw logs,
independent replay, matched common-prefix/control comparisons and immutable
pilot/final archives. Log success, depth, relative pose, detection/diagnosis,
attempts/rescues/unnecessary recovery/regressions, all retreat/realign/reinsert
stage outcomes, action/path costs, controller completion versus physical success
and the complete robustness curve.

After frozen native M7 evidence, return to 02 before further scope.
Physics-propagated disturbances, non-privileged sensor verification, memory/world
models, Prototype B/C/D, foundation-model integration and 02W remain deferred.
