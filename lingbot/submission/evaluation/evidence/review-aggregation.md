# Independent frozen aggregation review B — 2026-10-22

SPEC verdict: **CHANGES REQUIRED**. QUALITY verdict: **CHANGES REQUIRED**.

Scope: the entire `review-aggregation-snapshot.txt`, SHA256 `9442c8252ff12d6089c0c357232ceac8f2324c3a3e5424f1f92cf7794e1626c7`, containing aggregate_results.py, test_aggregation.py and support.py. This is the initial frozen version, not a verdict on concurrent live edits. Review inputs: lingbot/AGENTS.md, Complete Team Guide, CURRENT.md, B-EVALUATION-RESULTS.md, evaluation/IMPLEMENTATION-PLAN.md, SOURCE-AUDIT.md, official/results-template.json, the commissioning negative example and reference results_document implementation. No production files changed, routine suite rerun, native/GPU/model execution, dependency change or server access. All probe episodes below are synthetic CPU inputs, even where their schema field says real_policy; they are not policy evidence.

## Blocking Important findings

1. **Matched STARTED records are always reported as interrupted.** Frozen aggregate_results.py lines 260–263 (snapshot 261–264) immediately append an interrupted_started error, without pairing with a subsequent or preceding terminal. A STARTED and matching COMPLETE_POLICY terminal produce counts 1/1 plus interrupted_started. Directory traversal includes both files, so this affects the normal immutable ledger structure and prevents COMPLETE status even with full coverage. Pair identities after all inputs; retain only unresolved starts as interruption errors and reject inconsistent pairs.

2. **NumPy true and false cannot be aggregated.** Lines 32–39 and 208 (snapshot 33–40 and 209). Installed NumPy 2.5.0 identifies both np.bool_ scalar values with module numpy and class name bool; the name-only bool_ check rejects both with `ValueError: task_success must be a boolean`. On the older bool_ spelling, validation still returns the original NumPy objects in the record passed to json.dumps, which cannot serialize NumPy scalars. Normalize validated success and predicate to Python bool before dedup serialization, and cover both true and false.

3. **Non-complete records bypass fixed checkpoint/stage validation.** Lines 290–294 and 304–310 (snapshot 291–295 and 305–311). A valid baseline/hash-a success followed by a real_policy ERROR with candidate/hash-b returns baseline/hash-a output and records an error without rejecting the mixed identity. The same bypass occurs in envelope.errors and envelope.rejections. Unknown tasks/settings on these paths also bypass the shared identity validator. Validate supplied identity on every error/rejection path, including parent-child agreement, while retaining valid completed children of same-identity partial/error envelopes.

4. **Report envelope and child can describe different task/setting.** Lines 278–289 (snapshot 279–290) compare only stage and checkpoint SHA. An envelope for beat_block_hammer/randomized containing a lift_pot/clean child is accepted and counts the child with no error. Check all shared applicable identity fields, including task, setting, seed, episode and shard, rather than only two fields. Explicit scope-less aggregate envelopes can remain supported.

5. **Conflicting terminal outcomes are accepted for one immutable attempt.** Lines 264–275 and 209–215 (snapshot 265–276 and 210–216). A COMPLETE_POLICY terminal and an INFRA_ERROR (or REJECTED_SETUP) terminal with exactly the same identity are accepted as one success and one error; only completed episode payloads participate in conflict detection. Track terminal identity/outcome across all terminal kinds and reject conflicting records. The frozen test at snapshot 509–529 actually constructs COMPLETE and REJECTED_SETUP for the same attempt and expects acceptance; it should use a distinct rejected identity and add a conflict regression.

6. **Malformed report status/count metadata are silently accepted.** Lines 278–298 (snapshot 279–299). An envelope with `status='TYPO'` and a valid child returns 1/1 with no errors. An envelope with `status='COMPLETE', attempts=-1, successes=999` also returns 1/1 with no errors. The official output counts themselves are reconstructed correctly, but the promised fail-closed malformed-count/report validation is absent. Define accepted envelope status/count metadata and validate any supplied counts against child outcomes, or reject unsupported count metadata explicitly. An unknown status must not be silently treated as a clean envelope.

No Critical finding established. These are Important correctness/acceptance blockers, not claims about model quality or actual native results.

## Reproduction and observed output

Run the following from the workspace root in Python. It executes only the frozen aggregator source in memory, not the moving live file. `probe` prints the observed return or exception; it does not assert fabricated policy outcomes.

