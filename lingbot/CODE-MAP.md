# Read the actual code

All links below refer to retained source references, not new teammate implementation. Host-specific absolute paths have been replaced with placeholders. External model/data/upstream files remain outside this workspace.

| File | Why read it |
|---|---|
| [joint50_train.py](reference/runtime/joint50_train.py) | Actual checkpoint save/restore, adapter/projections/resume state |
| [model_core.py](reference/runtime/model_core.py) | Model construction and named state/projection handling |
| [joint50_policy.py](reference/runtime/joint50_policy.py) | Policy loading, inference service and stage identity |
| [inference_common.py](reference/inference_common.py) | Observation transformation and decoding support |
| [lingbot_zero_padding.py](reference/runtime/lingbot_zero_padding.py) | Preserved canonical representation/padding behavior |
| [joint50_sim.py](reference/runtime/joint50_sim.py) | Evaluator setup, episode completion and typed rejections |
| [manager.py](reference/runtime/manager.py) | Native commissioning, baseline/train/candidate ordering and acceptance |
| [joint50_common.py](reference/runtime/joint50_common.py) | Shared constants and results conversion |
| [joint50_commission.py](reference/runtime/joint50_commission.py) | No-policy commissioning boundary |
| [commission negative example](reference/commission-negative-example.json) | Genuine receipt that must never be counted as policy performance |
| [official result template](official/results-template.json) | Required 50-task/two-setting result structure |

There are 25 runtime reference files plus inference support. They are a source handoff, not the full server environment. Some helpers/imports, trained weights, normalization files, fixed reference inputs and simulator assets remain external. List specific missing inputs rather than substituting invented implementations.

Read [public-reference-manifest.json](provenance/public-reference-manifest.json) to compare original and public identities. `source-pins.json` retains hashes for original installed files; it does not certify these placeholder-path copies as a runnable release. No runtime code has been redeployed by this repository setup.
