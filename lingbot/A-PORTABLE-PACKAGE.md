# Owner A — Portable checkpoint and reproduction entrypoints

目标：交出一个在新进程中能够加载、权重身份明确、能接入评测的模型包。今天开始，不等新训练完成。

## First4hours

1. Read `reference/runtime/joint50_train.py` save_checkpoint/restore_checkpoint, `model_core.py` projection_parameters/restore_capacity_start/snapshot_branch, and `joint50_policy.py` inference path. They define the actual saved state; generic PEFT assumptions are insufficient.
2. Create a new submission/portable implementation, plus a directory skeleton matching official/code-requirements.md. Add a configuration-driven export/load CLI and a CPU dry-run that inventories required artifacts and reports missing inputs explicitly. No weights or tensor identities may be silently invented.
3. Deliver an artifact inventory and exact dependency list. Identify each hard-coded server path/import needed for a standalone load. Ask the captain for those specific files/manifests, not a complete new environment install.

## Required contract

One policy identity = exact released base revision + adapter + five trained projection modules + persistent buffers/model step + tokenizer/processor/model config + clean50 normalization + preprocessing/zero-padding/inference settings. The adapter alone is incomplete.

Projection module shapes (out,in): state_proj(768,55), action_in_proj(768,55), action_out_proj(55,768), action_time_mlp_in(768,1536), action_time_mlp_out(768,768). Include their biases:10projection tensors. Preserve exact dtype and named-parameter mapping; do not map by enumeration order.

The current joint-training checkpoint producer saves adapter_model.safetensors, projection_weights.safetensors, adapter_config.json, resume-state.pt, norm-stats-clean50.json and checkpoint.json. `resume-state.pt` contains persistent_buffers/model_steps in addition to optimizer/scheduler/RNG. Inventory the existing fallback checkpoint separately; its layout must not be assumed identical to this joint-training format. Inference packaging may separate required inference state from training-resume state, but must prove it did not lose required state. Follow the actual retained loader's trusted-checkpoint/weights_only handling rather than loading arbitrary external pickle files.

Expose the portable CLI proposal in INTERFACES.md. The final evaluator must not require training-corpus images or historical run folders merely to load inference. One submitted checkpoint covers every task/setting. Do not merge LoRA into base as a hurried untested shortcut; if merging is selected, compare predictions before/after the merge.

## Acceptance

- CPU check rejects a missing projection, wrong normalization/hash, wrong shape/dtype, or a partial checkpoint. It never prints READY when weights have not loaded.
- Manifest hashes all inference artifacts and pins upstream/model revisions. Configs resolve relative to the package or an explicit assets-root; no dependency on the captain's home directory.
- A fresh process on coordinated GPU time loads the package and independently restores all tensors, buffers and model step. Compare the full normalized(1,50,55) and decoded(50,14) predictions for a captured fixed input/noise with the retained reference. Record tolerances and actual maximum differences; tensor identity is exact, numeric parity is measured. In-process save/restore alone is insufficient.
- `train.sh` documents/runs the actual legal clean50 pipeline and continuation provenance; `eval.sh` invokes B's runner using the frozen package. No scripts that only echo placeholder commands pass acceptance.
- Deliver README/configs/src, artifact manifest, reload/parity report, and explicit missing externally stored assets. Coordinate weight staging early; the review ZIP contains no trained weight binaries.

Suggested branch: lingbot/portable-package. Only captain starts GPU load tests while the active training workflow owns its resource. Do not mutate the active model/environment or overwrite the original checkpoint.

## Daily progress through 23 October / 每日进度到 23 日

Use 06-DAILY-REPORT-EN-ZH.txt. Send the captain a brief report each day, including when blocked; AI drafting is fine if checked against real files/logs. Proposed check-ins: 21/22 October 22:00 and23 October 12:00, Beijing. Include remaining hands-on effort, missing inputs and takeover-ready partial code/commands by the 23rd. Report critical blockers immediately.

每天汇报完成项、真实验证、剩余工时、阻塞和接手说明；可用 AI 起草，但本人核对。建议21/22日22:00、23日中午12:00北京时间，最后一天附当前代码及命令，以便下午补进度。
