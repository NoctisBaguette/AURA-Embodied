# AURA M9a candidate camera I/O commissioning

2026-10-10, Asia/Shanghai. Engineering development only.

## Reviewed source inspection

The uploaded native source-inspection archive is 157,068 bytes with SHA-256
`c3afdec4f968f5c18466e6ec29554424ce82a816b300923e5c0469e72a1760d2`.
Safe archive membership, exact index membership, sizes and all 31 indexed hashes
pass. Its executed probe equals the published `fe3d5a75` source. All 20 accepted
source/evidence hashes match; the inspection constructs no simulator or reset.

Python 3.10.22 and the six preserved native package versions match. Retained
history contains 3,576 event files and 6,079 reset records. Proposed calibration
180–199 and evaluation 200–239 have no recorded overlap. Neither is allocated or
frozen. This history snapshot does not prove the absence of deleted/unreported
runs and does not replace the fresh-entry history guard.

The server reported 9,488,991,760,384 free bytes. GPU1 was an A100 with 75,819 MiB
free at inspection. System ffmpeg/ffprobe are absent; existing imageio-ffmpeg
0.6.0, Pillow 11.3.0 and OpenCV 4.11.0.86 provide a candidate bundled H264 path.
The commissioning entry checks the actual bundled executable and libx264 rather
than installing or assuming an encoder.

See `evidence/AURA_M9a_Sensor_Inspection_Review_v1.json`. This receipt records
source/capacity evidence, not working cameras, perception accuracy or M9 success.

## Bounded native step

Five isolated processes each reuse development seed100, the accepted Baseline,
800 actions and zero external force. No seed, force, controller, verifier,
threshold or replacement CLI is provided. The specific reporting continuation
described below reuses the already-completed first slot; it cannot retry motion.

| Mode | Renderer and candidate cameras | Capture | Raw + MP4 | Live camera publication |
| --- | --- | --- | --- | --- |
| unrendered | off | off | off | off |
| render_idle | on | off | off | off |
| capture_only | on | each endpoint | off | off |
| record_no_view | on | each endpoint | on | off |
| record_with_view | on | each endpoint | on | on |

Each child calls the unchanged M6R runner through its existing dependency
injection interface. Config.render remains false, disabling the old human-view
capture path. The environment factory changes only render enablement/device;
the accepted build_env still supplies CPU physics, Panda, state_dict, pd_ee_pose,
reward mode and action budget. Two candidate sensor cameras are added after the
accepted reset. An unchanged DecisionTraceEnvironment checks every received
action against its independent accepted-controller replay before stepping. The
preserved zero-force ForceTrace retains five 100Hz samples per action and all
contact observations. No force binding is invoked at zero input.

Camera creation/capture/recording must leave object/contact and robot state
exactly unchanged at each capture boundary. Each child must pass the accepted
runner replay, physical audit and controller-gate audit. All four instrumented
cases must equal the unrendered control at reset, every action, decision,
observation, info/scorer/verdict/recovery/path, all 4,000 physical samples and
robot qpos/qvel/TCP samples. Exact equality is required; no tolerance is relaxed.
The zero-force known Baseline must remain healthy. Any failed case is retained,
stops commissioning and is not replaced or rerun.

The original recorded history and one retained seed100 witness are pinned for
this known-scene step. The installed constructor is checked to use only its
already-reviewed seed2022 initialization. New child native logs are placed under
the existing ignored prototype runs tree so future history scans retain them.
A fresh allocation still requires a new complete history scan, not this shortcut.

## Camera and recording candidate

Primary elevated-oblique RGB-D and complementary fixed RGB use 640×480, minimal
shader, 90-degree vertical FOV, 1cm near and 3m far planes. Exact eye/target
coordinates and measured CV intrinsics/extrinsics are retained in calibration
JSON. The cube's fixed 4cm edge and declared target are static priors. Framing,
occlusion and geometric accuracy still need review after actual camera output.

The installed Camera.get_obs is called with position, segmentation, normal and
albedo disabled. Its minimal shader internally packs position/segmentation;
neither those raw channels nor a simulator segmentation mask is exposed or
saved. Only filtered RGB, scalar integer millimeter depth, depth-derived validity
and measured Panda qpos enter raw packets. No privileged task extra, native TCP,
cube pose/velocity/contact/grasp/success, seed/force/condition or recovery state
enters that packet. Privileged audit logs are separate and never feed a sensor
verifier. No sensor verifier is implemented in this step.

