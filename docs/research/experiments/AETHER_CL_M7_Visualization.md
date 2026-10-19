# M7 recorded-state visualization

This 32.05-second, 1280×800 H.264 clip illustrates an already completed M7 trial pair. It reconstructs recorded peg, target and TCP poses from seed 140 at a nominal 6 mm offset. The target is displayed as a cutaway and the arm is omitted. **This is a geometry replay, not original camera footage, a new simulation run, training, or another native outcome.**

Baseline appears on the left and V2 on the right. The records match physically through action 642. V2 begins its bounded recovery at 643, retreats, refreshes geometry, realigns, reinserts and first satisfies the original independent task score at 801. The final Baseline depth is −0.082550 mm with lateral error 5.696575 mm; V2 depth is 114.454713 mm with lateral error 0.266975 mm. Displayed phases, scores and depth curves come from the retained original records.

The clip presents the complete 60 seconds of recorded control states at 2× speed, using every second original endpoint at 20 video frames/s, followed by a two-second endpoint hold. No trajectory interpolation or altered outcome is used. It is a deliberately selected paired rescue for explanation; the [full M7 results](AETHER_CL_M7_Results.md) retain all failures and denominators, including the two scenes that fail in normal conditions and the unnecessary easy-case recovery.

Video filename: `M7_Recorded_Geometry_Replay.mp4`, 470,647 bytes. SHA-256: `51af48018b76cebac44ff4d5e2cabad4f8c3b1b7b5c7401e67c2ca540dd9bd3d`. Native measurement remains `a51e5d2073c4033141b26e956804d593aa45d6df`. The video is delivered separately from the repository; this publication retains its source hashes, provenance and reproducible renderer rather than adding binary media to Git.

The [visualization receipt](evidence/AETHER_CL_M7_Visualization_Receipt.json) includes six checked source files, the selected native results, shown frame indices, video hash/format and source identity. [Executed visualization source](evidence/AETHER_CL_M7_Executed_Visualization.py) is byte-identical to the rendering program used for this clip. The [reusable renderer](../../../tools/m7_geometry_video.py) differs only by parameterizing the video-title seed/offset text; its default settings produce the same title. It uses NumPy, SciPy, Matplotlib and ffmpeg and never imports a native simulation environment.

From the repository root, using an extracted final archive and an output directory separate from raw evidence:

```bash
python tools/m7_geometry_video.py \
  --evidence /path/to/m7-insertion-seeds140-159 \
  --output /path/to/videos/M7_Recorded_Geometry_Replay.mp4 \
  --seed 140 --ratio 2 --stride 2
```

Selected manifest/result/event hashes and child-parent results are checked before rendering. Existing movie or receipt paths are rejected rather than overwritten. The video was inspected at initial/pre-insertion/final states; it preserves the cutaway/arm-omitted/provenance labels and matches the original task outcome. Generating a full arm view would require the native renderer and reconstruction of the recorded robot joint positions; none was recorded during the headless M7 matrix.

02 accepted M7 under DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40`; see the [02 research review](AETHER_CL_M7_02_Research_Review_v0.1.md). This visualization adds supporting material without changing frozen measurement code, scoring, seed selection, outcomes, audit tolerances or that decision. It does not execute the separately authorized M8 round.
