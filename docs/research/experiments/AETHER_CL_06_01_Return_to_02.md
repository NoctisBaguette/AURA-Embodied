# AETHER-CL v0.1 — 06-01 Engineering Closure and Return to 02

Date: 2026-10-05 (Asia/Shanghai)

Status: **06-01's current engineering round is complete; return to 02 for research review and the next scope decision.**

This closes the implemented held-cube experiment, not the entire original
multi-task Prototype A scope. Placement/release and insertion are outstanding.
No broader Prototype A acceptance criterion is silently waived. AETHER-CL is
the first scientific instrument for one AETHER hypothesis, not AETHER v1.0.

## Research boundary and question

02 continues AETHER architecture research. 06-01 implements and evaluates a
bounded experiment, returns its evidence, and waits for the next research
scope to be defined. This handoff does not activate Prototype B/C/D or 02W.

Question: does explicit verification and bounded recovery improve manipulation
success under disturbances while keeping the nominal policy fixed?

Baseline executes the fixed policy. V1 adds passive verification. V2 adds
one rule-based recovery attempt selected by a preceding confirmed failure.
All share the same task definition, nominal controller, seeds, physics and
360-action budget. The recovery intervention may refresh the current cube
target and reuse fixed motion primitives; it does not train a new policy.

## Delivered system and milestone status

| Milestone | Delivered and validated | Status |
| --- | --- | --- |
| M0 | ManiSkill PickCube/Panda environment, A100 offscreen rendering, browser viewing and episode logs | Complete |
| M1 | Fixed nominal grasp/lift/transport controller and baseline screening | Complete |
| M2 | Post-action verification, failure classification and passive trace equality | Complete and audited |
| M3 | One bounded observed-state retry, action gates, timeouts, outcome/cost logging and isolated screening | Complete and audited |
| M4 | Frozen 2/4/8/12/20 cm magnitude sweep, isolated trials, strict paired/control checks and robustness/cost curve | Complete and audited |

Implemented source is in
[`aura-sim/prototype_aether_cl/`](../../../aura-sim/prototype_aether_cl/README.md).
The environment uses CPU physics and privileged simulator state; A100 GPU 1
is selected process-locally for rendering. A 4090 was not required. No ACT,
Diffusion Policy or VLA model was trained or integrated in this experiment.

The verifier uses observed geometry/joint state, with null uncalibrated
confidence. Simulator contact/reference labels score the experiment but do
not select recovery actions. The two demonstrated recovery triggers are
GRASP_FAILURE and OBJECT_LOST; the prototype does not implement a general
search/planning controller for every failure category.

The browser viewer serves a paused initial frame and waits for Enter before
actions; the final frame remains until Ctrl+C. Port 8765 avoids the existing
LingBot service on port 8000. Offline deployment is GitHub to laptop to server.

## Accepted evidence

### M2 — passive verification

The [fresh-seed M2 audit](AETHER_CL_M2_Frozen_Screening.md) covers 120
episodes/43,200 actions on seeds 20–39. Normal succeeds 20/20 per system;
disturbed baseline/V1 succeeds 0/20. Passive action/state traces agree and
first failures are detected with two-step latency. V1 improves observability,
not task success, because its actions deliberately remain unchanged.

### M3 — bounded recovery and isolation correction

