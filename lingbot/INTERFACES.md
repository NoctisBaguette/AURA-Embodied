# Shared interfaces — agree before A and B write overlapping code

These CLI names are the proposed integration contract, not existing working commands.

- A: `export_checkpoint --source-checkpoint PATH --assets-root PATH --output PATH` and `load_policy --package PATH --device DEVICE --verify-manifest`.
- B: `evaluate --policy-package PATH --tasks-file PATH --setting clean|randomized --episodes N --output PATH --resume`; `--dry-run` performs no GPU/model/physics work. `eval.sh` is A's entrypoint delegating to this runner.
- B: `aggregate_results --records PATH --checkpoint-manifest-sha256 HASH --team-id ID --output PATH`. Output counts use official schema, with coverage/errors stored separately.
- Runtime contract: three RGB240×320×3uint8 camera views, current14Dfloat32joint/gripper state, task instruction. Preprocessing maps to55Dcanonical representation. Model prediction(1,50,55), decoded commandchunk(50,14), all finite. Existing inference usesFP32,50steps/chunk,10denoisingsteps and fixed per-request noise identity. Do not change these defaults in packaging.
- Final model identity is a content manifest covering base/adapter/projections/buffers/step/config/tokenizer/processor/normalization/preprocessing. Save its SHA in every evaluation shard. Display paths alone are insufficient identity.

## Existing files to inspect

`reference/runtime/joint50_train.py`: exact checkpoint producer/restore. `model_core.py`: retained builder and tensor identity. `joint50_policy.py`: transform/noise/HTTP inference and stage identity. `joint50_sim.py`: actual evaluator assembly/scene validity/finish records. `manager.py`: existing gates/episode receipt/video checks. `joint50_common.py`: schema conversion, normalization/audit references and results counts. `reference/inference_common.py`: retained preprocessing support. Some imports/assets remain external; list them instead of inventing substitutes.

The current reporter records successful commissioning as COMPLETE with native_commissioned=true, checkpoint=NO_MODEL_TRANSPORT_COMMISSION, episodes=[], policy_actions_executed=0. This is an explicit negative test case, not a policy success.

## Change ownership

A owns export/load/manifest/packaging. B owns evaluation scheduling/episode ledgers/aggregation. Baguette owns live resource allocation, frozen-policy choice and actual submission. Work on separate branches/new files; review the interface together before merging. Neither teammate edits the active server release, changes dataset labels, restarts the active worker, or upgrades GPU packages.

## 22–24 October delivery

The complete guide defines priorities and reporting. A/B agree this API within the first two work hours, deliver partial code by 23 October 12:00 Beijing, and aim for real integration that evening with captain-arranged resources. Final internal delivery is 24 October; the plan uses 20:00 Beijing. Do not rebuild the model stack or introduce unmeasured concurrency to meet the date.

## 22 October checkpoint schema clarification after A's handoff

The original clean50 fallback is update10000/samples40000/batch4, with checkpoint.json plus adapter weights/config, resume-state and normalization (five total files). Its projections remain in the pinned frozen base. The new joint continuation is batch2 and six total files, adding separately trained projection_weights.safetensors. Validate their producer-specific identities and complete file sets; do not fabricate a missing projection file or apply the new cursor formula to the old fallback. See reviews/2026-10-22/01-A-REVIEW-EN-ZH.txt. A's proposed callable loader remains unimplemented, not accepted integration.


## 23 October takeover implementation on review branch

A core implementation now lives in submission/portable. export_checkpoint accepts --source-checkpoint with --assets-plan or --assets-root and --output. prepare_assets builds a CPU hash/copy plan from existing assets. load_policy defaults to CPU manifest verification; explicit CUDA mode performs restoration and reference-bound parity after bounded same-UUID admission. PortablePolicy.predict consumes existing NPZ packet bytes and an explicit (1,50,55) float32 noise array, returns normalized/commands/images/lang_tokens/lang_masks. Model construction is not performed on import. B's final scheduler/HTTP bridge and train.sh/eval.sh are still integration work. The code is CPU checked, not a native-qualified or final submission package. See the implementation README for exact CLI and limits.
