# Owner A — 22–24 October

Extract from the complete bilingual guide; its shared interfaces and schedule also apply.

3. A — PORTABLE MODEL PACKAGE AND REPRODUCTION

Your outcome: the same selected policy can be restored outside the historical training run, with complete state and traceable identity. You own export/load/manifest and packaging; B owns scheduling and scoring.

Read these real sources before choosing a generic adapter-export recipe:
  reference/runtime/joint50_train.py — save_checkpoint / restore_checkpoint
  reference/runtime/model_core.py — projection_parameters, restore_capacity_start, snapshot_branch
  reference/runtime/joint50_policy.py — inference transform/noise/state path
  reference/runtime/lingbot_zero_padding.py
  reference/inference_common.py

First work session, target a reviewable draft in roughly four hours:
  1) Inventory saved state and external dependencies; distinguish present, missing and unverified assets.
  2) Build new code under submission/portable/: configurable exporter/loader, manifest and CPU dry-run, plus README/config/src structure and entrypoint design.
  3) Return that code, inventory, exact commands/check output and precise missing-input requests. This is a first draft target, not a promise of GPU acceptance in four hours.

The policy identity must include exact base revision, adapter, FIVE trained projection modules including biases, persistent buffers/model step, tokenizer/processor/model config, clean50 normalization, preprocessing/zero-padding and inference settings. Adapter-only export is incomplete.

Projection shapes (out,in): state_proj (768,55); action_in_proj (768,55); action_out_proj (55,768); action_time_mlp_in (768,1536); action_time_mlp_out (768,768). Include all 10 weight/bias tensors and exact named mapping/dtypes.

Current joint-training checkpoint files:
  adapter_model.safetensors; projection_weights.safetensors; adapter_config.json;
  resume-state.pt; norm-stats-clean50.json; checkpoint.json.
resume-state.pt also carries persistent_buffers/model_steps, beyond optimizer/scheduler/RNG. Inventory any older fallback separately; its layout may differ. Separate inference state from resume-only state only after checking the actual loader. Follow its trusted-checkpoint/weights_only handling; do not treat arbitrary external pickle files as trusted.

THREE-DAY PRIORITIES FOR A
P0, usable draft by 23 October 12:00: artifact inventory; manifest validation; configurable export/load implementation; exact missing dependency list; CPU rejection checks; agreed B-facing API. Send runnable partial code tonight, not just a design description.
P0, integration by 23 October evening if resources are available: a fresh-process real load and fixed-input/noise comparison on one complete checkpoint, coordinated by the captain. Match every required tensor/buffer/model step and record actual numeric differences. A copied folder or CPU fixture is not this acceptance.
P0, delivery by 24 October 20:00: one selected package identity; actual load/eval commands; configs/dependencies; manifest; reload/parity evidence; README and verified reproduction entrypoints. Missing native evidence remains an explicit blocker, not a PASS.
Use the existing approved training pipeline for train.sh; the captain supplies its exact sources/config/asset identity. Wire and document that pipeline, rather than designing a new trainer. Do not launch another training run merely to complete this assignment. If an entrypoint cannot yet work, return the missing dependency and exact failing command.
Defer optional LoRA merging, quantization, performance rewrites, container rebuilds, fancy UI and broad dependency upgrades. Keep the retained fallback package intact. A does not own tuning the policy or collecting 10,000 episodes.

Required behavior and acceptance:
  • Resolve paths relative to the package or explicit assets-root; inference must not depend on training-corpus images, a personal home directory or old run folders.
  • Hash every required inference artifact and pin revisions/config. Reject missing projections, wrong shapes/dtypes, mismatched normalization/hashes and partial checkpoints. CPU dry-run must not announce that real weights loaded.
  • During captain-arranged GPU time, load in a fresh process; verify restored tensors/buffers/model step. Compare fixed-input/fixed-noise normalized predictions (1,50,55) and decoded actions (50,14) with the reference. Record actual maximum differences and chosen tolerances. An in-process save/restore is insufficient.
  • Preserve inference behavior. Do not hurry into a LoRA merge without a before/after prediction comparison.
  • Provide a real train.sh for the actual permitted clean50 pipeline and continuation provenance; eval.sh delegates to B's runner using the frozen package. Scripts that only print placeholders are unfinished.

Return: implementation, README, configs, dependency/asset inventory, content manifest, exact commands, CPU evidence, real reload/parity evidence when available, and a clear NOT RUN / missing list. No new model training is assigned to A.