The [corrected M3 isolation replication](AETHER_CL_M3_Isolated_Screening.md#corrected-native-results)
checks 180 selected trials and 61,560 actions on the original seeds 40–59.
There are 171 eligible episodes; seed 58 remains excluded across all nine
cells. Normal succeeds 19/19 per system; 12 cm shift/drop succeeds 0/19 for
baseline/V1 and 19/19 for V2. All 60 passive and 60 causal recovery pairs pass.
This is a correction on already observed selected seeds, not a new held-out
sample. Earlier invalid archives remain rejected and documented.

### M4 — frozen magnitude robustness

The [audited M4 report](AETHER_CL_M4_Robustness.md#audited-native-results)
covers new seeds 60–79, used across eleven points and all three systems.
All 660 selected episodes are eligible, with no exclusions. All 3,304 indexed
file hashes, 237,600 actions, 220 passive full pairs, 220 recovery causal pairs
and 200 normal pre-injection controls pass. Exact native aggregate JSON/CSV
reproduction and action/reference/verifier/recovery replay pass. Strict native
comparison tolerances were not relaxed.

| Condition | Baseline / V1 final success | V2 final success |
| --- | --- | --- |
| Normal | 20/20 | 20/20 |
| Shift 2 cm | 20/20 | 20/20 |
| Each shift 4/8/12/20 cm | 0/20 | 20/20 |
| Each drop 2/4/8/12/20 cm | 0/20 | 20/20 |

Across 220 matched V1/V2 pairs: 180 recovery-only successes, 40 both-success
pairs, no passive-only successes, and no both-failed pairs. Normal and 2 cm
shift require no retries. All 180 first retry diagnoses retain two-step
latency. Dense later agreement is reported separately and remains
privileged-state simulator-reference agreement.

Recovery action/path costs rise with magnitude. Median final recovered goal
errors across retry cells are 1.11–1.34 cm, versus 0.459 mm normal. Current
success establishes the 2.5 cm task tolerance, not fine precision. The same
20 seeds are reused across points; conditions and dense frames are correlated.
No eventual final-task recovery failure threshold was located within 2–20 cm.

Of 180 retries, 178 finish their recovery phases. At 20 cm drop, seeds 69/76
attain shared task success at steps 352/353, begin the retry hold at 353/354,
and budget-abort at step 360. Both use the remaining 177 actions. Shared
scoring requires five static observations; retry phase completion also
requires ten hold actions. Their task success precedes the abort, not the
deadline. Final task success and controller completion remain separate
outcomes, and both aborts contribute to costs.

## Scope reconciliation with the original 02 handoff

| Original expectation | Delivered coverage | Remaining limitation |
| --- | --- | --- |
| Manipulation policy | Fixed scripted controller and feedback motion primitives | No learned-policy evaluation |
| Environment interaction | One Panda/cube simulator task | One object and embodiment |
| Verification and classification | Observed-state rules, failure agreement/latency scoring | No independent camera-based perception; no calibrated confidence |
| Recovery | One bounded retry for missed grasp/lost object | No general planner/search or repeated recovery |
| Evaluation framework | Three systems, matched budgets, frozen protocols, paired/control audits and magnitude curve | Finite synthetic subset |
| Pick-place, insertion, transport | Grasp, lift and held-cube target transport | Placement/release/support and insertion remain unimplemented |
| Disturbances | Scripted cube shift and drop-plus-shift | Real-force/contact perturbations and broader environment changes remain untested |
| Episode dataset | Raw state/action/verification/recovery/result archives and provenance | Experience learning/memory is not implemented |
| Findings/report | Accepted reports, rejected evidence, machine audits and SVG curve | Broader Prototype A scientific sign-off belongs to 02 |

The shared task requires contact grasp, at least 5 cm achieved lift, distance
within 2.5 cm of the original goal, and five consecutive static observations.
The green sphere is a noncolliding goal marker. Release onto a support is not
required. The synthetic relocations are deliberate interventions and should
not be described as physically applied force disturbances.

Long-term memory, learned experience abstraction, embodiment transfer, a full
planner, world models and foundation-model training remain excluded, exactly
as requested by the original scope freeze. The current findings do not prove
that adding any of those components is necessary.

The three-system matrix also lacks a blind-retry or recovery-without-verification
comparison. It establishes the combined verification/recovery intervention's
benefit over the fixed baseline and passive V1; it does not establish that the
verifier itself is necessary or superior to an ungated retry/replanning rule.

## Operator observation versus measured evidence

The operator observed shifted-cube recovery and later the complete live process
after the audited M4 handoff. Reported concerns include slow nominal phases,
unnecessary movements, conservative high transport clearance, a large visual
goal marker and limited precision. These are useful engineering observations;
no new numerical performance claim or live-log audit follows from them alone.
The M4 benchmark uses the unrendered measurement batch. Rendering and viewer
pacing can change execution details, so live viewing is illustrative evidence.

## Evidence and GitHub locations

Repository: https://github.com/NoctisBaguette/AURA-Embodied

Implementation branch: `06-01/aether-cl-m0`.
PR: https://github.com/NoctisBaguette/AURA-Embodied/pull/1 — open, draft and
unmerged. Closing this chat is not a merge or broader research acceptance.

Frozen M4 native execution commit: `67a44d13b5363b615b5214ff543c34224e6af745`.
Audited M4 results publication: `1d64e137512357bbdf3abdbdea162855c138033e`.
The commit containing this handoff is a later documentation-only closure;
it does not change the frozen scientific sources, protocols or raw evidence.

Stable knowledge is already stored in GitHub:

- [Prototype implementation README](../../../aura-sim/prototype_aether_cl/README.md).
- [Experiment log](../../../EXPERIMENT_LOG.md), including rejected attempts and corrections.
- [Accepted M3 results](AETHER_CL_M3_Isolated_Screening.md).
- [M4 report, scope and live commands](AETHER_CL_M4_Robustness.md).
- [M4 frozen protocol](evidence/AETHER_CL_M4_Robustness_Protocol.json).
- [M4 machine audit with all 660 compact episode rows](evidence/AETHER_CL_M4_Native_Audit.json).
- [M4 robustness and retry-cost figure](evidence/AETHER_CL_M4_Robustness.svg).

Raw archives were transferred from the server and audited. They are not
embedded as binary datasets in GitHub; the repository stores their
provenance/hashes and audit records. Preserve the original archive files.

| Accepted archive | SHA-256 |
| --- | --- |
| `aether-cl-m3-screening-isolated-seeds40-59.tar.gz` | `87d1ada67b827e6a6c8b5b074d0654fbf3b03176d62c7b01714bd05584cc1421` |
| `aether-cl-m4-robustness-seeds60-79.tar.gz` | `a183e1357d6aba771fa193ae358dbcd1af30d11325eb3898ec4e93cf2a0f0bbd` |

## Findings returned to 02

1. Explicit observed-state verification plus a bounded retry improves final
   task success under the tested relocations while the nominal policy stays fixed.
2. Passive verification supplies detection without task improvement under
   unchanged actions. The added recovery is the demonstrated behavioral intervention.
3. The current environment/task is easy enough for V2 to saturate final success
   over the tested range, while cost and hold-budget pressure still deteriorate.
4. Task completion and controller-phase completion need distinct outcomes.
5. Success does not establish fine precision, camera perception, realistic
   physical disturbance handling or release/support placement.
6. Fresh per-episode native isolation and strict preintervention comparisons
   are necessary to trust this benchmark; earlier invalid evidence remains rejected.

## Decisions requested from 02

Review the evidence and update the AETHER hypothesis within its measured scope.
Then decide the next engineering round before additional implementation:

- What task coverage is required to scientifically close Prototype A, given
  outstanding placement/release and insertion?
- Should the next comparison prioritize a harder manipulation task, physically
  applied disturbances, perception-based verification, or motion/precision cost?
- If motion changes are selected, define a new frozen nominal baseline and
  rerun baseline/V1/V2 fairly rather than attaching improved motions to V2 only.
- Is a blind-retry/ungated-recovery comparator needed to isolate the value of
  explicit verification beyond simply allowing a refreshed target and retry?
- Do any measured limitations justify Prototype B/C/D or an 02W investigation?
  Current evidence does not automatically establish a memory or world-model need.

No further native run is required to return this round's findings. Preserve
current execution code and archives while 02 chooses the next scope.

**06-01 AETHER-CL is complete for this engineering round. Return to 02 now.**