The depth dtype and pixels are retained losslessly without float conversion or
visual normalization. Its 1mm quantization must enter later uncertainty bounds;
this step does not relax any physical success threshold to accommodate it.
The unit/invalid-value convention is also documented in the official
[ManiSkill observation reference](https://maniskill.readthedocs.io/en/latest/user_guide/concepts/observation.html).
RGB8/depth/validity/qpos arrays are saved in NPZ with lossless DEFLATE level1.
Every retained array is reloaded, validated and checked against its live hash.
Both RGB views are also encoded into a labeled MP4. Raw camera arrays remain
unannotated; the human video has an external footer identifying development,
Baseline, seed100, zero force, mode, action and simulation time.
The generator writer follows the official
[imageio-ffmpeg interface](https://github.com/imageio/imageio-ffmpeg/blob/main/README.md);
the installed native executable and resulting video must still pass runtime checks.

Reset plus 800 control endpoints yield 801 camera sets and 801 video frames.
Playback is 20fps, independent of actual wall-clock throughput. Native OpenCV
must decode exactly 801 frames at the declared size/fps. Actual capture, record,
pipeline and wall-period distributions, raw/stored bytes and compression ratios
are reported. Live pacing may wait to target 50ms; over-budget work is neither
hidden nor accelerated, and simulation timestamps are kept separate from wall
timestamps. The manually held initial frame is excluded only from live cadence
statistics and remains in raw/video/frame-count evidence.

## Actual local viewer

The live child binds **127.0.0.1:18709**. HTTP reads only cached JPEG/status bytes;
it has no environment/action reference. Three short-lived clients read cached
frames at actions200/400/600, while full physical equality checks the stream
case. Browser reads are counted. The initial actual camera frame is held until
the user clicks Start, with a one-hour maximum wait. Start only releases that
pre-action gate; it cannot modify or restart a running episode.

From a separate Windows PowerShell window:

```powershell
ssh -p 2221 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N -L 127.0.0.1:18709:127.0.0.1:18709 jiangle@166.111.59.11
```

After `M9_CAMERA_LIVE_READY`, open `http://127.0.0.1:18709`, inspect the initial
actual camera frame, and click Start. Keep the tunnel window open. No metric
reconstruction is substituted for renderer footage. After completion, the
parent exposes the retained MP4 and last camera frame for up to one hour without
resetting/stepping any simulator. The archive is already complete during this
replay-service period and can be downloaded immediately.

## Scope after this step

Local fixtures do not substitute for native rendering or physics equality.
Return the native archive and log for independent review. A ready marker only
establishes candidate camera I/O and strict neutrality if the retained checks
pass. It does not establish observability, calibration accuracy, one-tick sensor
delivery feasibility, a non-privileged verifier, M9a success or Prototype A
closure. Estimator/S0/ST implementation and development tests remain next;
Core must accept the frozen executable protocol before any fresh M9 evaluation.

## First-slot reporting correction, 2026-10-10

The native `c05ee86` run completed the unrendered episode, then failed while
serializing its audit: `TypeError: Object of type bool_ is not JSON serializable`.
The parent stopped before any rendered child and retained the failure archive
with SHA-256 `d4726e7a043622a92a3d6c8f516f231ba70c4c2c5cdf73007d11c64228d85565`.
This is a reporting defect; no camera neutrality result is claimed from it.

The JSON writer now converts NumPy scalars/arrays into JSON primitives without
changing true/false check values. It still rejects nonfinite or unsupported
values and refuses overwrite. Encoding precedes file creation, avoiding empty
audit files from serialization failures. Regression tests exercise an actual
accepted auditor return shape containing NumPy true and false checks.

`--recover-reporting-archive` accepts only that exact failed archive. It checks
safe indexed archive membership, all indexed hashes, the original revision,
the unique first unrendered slot, the precise error, unchanged preflight/source
identity, a finished native episode with all 800 actions and all 801 robot
states, and no camera frames or started rendered slot. It then re-runs only the
existing offline decision, physics and gate auditors on retained logs. Failed
audits or an unhealthy episode block continuation. No simulator is created or
reset by this repair, and no retained action is executed again.

Use new output/log/archive names ending in `v2`. The original v1 output and
archive are not modified. The continuation includes the original failure
archive, the original error carrier, the original failed audit file and exact
native trace bytes. Revalidated reports and a new carrier record the original
native revision and the corrected reporting revision. The unrendered slot
stays in the same five-case denominator. Only the four unstarted rendered cases
execute on the corrected revision, followed by the original strict neutrality
comparison. Child progress is printed every 100 actions. Native camera success
remains unestablished until this continuation completes and evidence is reviewed.

## Episode-summary schema correction, 2026-10-10

The v2 continuation at `3f22d78` stopped with `KeyError: 'task_success'` before
any rendered case started. The screenshot reports retained v2 archive SHA-256
`d2d7a901ebc7df5bfb04eac5a05b8b72764dcd1aff72e120b8a7aa103f29af59`;
the archive itself has not yet been independently downloaded and indexed here.

Both the native-child completion path and the first-slot reporting continuation
had incorrectly read the per-step reference field `task_success` from a terminal
episode summary. The accepted M6/M6R summarizer instead emits
`task_success_at_end`, as used by the accepted M8 scorer. Both readers now use
one explicit terminal-summary gate. Missing fields or a false terminal outcome
still block continuation; controller completion and environment success do not
substitute for the physical task scorer.

The previous hand-written recovery fixture repeated the incorrect field name.
It has been replaced by an episode generated by the unchanged accepted M6R
summarizer. Regression tests cover healthy, unhealthy and missing-field reports,
both consumers, and the retained-episode repair using this actual summary schema.
No accepted source, controller, force, camera, task threshold or seed changes.

Use new output/log/archive names ending in `v3`, passing the original pinned v1
archive to `--recover-reporting-archive`. Re-audit that same retained first
episode, then execute only the four originally unstarted cases. Keep v1 and v2
directories, logs and archives unchanged; v2 records a reporting attempt, not a
new motion outcome. The original five-case denominator remains unchanged.