```python
from pathlib import Path
import types, json
s = Path('review-aggregation-snapshot.txt').read_text(encoding='utf-8-sig')
code = s.split('FILE lingbot\\submission\\evaluation\\aggregate_results.py\n', 1)[1].split('\nFILE ', 1)[0]
m = types.ModuleType('frozen_aggregation')
exec(compile(code, 'frozen_aggregation', 'exec'), m.__dict__)
t = json.loads(Path('lingbot/official/results-template.json').read_text())
sha = 'a' * 64
e = dict(evidence_kind='real_policy', status='COMPLETE', stage='baseline',
    checkpoint_manifest_sha256=sha, task='lift_pot', setting='clean',
    scene_seed=100000, episode_id='ep-a', shard_id='baseline-clean-lift_pot',
    task_success=True, task_predicate=True, actions_started=25, step_limit=50,
    official_step_limit=50, chunks=1, wall_seconds=12.5,
    log_path='logs/a.log', video_path='videos/a.mp4', requests=[dict(
        request_id=m.request_id_for('ep-a', 1), chunk_index=1, noise_seed=100000)])
terminal = {k: e[k] for k in m.IDENTITY_FIELDS}
terminal.update(record_type='TERMINAL', terminal_status='COMPLETE_POLICY', episode=e)
started = {k: e[k] for k in m.IDENTITY_FIELDS}
started['record_type'] = 'STARTED'
def probe(name, records):
    try:
        official, report = m.aggregate_records(records, t, sha, 'fixture-team')
        print(name, official['results']['clean']['lift_pot'],
              [v['kind'] for v in report['errors']], report['stage'])
    except Exception as error:
        print(name, type(error).__name__, str(error))
probe('matched_started_terminal', [started, terminal])
probe('conflicting_parent_cell', [dict(status='COMPLETE', stage='baseline',
    checkpoint_manifest_sha256=sha, task='beat_block_hammer',
    setting='randomized', episodes=[e])])
probe('malformed_envelope_counts', [dict(status='COMPLETE', stage='baseline',
    attempts=-1, successes=999, episodes=[e])])
probe('mixed_error_child', [e, dict(e, status='ERROR', stage='candidate',
    checkpoint_manifest_sha256='b'*64)])
probe('mixed_nested_errors', [dict(status='ERROR', episodes=[e], errors=[
    dict(e, status='ERROR', stage='candidate', checkpoint_manifest_sha256='b'*64)])])
probe('conflicting_terminal_outcomes', [terminal,
    dict(terminal, terminal_status='INFRA_ERROR', episode=None, error='crashed')])
probe('unknown_envelope_status', [dict(status='TYPO', episodes=[e])])
import numpy as np
print(np.__version__, type(np.bool_(True)).__module__, type(np.bool_(True)).__name__)
for value in (True, False):
    probe('numpy_' + str(value), [dict(e, task_success=np.bool_(value),
                                      task_predicate=np.bool_(value))])
```

Observed on this environment:

```text
matched_started_terminal counts=1/1 errors=[interrupted_started] stage=baseline
conflicting_parent_cell counts=1/1 errors=[] stage=baseline
malformed_envelope_counts counts=1/1 errors=[] stage=baseline
mixed_error_child counts=1/1 errors=[error] stage=baseline
mixed_nested_errors counts=1/1 errors=[failure] stage=baseline
conflicting_terminal_outcomes counts=1/1 errors=[failure] stage=baseline
unknown_envelope_status counts=1/1 errors=[] stage=baseline
2.5.0 numpy bool
numpy_True ValueError task_success must be a boolean
numpy_False ValueError task_success must be a boolean
```

## Remaining quality observations and boundaries

The completed-record path checks physical task/setting/seed duplicates, canonical per-chunk request IDs, finite elapsed time, integer action counts, predicate agreement and required provenance. Output construction uses all 100 template cells and integer attempt/success counts. Explicit fixture records and the actual commission negative example are excluded before counting. Completed children of an ERROR/PARTIAL envelope are retained. These useful properties do not cure the validation gaps above.

Two frozen test assertions also contradict their implementation/contracts: one episode at target=2 cannot mean one fully covered cell and 99 remaining cells (snapshot 502–507; correct values are 0 and 100), and a standalone real_policy ERROR is retained as an error while snapshot 577–581 expects it to raise. Inspection, not a rerun of the implementer's routine suite, establishes these contradictions. Align expected behavior and use identity-invalid error inputs for rejection checks.

The CLI directory reader has no path provenance attached to individual events (`source` stays None); this is a usability issue rather than an additional acceptance blocker. Real simulator completion, full action-limit authority, A-loader integration, real throughput and native interruption/resume remain NOT RUN and outside this frozen review. A later complete runner/ledger integration snapshot must be reviewed separately.
