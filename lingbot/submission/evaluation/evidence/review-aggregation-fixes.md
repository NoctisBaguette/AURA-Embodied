# Scoped aggregation fixes review — 2026-10-22

Reviewed only frozen `review-aggregation-fix-snapshot.txt`, SHA256 `ef671c759404b72b836bef10b71fe0dbba7342aac84cca29ca24326ac484d414`. Original review is unchanged. No routine test-suite rerun; targeted in-memory CPU probes only. The implementer's 22/22 claim is not independently reasserted. Newer live changes are outside this snapshot verdict.

SPEC: **CHANGES REQUIRED**. QUALITY: **CHANGES REQUIRED**.

| Original finding | Verdict | Evidence |
|---|---|---|
| 1. Matched STARTED called interrupted | Addressed | STARTED/TERMINAL in both orders gives 1/1, zero errors; unresolved STARTED gives interruption; mismatched run hash raises. |
| 2. NumPy true/false rejected | Partially addressed | Standalone np.bool_(True/False) gives 1/1 and 1/0. New terminal conflict registry serializes original NumPy children, so identical duplicate NumPy terminals now raise. |
| 3. Error identity bypass | Partially addressed | Mixed candidate/hash errors and nested events now raise. Explicit null stage/hash still accepted for real_policy ERROR. |
| 4. Parent-child identity mismatch | Partially addressed | Task/setting conflicts raise. Parent scene_seed, episode_id and shard_id conflicts remain accepted. |
| 5. Conflicting terminal outcomes | Addressed | Same-ID COMPLETE_POLICY versus INFRA_ERROR raises conflicting terminal records. |
| 6. Status/count metadata ignored | Partially addressed | Unknown status and negative nested official counts raise. Original top-level negative attempts / excess successes still ignored, and nested counts need not match episode children. |

Remaining Important findings, scoped to the original issues/fix changes:

1. **NumPy terminal dedup regression** at snapshot 323–326: `_json_identity(previous)` and `_json_identity(record)` serialize unnormalized nested episodes. With a valid terminal `T`, let `N=dict(T, episode=dict(E, task_success=np.bool_(True), task_predicate=np.bool_(True)))`; `aggregate_records([N,N], ...)` raises `ValueError: episode record is not finite JSON: Object of type bool is not JSON serializable`. Both copies individually represent the same valid episode. Normalize before journal conflict comparison, preserving the true/false acceptance contract.

2. **Null identity bypass** at snapshot 246–251, 120–130: `dict(E,status='ERROR',error='boom',stage=None,checkpoint_manifest_sha256=None)` is accepted next to a valid baseline/hash-a episode, returning 1/1 and an error under baseline/hash-a. Keys merely existing do not establish identity; validate non-null permitted stage and matching SHA for explicit real_policy events. Same-stage/hash non-complete evidence must remain visible.

3. **Incomplete parent identity enforcement** at snapshot 269–274 and 354–356: `dict(status='COMPLETE',episodes=[E],scene_seed=100001)` accepts child seed 100000; changing parent episode_id to different-episode or shard_id to different-shard also accepts with no error. Compare every applicable supplied shared identity field. Implementer reports a newer live fix, not present in this snapshot.

4. **Count metadata not reconciled** at snapshot 339–357 and 277–291: `dict(status='COMPLETE',episodes=[E],attempts=-1,successes=999)` still returns 1/1 with no errors. A nested official `results` grid containing all zeros with the same successful child also returns 1/1 without discrepancy. Either reject unsupported top-level count metadata explicitly or validate it; supplied supported counts must agree with validated child outcomes. No change is needed to count reconstruction from episodes itself.

Reproduction uses the code block in `review-aggregation.md`, replacing the snapshot filename with `review-aggregation-fix-snapshot.txt` and adding these required journal metadata before probes:

```python
terminal.update(run_config_sha256='c'*64, finished_at_utc='2026-10-22T00:00:01Z')
started.update(run_config_sha256='c'*64, started_at_utc='2026-10-22T00:00:00Z',
               request_id_prefix='req-ep-a')
probe('matched', [started, terminal])
probe('reverse', [terminal, started])
probe('unresolved', [started])
probe('null_identity', [e, dict(e,status='ERROR',error='boom',stage=None,
                              checkpoint_manifest_sha256=None)])
for key, value in [('scene_seed',100001),('episode_id','different-episode'),
                   ('shard_id','different-shard')]:
    probe(key, [dict(status='COMPLETE', episodes=[e], **{key:value})])
probe('bad_counts', [dict(status='COMPLETE',episodes=[e],attempts=-1,successes=999)])
probe('inconsistent_counts', [dict(status='COMPLETE',episodes=[e],results=t['results'])])
import numpy as np
n = dict(terminal,episode=dict(e,task_success=np.bool_(True),task_predicate=np.bool_(True)))
probe('numpy_duplicate_terminal', [n,n])
```

Observed new video handling: null video_path with NOT_REVIEWED counts the completed episode; null with REVIEWED raises. This maintains missing-video transparency without inventing a reviewed video. No additional video-related blocker found in this scope. Native/GPU/model checks remain NOT RUN.
