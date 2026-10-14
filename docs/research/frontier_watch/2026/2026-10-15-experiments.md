# October 15 AURA Experiment Proposals

**For Branch 02:** compare AETHER against DynaHarness, HELM, CRIS-0, RoboRSI, SEAR and ForkCast. These are research candidates, not approved architecture changes. Do not rewrite ARCHITECTURE.md or DECISION_LOG.md from this scan.

**For 06/06-01:** Do not interrupt current insertion milestone. In the next checkpoint choose among:

1. **Revisable state:** simulated 3–5-stage task with disturbed prior accomplishments. Compare no memory, append-only completion flags and evidence-linked dependency revision. Metrics: stale-state false positives, success, wasted actions and runtime.
2. **Intervention value:** at saved simulator checkpoints compare Continue, Reobserve, Local Retry, Subtask Replan, Reset. Compare default execution, binary monitor, oracle branch selection and estimated-value selection. Report expected time per completed episode, unnecessary interventions and final success.
3. **Reasoning cadence:** same skill set; compare per-step planner calls, subtask-boundary calls and event-triggered calls. Preserve fast local safety monitoring. Measure missed interruptions, response time, token/call budget and success.
4. **Transferable skills:** compare raw history, lessons/skill contracts, fresh-start agent with identical practice budget and oracle repairs on new scenes/tasks.
5. **Prediction and interface robustness:** compare world model's predicted versus executed contact/state transitions; sweep camera calibration, control rate and gripper parameters.

Separate clean and perturbed settings, autonomous and human-assisted attempts, and include variability across randomized seeds. Begin with small simulation controls; no large world-model retraining or sensor purchase yet.
