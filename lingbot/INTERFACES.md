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

A owns export/load/manifest/packaging. B owns evaluation scheduling/episode ledgers/aggregation. Optional C owns prose/provenance/uploads. Baguette owns live resource allocation, frozen-policy choice and actual submission. Work on separate branches/new files; review the interface together before merging. Neither teammate edits the installed frozen v3 release, changes dataset labels, restarts the active worker, or upgrades GPU packages.
