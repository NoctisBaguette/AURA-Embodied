# Portable LingBot checkpoint implementation

Captain-authorized takeover of A's core export/loading work, 23 October Beijing. Original A handoff remains unchanged. **Implemented, CPU checked, native qualification pending.** This is not a final competition submission and does not include model weights.

Start with `../../reviews/2026-10-23/READ-FIRST-EN-ZH.txt`. B's scheduler and reproduction `train.sh`/`eval.sh` still require integration. This code never deploys to or modifies the running recovery job. Do not run a second model alongside that job.

## Contracts

- Old clean50 fallback: five files total, batch 4, adapter plus frozen base projections, 10,000 updates / 40,000 samples in the retained receipt.
- New joint50: six files total, batch 2, adapter plus all ten named tensors of five trained projection layers.
- Both: checkpoint metadata and normalization hashes, full persistent buffers, model counter, pinned base/Qwen source receipts, code, tokenizer/processor, runtime versions and exact retained cache/padding helpers. Optimizer/RNG remain preserved in the full resume file; inference restores the inference state and does not restart training.
- FP32, three RGB uint8 240×320 cameras, 14D state, absolute joint targets, 50-step chunks, 10 denoising steps. Canonical active slots 0..11, 28,29. Decoded commands retain the producer's dtype (normally float64); simulator transport may cast to float32.
- LoRA: 36 layers × q/k/v/o × A/B, rank8/alpha16, 288 FP32 tensors / 3,833,856 parameters. V2 q output4096, k/v output1024, hidden768; o input4096. Five projection layers add1,899,319 parameters. The source model, not matching shapes alone, determines names.
- Runtime interface: `PortablePolicy(package, admitted_gpu_uuid=UUID)` then `.predict(packet_bytes, noise=float32_array)`; returns `normalized`, `commands`, processed `images`, `lang_tokens`, `lang_masks`. The caller uses the same packet/task/state/camera keys as `joint50_policy.py`. This is an in-process interface, not a new HTTP server or B's final evaluator.

## Local CPU tests

From this directory:

```bash
python tests/test_portable.py
python src/export_checkpoint.py --help
python src/load_policy.py --help
```

27 synthetic CPU boundary tests pass, including both checkpoint generations, full fixture export/reverification, missing tokenizer despite edited manifest, missing/extra tensors, malformed payload lengths, nonfinite values, negative checks, path collisions, failure cleanup, atomic no-overwrite and GPU admission stability/deadline using a fake inventory. Importing the loader does not import Torch. The fixture resume file is deliberately not a real Torch checkpoint and must never be used for loading.

The builder function was compared by AST with retained actual inference_common.py (SHA e87f3036866274b4f5153d7a821059d3c237a288f2d17921a14824022172e5c8); only the GPU log label changes. Its base/Qwen paths are package-relative. Actual retained checkpoint identity equals original resolved-inputs. Python compilation passes. This environment lacks Torch/PEFT/Transformers/safetensors and model bytes; real model restoration, helper import behavior, asset closure, GPU parity and simulator success remain NOT RUN.

## Native preparation — captain's existing model environment, after current evaluation

These are integration commands with explicit paths to fill, not instructions to restart the live workflow. Use the same model Python environment as the retained runtime. CPU preparation only hashes/copies existing files; it does not install dependencies or download models.

```bash
python src/prepare_assets.py \
  --base /ABS/EXISTING/base-model \
  --qwen /ABS/EXISTING/qwen-tokenizer-processor \
  --repo /ABS/EXISTING/lingbot-vla-v2 \
  --identity /ABS/EXISTING/initializer/training-smoke/resolved-inputs.json \
  --robot-config /ABS/EXISTING/clean50/robot-configs/robotwin.yaml \
  --cache-helper /ABS/EXISTING/inference-cache-recovery-v1/inference_cache_recovery.py \
  --padding-helper /ABS/EXISTING/current-run/lingbot_zero_padding.py \
  --output /ABS/NEW/asset-plan

python src/export_checkpoint.py \
  --source-checkpoint /ABS/COMPLETE/checkpoint \
  --assets-plan /ABS/NEW/asset-plan/asset-plan.json \
  --output /ABS/NEW/portable-policy

python src/load_policy.py --package /ABS/NEW/portable-policy --device cpu --verify-manifest
```

