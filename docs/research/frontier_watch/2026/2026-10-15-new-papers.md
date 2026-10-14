# October 15 AURA — New Papers (Primary)

All metrics are **author-reported**. See [main issue](2026-10-15.md) and [other research](2026-10-15-secondary.md).

## RoboRSI — constrained skill revision
[arXiv:2610.12424](https://arxiv.org/abs/2610.12424), submitted October 8. Decomposes tasks into compound, atomic, and base skills with scoped input/output contracts. Execution outcomes are attributed to responsible branches; revisions undergo validation and stable routines are consolidated. Authors report 104 physical improvement rounds and 2.7–11.0 percentage-point gains across simulation suites.

**Capability / AURA value:** direct competition for AETHER's diagnosis, hierarchical recovery, validated reuse, and agentic tool orchestration. **DEEP DIVE.** Experiment: corrupt one skill in a three-stage manipulation task; compare changing the responsible skill alone with rewriting the entire plan, including regression and held-out transfer. Distinguish predefined skill ontology from genuine autonomous discovery.

## SEAR — test true experience accumulation
[arXiv:2610.18792](https://arxiv.org/abs/2610.18792), October 13. Self-Evolving Agentic Robotics separates code-as-policy, agent-as-policy, and auto-research modes. Benchmark controls for trials, budget, privilege and scene generalization across seven LMs, 330 simulated tasks and five physical tasks. Authors find reusable control routines transfer more reliably than task-specific fixes; for some easier tasks, rerunning short sessions matches longer learning sessions.

**Capability / AURA value:** persistence, procedural memory, fair learning-versus-repeat testing. **DEEP DIVE.** Compare agent with stored experience versus fresh-start equal-budget agent on held-out scenes and tasks.

## ForkCast — intervention choice from counterfactual futures
[arXiv:2610.18650](https://arxiv.org/abs/2610.18650), October 13. A latent predictor scores nominal Commit, camera Reobserve and trajectory Replan at matched future horizons. No explicit binary failure detector is necessary. On five perturbed RoboTwin 2.0 tasks, authors report 13.3% to 30.0% pooled success. Paper says code **will** be released; do not assume it is public.

**Capability / AURA value:** estimated value of interventions, active information acquisition, bounded world prediction. **DEEP DIVE / reproduce principle.** Start with simulator checkpoint-branch oracle, then learn candidate ranking. Measure success, extra actions, latency and needless interventions.

## LoopWAM — learn failures without imitating them
[arXiv:2610.18873](https://arxiv.org/abs/2610.18873), October 13. Mixed-quality deployment rollouts provide world-consequence supervision while action imitation is quality-weighted. Authors report RoboChallenge Table30-V2 success 23.67% -> 43.33% after three learning rounds and strong RoboTwin/RoboCasa results.

**Capability / AURA value:** experience-driven WAM improvement and safe utilization of negative outcomes. **DEEP DIVE.** Compare success-only imitation, naive all-data imitation, and all-outcomes world prediction with filtered actor under matched rollout budgets.

## ChunkAct — let fast routines run
[arXiv:2610.18874](https://arxiv.org/abs/2610.18874), October 13. Compiles memory-derived primitive sequences into action chunks and calls an LLM only at meaningful boundaries/failure. Authors report LIBERO-Pro +5.0 success points, 2.9x fewer LLM calls and 4.4x fewer input tokens than the agentic baseline.

**Capability / AURA value:** selective reasoning and deployment efficiency. **READ -> DEEP DIVE.** Compare primitive-level, boundary-level, and event-triggered planning under safe local monitoring. Failure-only replanning could react too slowly to hazards; measure reaction time.
