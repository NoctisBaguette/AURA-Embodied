# AETHER live view and recording requirement

Recorded: 2026-10-09, Asia/Shanghai. User instruction for future native rounds.

Actual simulator camera output must be available through a browser opened at a
local address, with an SSH tunnel when the simulator runs on the server. A
metrics dashboard or a cube/TCP reconstruction does not satisfy the requirement.
Show the actual robot, object and interaction. Record MP4 video so the work can
also be watched after execution and shared with an instructor.

For matched examples, provide synchronized Baseline/V2 comparisons for a
successful recovery, a failed recovery and a healthy control. Show seed,
condition, system, action/time and the relationship to the retained episode.
Use the same camera, playback rate and spatial framing for both systems. Retain
failed outcomes and label reconstructed geometry separately from camera footage.

Set up and verify the camera stream and video output before the next native
round. Preserve the frozen controller, disturbance, physics settings, audit
guards and reset history. If rendering would change those settings, resolve and
document that before freezing/executing the round. A demonstration replay must
be labeled as a replay and must not be presented as original evaluation footage.

Existing connection:

```text
ssh -p 2221 jiangle@166.111.59.11
Server repository: /home/jiangle/aura-work/AURA-Embodied-offline
Prototype: aura-sim/prototype_aether_cl
Conda environment: aether-cl
```

The camera-service port and local forwarding port must come from the actual
viewer configuration; no port is assumed by this note.

M8 was unrendered. The three accompanying M8 MP4s reconstruct the retained cube
pose and TCP position at 20 Hz. They contain 801 recorded states spanning
40 seconds of simulation and hold the last state for 2 seconds. They introduce
no new simulation, reset seed, outcome or training run.

M8 evidence source archive SHA-256:
`667c043859f9d639bbff79e3456c4a608d4ef336806f94b77acccde40870924c`.

M8 published review head remains:
`4a6396a8ef8fc33fb543f37638f0ba7a81a784ea`.

This instruction concerns observability and communication. It does not authorize
M9, a force-regulation experiment, or any change to the research scope awaiting
02's decision.