3. A：模型便携打包与复现入口

目标：离开历史训练目录后，仍能完整恢复同一个选定策略，并明确模型身份。你负责导出、加载、manifest 和打包；B 负责调度与计分。

先读真实保存者和使用者，不能直接套“只导出 LoRA”的通用方案：
  reference/runtime/joint50_train.py：save_checkpoint / restore_checkpoint
  reference/runtime/model_core.py：projection_parameters、restore_capacity_start、snapshot_branch
  reference/runtime/joint50_policy.py：推理变换、噪声与状态
  reference/runtime/lingbot_zero_padding.py
  reference/inference_common.py

第一轮工作，争取约四小时内交可审查的 CPU 草稿：
  1）列保存状态和外部依赖清单，区分已提供、缺失、未验证。
  2）在 submission/portable/ 写新实现：可配置导出/加载器、manifest、CPU dry-run，以及 README/config/src 结构和入口设计。
  3）交代码、清单、准确命令/检查输出和具体缺失输入请求。四小时是第一版目标，不是四小时完成 GPU 验收的承诺。

完整策略身份包括：准确 base revision、adapter、五个训练过的 projection 模块及 bias、persistent buffers/model step、tokenizer/processor/model config、clean50 normalization、预处理/zero-padding 和推理设置。只有 adapter 不完整。

Projection 形状（out,in）：state_proj (768,55)；action_in_proj (768,55)；action_out_proj (55,768)；action_time_mlp_in (768,1536)；action_time_mlp_out (768,768)。包含全部 10 个 weight/bias tensor，按准确名称映射，保留 dtype。

当前联合训练保存：
  adapter_model.safetensors、projection_weights.safetensors、adapter_config.json、
  resume-state.pt、norm-stats-clean50.json、checkpoint.json。
resume-state.pt 除 optimizer/scheduler/RNG 外还含 persistent_buffers/model_steps。旧 fallback 的格式可能不同，必须单独盘点。只有核对真实加载逻辑后，才能拆分推理必需状态与仅续训需要的状态。遵循现有受信 checkpoint / weights_only 处理，不把任意外来 pickle 当可信文件加载。

A的三天优先级
P0，23日12:00前可用草稿：资源清单、manifest验证、可配置导出/加载实现、准确缺依赖列表、CPU拒绝检查、与B约定API。今晚交可运行的部分代码，不只交设计说明。
P0，资源允许时23日晚联调：由队长安排，对一个完整checkpoint做新进程真实加载、固定输入/噪声对比，核对tensor/buffer/model step并记录实际误差。复制目录或CPU样例不等于这项验收。
P0，24日20:00前最终交付：一个选定模型包身份、准确加载/评测命令、配置/依赖、manifest、新进程一致性证据、README和已验证复现入口。缺原生证据仍是阻塞，不能写PASS。
train.sh对接现有获准训练流程；队长提供准确源码/配置/资源身份。你负责接线和复现说明，不另写训练框架，也不为完成任务再开一轮训练。入口不能运行就交准确缺依赖与失败命令。
暂缓可选LoRA合并、量化、性能重写、容器重建、漂亮界面和大范围依赖升级。保留fallback包。A不负责重新调模型或亲自收集10,000次episode。

必须实现并验收：
  • 路径从包内或显式 assets-root 解析；推理不能依赖训练图片、某个人主目录或历史 run 目录。
  • 所有推理资源进入哈希 manifest，锁定版本/配置。拒绝缺 projection、形状/dtype 不符、normalization/哈希不符及不完整 checkpoint。CPU dry-run 不能谎报真实权重已加载。
  • 队长安排 GPU 后，在新进程加载并核对 tensor/buffer/model step。用固定输入和噪声对比参考输出：normalized (1,50,55)，decoded (50,14)。记录实际最大差异和容差；只在同一进程保存再读回不够。
  • 保留推理行为。若考虑 LoRA 合并，必须做合并前后输出对比，不能临时图省事。
  • train.sh 应对应实际允许的 clean50 训练流程及继续训练来源；eval.sh 用冻结模型包调用 B 的 runner。只打印占位命令的脚本属于未完成。

交付：实现代码、README、配置、依赖/资源清单、content manifest、准确命令、CPU 证据，以及具备条件后的真实新进程加载/一致性报告。缺的或没运行的明确写 NOT RUN。A 不负责另开一轮模型训练。
