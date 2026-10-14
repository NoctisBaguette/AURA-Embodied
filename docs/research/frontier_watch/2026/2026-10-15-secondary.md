# October 15 AURA — Secondary Discoveries

**All reported benchmark results originate from the authors.** See [main issue](2026-10-15.md) and [primary new papers](2026-10-15-new-papers.md).

## EmbodiedEvo — reusable Skills and Lessons
[arXiv:2610.18867](https://arxiv.org/abs/2610.18867), October 13. Coding agent evolves Skill and Lesson artifacts during a playground run, then freezes the resulting harness for later unseen scenes. Authors report RoboDojo-Sim average score 44.48, success 37.82%, and 53% lower execution cost versus raw history at similar performance. Its claim to exceed the then officially verified leaderboard is **not independently verified here**. **READ → DEEP DIVE:** compare structured skill code versus raw episodic replay across held-out tasks, not just repeated trials. Fine contact remains a reported weakness.

## WorldOracle — physical correctness of predicted futures
[arXiv:2610.18826](https://arxiv.org/abs/2610.18826), October 13. Aligns initial observation, real action sequence, predicted rollout, and actual physical outcome, evaluating state correctness, interaction alignment, contact areas and multi-view coherence. Seven models reveal different failure modes. Code/datasets/leaderboard promised, not assumed public. **READ + benchmark candidate:** start with paired simulated trajectories, log outcomes and perturbations.

## ForceWAM — contact futures
[arXiv:2610.18852](https://arxiv.org/abs/2610.18852), October 13. Learns joint video plus 6-axis wrench futures from demonstrations; inverse dynamics integrates task-specific demos and task-agnostic play for local contact response. Authors report 85–95% success on selected real contact-rich tasks and +15–45 points from play-data use. **READ:** investigate simulation-only force/contact prediction before considering tactile hardware.

## LIBERO-RIG — hardware setup robustness
[arXiv:2610.18843](https://arxiv.org/abs/2610.18843), October 13. Fixed-task benchmark with eleven perturbation axes covering camera mounting/calibration, control rate/gain, proprioception, base/table geometry and gripper pads. Authors report pooled success 93.2% clean, 76.7% middle severity and 50.9% highest severity. **READ + subset REPRODUCE:** vision-only OOD does not adequately stress sensing/control mismatches.

## Chronos Policy — physical timestamp conditioning
[arXiv:2610.13929](https://arxiv.org/abs/2610.13929), October 9. Uses observation capture times and intended action times, with time-aware RoPE and temporal sampling randomization, to improve robustness to asynchronous sensing and inference delays. **READ** and test variable sensor/control scheduling in simulation.

## SpatialHarness, DreamTrue, Dream to Remember
[SpatialHarness](https://arxiv.org/abs/2610.12457), October 8: synchronized virtual scene and alternate rendered viewpoints aid fine manipulation by a frozen multimodal policy. Authors report plug insertion 26.7% -> 66.7% in their limited evaluations. **READ:** geometry/observability experiment.

[DreamTrue](https://arxiv.org/abs/2610.12468), October 8: counterfactual, action-faithful world model training and reward-based physical plausibility post-training; reported interaction defect rate 48.12% -> 6.25%. **READ:** action-fidelity scoring.

[Dream to Remember](https://arxiv.org/abs/2610.13816), October 9: world-model rehearsal prevents forgetting as a steering module learns new tasks; on CALVIN authors report 63.7% -> 74.8% average success after eight imagination-trained tasks compared with large degradation in a LoRA baseline. **READ:** a predictor may be too inaccurate for new-task planning yet useful for rehearsing old behaviors.

## Further watching
[EqC](https://arxiv.org/abs/2610.18790): learned energy-consistency signal for competence-boundary takeover and data-driven improvement — **WATCH**.

[ACCRUE](https://arxiv.org/abs/2610.18596): persistent lightweight off-policy actor/critic for continual assembly adaptation — **WATCH**.

[AXIS-Bench](https://arxiv.org/abs/2610.18869): matched data/compute evaluation of demonstration quality conditioning/filtering/weighting — **READ**, particularly for LoopWAM.

[BT-Agent](https://arxiv.org/abs/2610.13862): onboard behavior-tree skills with local checks and structured failure feedback — **READ secondary comparator**; its experiments focus on quadruped navigation.

[Hesai Kosmo launch](https://www.reuters.com/technology/chinas-hesai-launches-spatial-camera-boost-ai-powered-robotics-adoption-2026-10-14/), October 14 — **WATCH**, sensor/data infrastructure rather than novel adaptive manipulation intelligence.

**Evidence caveat:** Announced “code release,” project pages, and advertised checkpoints do not prove runnable reproduction. Check actual repository contents, weights, license and hardware dependencies first.
