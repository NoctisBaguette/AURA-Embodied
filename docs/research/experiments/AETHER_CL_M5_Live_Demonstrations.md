# AETHER-CL M5 — Separate Live Demonstrations

Date: 2026-10-06 (Asia/Shanghai)

The frozen M5 measurement batch was unrendered. Its archive contains no
images or video. These commands execute **new demonstrations**, not playback
of the archived 960 episodes. They use existing runtimes/controllers and do
not edit tracked source, change M5 evidence or replace any measured outcome.
Rendering and wall-clock pacing differ from the batch, so exact native trace
reproduction is not assumed.

The same drop-family scene, seed 80, is shown in this order:

1. Healthy control, V2: verifier-gated system; no retry is needed.
2. Healthy control, V3: scheduled retry at action 184; the archived run opens
   a valid grasp, drops the cube, then aborts the retry.
3. A 12 cm synthetic drop, V2: detects the loss and invokes recovery.
4. The same drop, V3: invokes its same-capability recovery by schedule.

The archived disturbed pair has aligned triggers and identical physical
traces. The healthy pair shows the value of avoiding an unnecessary retry.
This selected visualization is explanatory, not a new success-rate study.

## Laptop PowerShell — login with forwarding

If the old log watcher is still active, Ctrl+C leaves `tail -f` first. If
another AETHER viewer/tunnel is using port 8765, close that session before
starting this one. LingBot's port 8000 is unaffected.

```powershell
Set-Location "C:\Workspace\AURA-Deploy"
ssh -p 2221 -o ExitOnForwardFailure=yes -L 8765:127.0.0.1:8765 jiangle@166.111.59.11
```

Enter the password yourself. Paste the following block into the resulting
**server Bash terminal**. The existing native implementation revision
`12a9d2626636206e1687fa24df507bbadbc2a37d` already contains everything required;
no server internet, dependency installation or repository update is needed.

## Server Bash — four paused demonstrations

```bash
(
set -e
cd /home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl
source /home/jiangle/miniconda3/etc/profile.d/conda.sh
conda activate aether-cl
unset LD_PRELOAD
export LD_LIBRARY_PATH=/home/jiangle/aura-work/aether-glvnd-1.4.0/usr/lib/x86_64-linux-gnu
export CUDA_VISIBLE_DEVICES=1

python -u -c '
from pathlib import Path
import aether_cl.m3 as viewer
from aether_cl.m3_runtime import M3Config, run as run_v2
from aether_cl.m5_v3_runtime import V3Config, run as run_v3
from aether_cl.m5_attribution import preflight

preflight()
for label, disturbance in (("healthy-control", "none"), ("drop-12cm", "object_drop")):
    for system in ("v2", "v3"):
        options = dict(system=system, verification=system == "v2", seed=80,
            episodes=1, max_steps=360, disturbance=disturbance,
            disturbance_magnitude=0.12, render=True, render_device="cuda:0",
            fps=10.0, output=Path("runs/m5-live-demonstrations") / label / system)
        config = V3Config(family="drop", **options) if system == "v3" else M3Config(**options)
        viewer.run = run_v3 if system == "v3" else run_v2
        print("\nM5 LIVE DEMONSTRATION:", label, system, flush=True)
        print("Open the browser, then press Enter HERE. After it finishes, Ctrl+C advances to the next demonstration.", flush=True)
        viewer.serve(config, 8765)
print("All four demonstrations finished.", flush=True)
'
)
```

Open **http://127.0.0.1:8765** on the laptop when the terminal reports that
the preview is ready. Each demonstration waits for **Enter in the server
terminal** before moving. At 10 actions/s, 360 actions take roughly 36 seconds,
plus rendering/initialization time. The last image remains available after
the episode finishes. Only then press **Ctrl+C** to advance, refresh the
browser for the next preview, and press Enter again. Ctrl+C during movement
stops that demonstration early; it is not necessary to stop a completed batch.
After the fourth demonstration, Ctrl+C closes its viewer and returns the shell.

V3 reuses the existing M3 preview server through a process-local runner
binding. Its legacy viewer banner says M3; the explicit demonstration banner
and manifest identify V3 and its actual scheduled controller. No scientific
source file is patched. Local rendered fixtures verify initial preview
blocking, 360 actions, retained final image and cleanup; native rendering
remains a server observation, not a claim from those fixtures.

Separate logs/latest frames are written beneath
`runs/m5-live-demonstrations/`. The measured evidence remains at
`runs/m5-attribution-seeds80-99/` and in the original uploaded archive.
Further implementation still requires the [return to 02](AETHER_CL_M5_Return_to_02.md).
