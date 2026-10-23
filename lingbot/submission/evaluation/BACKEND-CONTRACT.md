# Integration additions — 23 October

The only accepted model manifest filename is A's `package-manifest.json`, format `lingbot-portable-v2`. Its byte SHA256 is the `checkpoint_manifest_sha256` carried through plans, requests, records and aggregation; this differs from the inner training `checkpoint.json` SHA. Do not rename files inside an immutable package. The runner executes the sibling portable CPU validator before starting a native backend; actual GPU load/parity remains a separate required gate.

Transport explicitly encodes stdin as UTF-8. A setup rejection may contain only zero policy action/chunk counts (or omit them), an empty request list (or omit it), and no policy outcome. The native adapter must positively establish that no learned action occurred. Do not classify a mid-policy failure as scene rejection. The `init_scene` field for EXPERT_UNSOLVED represents the original expert acceptance predicate (`TASK_ENV.check_success()` after `play_once`), together with `TASK_ENV.plan_success`; it is not a free-form startup claim.

Each terminal execution_evidence now records `runner_wall_seconds`, measured over the backend call including startup and cleanup. `wall_seconds` retains the backend's reported episode wall time. Use the runner value for throughput, and add any separately owned policy-service load time explicitly.

B native adapter still NOT IMPLEMENTED. Required inputs now exist as code/API and retained baseline evidence; actual exported weights and GPU allocation remain captain handoffs. Reference wrappers are not deployment commands. Preserve full100instruction-template generation, two setups/expert acceptance, scene seed, first noise777,50actions/chunk, official action limit, and exact task.eval_success. A callable is `PortablePolicy(package, admitted_gpu_uuid=UUID).predict(packet_bytes, noise=float32_array)`; keep policy lifetime outside per-scene subprocesses. Its portable-GPU qualification is not established by the existing server runtime replay receipt.

Original B contract follows.

# Serial backend contract

The CPU runner owns the schedule, candidate seeds, request namespace, immutable
journal, one-at-a-time process launch, and wall-clock deadlines. The deployment
adapter owns loading the policy package, native runtime initialization, task and
scene creation, inference, action execution, cleanup, logs, and video capture.
No native adapter is included in this package.

The runner launches one command for each candidate episode without a shell. It
passes one UTF-8 JSON object on stdin and expects exactly one UTF-8 JSON object
on stdout. Any non-zero exit, invalid JSON, identity mismatch, unrecognized
status, process timeout, or adapter exception is terminal `INFRA_ERROR` for that
cell. The timeout starts before process creation and includes adapter startup,
episode execution, and cleanup. There is no automatic retry of failed or
ambiguous work. The adapter must shut down child processes and release scene
resources before it exits.

For every attempt, the runner opens `backend.stdout.log` and
`backend.stderr.log` with exclusive creation under the request's `output_dir`,
then directs the child process streams to those files. The full raw streams are
retained for successful episodes, setup rejections, crashes, protocol errors,
and timeouts. The immutable terminal record includes their paths as
`backend_stdout_path` and `backend_stderr_path` in `execution_evidence`; these
runner-owned files are separate from the adapter's `log_path`.

The request contains these identity fields, which the adapter must echo exactly:

```json
{
  "evidence_kind": "real_policy",
  "stage": "baseline",
  "checkpoint_manifest_sha256": "<64 lowercase hex characters>",
  "task": "lift_pot",
  "setting": "clean",
  "scene_seed": 100000,
  "episode_id": "ep-<deterministic UUID5 hex>",
  "shard_id": "sh-<deterministic UUID5 hex>",
  "instruction_type": "seen",
  "precision": "FP32",
  "actions_per_chunk": 50,
  "denoising_steps": 10,
  "action_limit": "official_full_task_limit",
  "noise_seed_base": 777,
  "request_id_prefix": "req-ep-...",
  "request_id_template": "req-ep-...-chunk-{chunk_index:04d}"
}
```

`clean` maps to `seen`; `randomized` maps to `unseen`. The adapter must use the
full task-specific action limit from the runtime and report that limit twice as
`step_limit` and `official_step_limit`. The runner checks they match, verifies
`1 <= actions_started <= step_limit`, and verifies `chunks == ceil(actions_started
/ 50)`. It cannot independently verify a native environment's configured limit
until the missing adapter is reviewed and connected to the official runtime.

For each policy request, chunk indexes start at one. The adapter reports
`request_id = req-{episode_id}-chunk-{chunk_index:04d}` and
`noise_seed = 777 + chunk_index - 1`. Request identities must be consecutive and
unique. Episode success must be a JSON boolean, and `task_predicate` must be the
runtime's `task.eval_success` boolean with the same value.

A completed response uses `status: "COMPLETE"` and includes the exact echoed
identity plus `task_success`, `task_predicate`, `actions_started`, `step_limit`,
`official_step_limit`, `chunks`, finite `wall_seconds`, a retained `log_path`,
`video_path`, and `requests`. If a video is unavailable, set `video_path: null`
and `video_review_status: "NOT_REVIEWED"`; this keeps the result in coverage
without claiming visual review. When present,
`video_review_status` must be `REVIEWED` or `NOT_REVIEWED`; `PENDING` and other
values cannot be accepted as a completed episode.

Only these setup rejections may advance to another seed:

```json
{
  "status": "REJECTED_SETUP",
  "rejection_category": "EXPERT_UNSOLVED",
  "rejection_evidence": {"plan_success": false, "init_scene": true}
}
```

`EXPERT_UNSOLVED` requires both evidence fields to be booleans and at least one
to be false. `UNSTABLE_SETUP` requires `exception_type: "UnStableError"`,
`exception_module: "envs.utils.create_actor"`, and a `traceback_frames` list
containing a frame whose name is `_init_task_env_` and whose filename ends in
`/envs/_base_task.py`. All planner, model, transport, runtime, and other failures
are fatal for the cell. Free-form error messages do not qualify as setup
rejections.

Fixture adapters are used only by tests and must echo `evidence_kind: "fixture"`.
The production CLI does not expose a way to run fixtures as policy evaluation.
Fixture evidence never contributes to official counts.
