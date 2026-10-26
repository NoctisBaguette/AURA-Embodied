# Stable aggregation scoped re-review — 2026-10-22

Snapshot: `review-aggregation-stable.txt`, SHA256 `7450c5044ed9fd5c62359dc4e32cd6043d8a1e1e72a05894270e6726c6f5ef9c`; source file SHA256 `f0c59ae127268cdf7106d4e64a70778f7ecd4ca8db8152fabb51fe2678be96e7`.

Original-six-finding SPEC verdict: **PASS**. Original-six-finding QUALITY verdict: **PASS**. All six original findings and the intermediate fix regressions are addressed in this frozen version. This is a scoped verdict, not overall integration acceptance: `review-runner.md` independently identifies evidence_kind relabeling/pairing and runner defects requiring fixes. Earlier reviews remain unchanged.

Targeted CPU probes ran against extracted frozen source in memory; no routine suite rerun and no claim of independently repeating the implementer's 23-test run. Synthetic records remain outside policy results.

| Finding | Observed result |
|---|---|
| STARTED/TERMINAL pairing | Both input orders return one success with zero interruption errors; unresolved STARTED remains visible; run hash mismatch raises. |
| NumPy booleans/dedup | True and false return 1/1 and 1/0. Duplicate terminals with NumPy-valued children deduplicate without JSON serialization failure. |
| Error identity validation | Wrong hash/stage and nested mixed-stage errors raise; explicit null real_policy stage/hash raises. |
| Parent-child identity | Conflicting task, setting, scene_seed, episode_id and shard_id each raise a specific envelope identity mismatch. |
| Conflicting terminal outcomes | COMPLETE_POLICY versus INFRA_ERROR for the same episode raises conflicting terminal records. |
| Status/count validation | Unknown status, negative top-level counts, negative nested counts and all-zero nested counts contradicting a successful child all raise. Consistent 1/1 report counts pass. |

Regression boundary probes also confirm ERROR envelopes retain a valid completed child plus visible failure, null video_path with NOT_REVIEWED remains accepted, and null with REVIEWED is rejected.

Reproduction: use the original review's in-memory loader with `review-aggregation-stable.txt`, the journal metadata additions and probe inputs documented in `review-aggregation-fixes.md`, and run both NumPy boolean values for duplicate terminals. The observed failures now are:

```text
null_identity: invalid stage in failure record
parent_scene_seed: report envelope identity mismatch for scene_seed
parent_episode_id: report envelope identity mismatch for episode_id
parent_shard_id: report envelope identity mismatch for shard_id
bad_counts: attempts must be an integer >= 0
inconsistent_counts: report results disagree with completed episodes for clean/lift_pot
numpy_duplicate_terminal true: attempts=1 successes=1 errors=[]
numpy_duplicate_terminal false: attempts=1 successes=0 errors=[]
```

No new blocker attributable to these six repairs was found. Native/GPU/model execution remains NOT RUN.