`prepare_assets` freezes hashes and small runtime copies without duplicating all weights. Export makes one complete independent copy, stages validation, then atomically publishes with no overwrite on Linux/Windows. It requires enough disk for the full copied package plus1GiB. Failed stages are removed; existing inputs/output are not deleted. Sources must be regular files; source symlinks require explicit resolution. Full dependencies are version-checked, not bundled as an environment image. Original metadata may contain host paths as provenance; loading uses package-relative paths, but the exported private package must not be committed to the public repository.

Provenance limits: original base/Qwen source-manifest bytes are bound to initializer hashes; all current copied assets are separately hashed. This does not independently re-download the official weights or authenticate their source. Fresh construction additionally checks all base tensor keys/shapes. Never call CPU structure checks successful inference.

## Fresh-process load/parity — only in the captain's allocated GPU window

Use a raw input and policy output/noise reference **from this exact checkpoint**. Old baseline arrays cannot qualify a new candidate. Bind the reference to the original checkpoint.json SHA from its retained provenance, not a guessed/latest path. Pre-create the external evidence directory; do not write reports inside the immutable package.

```bash
CUDA_VISIBLE_DEVICES=GPU-CAPTAIN-SELECTED-UUID python -B src/load_policy.py \
  --package /ABS/NEW/portable-policy --device cuda --verify-manifest \
  --admitted-gpu-uuid GPU-CAPTAIN-SELECTED-UUID --admission-timeout 600 \
  --input /ABS/EVIDENCE/matching-input.npz \
  --reference /ABS/EVIDENCE/matching-chunk-001.npz \
  --reference-checkpoint-sha256 CHECKPOINT_JSON_SHA256 \
  --report /ABS/EVIDENCE/fresh-process-parity.json \
  > /ABS/EVIDENCE/fresh-process-parity.log 2>&1
```

Admission prints status, requires the same UUID, three stable samples ≥60GiB free and ≤10% utilization, and has a finite deadline. Model failures are not retried. The retained builder additionally enforces one visible GPU and its conservative allocator cap. The captain still owns scheduling; memory checks are not a GPU reservation. Follow foreground progress with `tail -f /ABS/EVIDENCE/fresh-process-parity.log` in another terminal. This command is not an unattended job launcher.

PASS requires exact live adapter/buffer/projection restoration, fixed model counter, repeated identical-input output equality, and equality with captured normalized/decoded/tokens/masks. Processed image equality is checked when present in the reference; omitted images are explicitly reported. No tolerance widening, kernel switch or automatic checkpoint promotion occurs. A report records failure or actual parity success; the full stderr log retains the traceback. Windows PowerShell execution of these Bash examples is not tested—run them in the server's model environment.

## Remaining integration

1. Real asset plan/export, fresh-process load and matching-output parity; qualify both generations that will be used.
2. B's evaluator API/CLI and train/eval reproduction entrypoints; full schema and checkpoint-hash propagation.
3. Test the portable loader on the intended submission environment, which may differ from the existing A100 runtime.
4. Freeze one checkpoint after candidate comparison; retain actual coverage, failures and videos. Export/load work preserves behavior and does not itself improve success.

中文：这是A核心导出/加载工作的接手实现，尚未通过真实GPU联调。不要把27项CPU测试称为真实模型成功。当前后台评测继续；等队长安排资源后，用同一个checkpoint的输入/噪声/参考输出做新进程验收。原始A包和现有服务器release都不改。B仍需完成评测对接，train.sh/eval.sh和最终提交包还需联调。失败要提交完整日志，不能用旧模型参考输出为新模型做验收，也不能降低一致性标准来让测试“通过”。


## 24 October admission and bounded execution update

PortablePolicy now accepts optional admission_deadline_epoch, admission_progress and cancelled arguments. Admission requires three stable samples of the selected UUID plus a separate fresh final recheck. An absolute epoch deadline is preserved across prerequisite work; cancellation is checked during waits. Default callers remain supported. CPU fixture tests include the final sample. No GPU or native simulator success is established by these tests.

execution_contract.py supplies a finite request/progress contract for separately reviewed execution-prefix consumers:700actions with10-target prefixes require70requests. It rejects skipped/duplicate chunks, inconsistent completed actions, unsupported prefixes and noise schedule changes. This module does not by itself change the default policy, route tasks, alter success predicates or authorize replacing evaluation results.

The captain's isolated workflow exports the fixed checkpoint, requires actual fresh-process parity, then compares two already-inspected laptop scenes at execution prefixes50and10 with videos and full action evidence. Four development episodes are not an official score or broad validation. No automatic prefix promotion or training is scheduled. Native model load, parity and comparison remain pending until run.
