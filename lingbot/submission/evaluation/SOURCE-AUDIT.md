# B producer/consumer review, 2026-10-22

Source inspection only; no retained runtime imported or executed. Paths below relative to lingbot/.

| Source | Observed contract | B implication |
|---|---|---|
| official/results-template.json | schema_version=1; team_id; exactly clean/randomized × same 50 task keys; integer attempts/successes | derive authoritative grid from template, separate coverage/errors |
| reference/runtime/joint50_common.py: results_document | COMPLETE only, fixed checkpoint, bool/np.bool_, unique task/setting/scene_seed | strengthen path identity to content SHA, reject conflicts, explicit fixture/commission exclusion |
| reference/runtime/joint50_sim.py: evaluation_tree | AST rewrite asserts exact six hook counts; generic expert exceptions fatal, UnStableError and false plan/init checks separated | upstream source/version drift must fail closed; do not catch arbitrary exceptions as rejected setup |
| joint50_sim.py: candidate/rejection/unsolved | 64 candidates; UNSTABLE_SETUP accepted only exact type and setup traceback; EXPERT_UNSOLVED when expert setup unsuccessful | parameterize finite candidate budget; maintain typed rejections and origin evidence |
| joint50_sim.py: Bridge.finish | official success equals task.eval_success; full task.step_lim; actions_started; episode/video/planner telemetry | completed failure counts as attempt; error/invalid setup does not; no shortened action budget |
| joint50_sim.py: eval_policy call | seed 100000, test_num=2; clean seen/randomized unseen, language generator 100 | new parameterized runner required; preserve setting/instruction semantics |
| reference/configs/demo_clean.yml and demo_randomized.yml | retained scene settings, aloha-agilex, RGB head/wrist; randomized background/table/light/clutter | use retained scene configs without inventing substitute task settings |
| reference/runtime/joint50_policy.py: infer/serve | one HTTPServer; global model; persistent seen requests, visual cache reset; episode/chunk identity, fixed noise seed; chunk limited to 40 | serial only; adapter must lift pilot-only bound by using official step limit, never reuse server unchanged |
| joint50_policy.py and reference/inference_common.py | high/left wrist/right wrist RGB; state float32 14D; transformation to canonical; FP32/noise(1,50,55); decoded finite(50,14) | A owns model/transform; B passes exact observations and identities, no generic LoRA substitute |
| reference/runtime/manager.py: pilot | 8×2×2, validates video decode, 20min/cell and 3h phase; dependent external wrappers | historical reference is not deployed manager; B deadlines are separate configurable limits |
| reference/commission-negative-example.json | COMPLETE but NO_MODEL_TRANSPORT_COMMISSION; episodes=[]; policy_actions_executed=0 | explicitly exclude; this is available real negative evidence, no policy result |
| official/code-requirements.md and reproduction-template.md | eval.sh loads submitted checkpoint, both settings; describe upstream changes/config | B CLI handed to A for eval.sh; actual A loader/runtime integration still required |

Immutable CPU plan policy proposed for captain review: each cell starts at scene seed 100000, advances by one; target=100 completed learned-policy episodes, maximum=1000 candidate seeds. Equal task/setting/seed panels across baseline/candidate permit paired comparison. A rejection is not a policy failure. A fatal infrastructure/model/planner error terminates the shard and is not bypassed by selecting a fresh seed. An ambiguous STARTED attempt requires evidence reconciliation rather than automatic re-execution.

No live server accessed. The dated progress/current.json snapshot is captain supplied historical status; it is not an episode ledger. No baseline scores have been reconstructed from it.
