"""Read-only M7 native-evidence review; never starts a simulator or resets a seed.

Requires Python 3.10, NumPy 1.26.4 and SciPy 1.10.1, matching measurement arithmetic.
Supply extracted final/pilot roots, both original archives and the resume log.
All replay work is local; only the separate --output directory receives writes.
"""
import argparse
import concurrent.futures
import hashlib
import json
import platform
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

if not __debug__:
    raise RuntimeError('Audit assertions require Python without -O')
WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / 'aura-sim/prototype_aether_cl'))
from aether_cl.m7_frozen import checked_trial, protocol, SEEDS, RATIOS, SOURCES, SCOPE, PROTOCOL_PATH
from aether_cl.m7_development import file_index
from aether_cl.m7_audit import compare
from aether_cl.m7_sweep import assess_pilot, plan
from aether_cl.m7_summary import summarize, write_csvs
import numpy as np
import scipy

if sys.version_info[:2] != (3, 10) or np.__version__ != '1.26.4' or scipy.__version__ != '1.10.1':
    raise RuntimeError('Use Python 3.10 / NumPy 1.26.4 / SciPy 1.10.1 for exact M7 arithmetic')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--pilot-evidence', type=Path, required=True)
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--pilot-archive', type=Path, required=True)
parser.add_argument('--resume-log', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--workers', type=int, default=8, choices=range(1, 17))
parser.add_argument('--check-inputs-only', action='store_true')
ARGS = parser.parse_args()
ROOT, PILOT_ROOT, OUT = ARGS.evidence.resolve(), ARGS.pilot_evidence.resolve(), ARGS.output.resolve()
for protected in (ROOT, PILOT_ROOT):
    if OUT == protected or protected in OUT.parents or OUT in protected.parents:
        raise ValueError('Output must be separate from both extracted evidence roots')
OUT.mkdir(parents=True, exist_ok=True)
REPORT = json.loads((ROOT / 'suite.json').read_text())
PILOT = json.loads((PILOT_ROOT / 'suite.json').read_text())
EXPECTED = json.loads((WORK / 'docs/research/experiments/evidence/AETHER_CL_M7_Native_Audit.json').read_text())

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def trial_review(index):
    item = REPORT['trials'][index]
    started = time.perf_counter()
    result, replay = checked_trial(ROOT / item['run_directory'], item, REPORT['native'])
    assert result == item['result'], ('parent child result', index)
    assert replay == item['audit'], ('parent audit', index)
    return {'index': index + 1, 'ratio': item['ratio'], 'seed': item['seed'], 'system': item['system'],
            **replay, 'review_seconds': time.perf_counter() - started}

def pair_jobs():
    lookup = {(t['ratio'], t['seed'], t['system']): t for t in REPORT['trials']}
    jobs = []
    for ratio in RATIOS:
        for seed in SEEDS:
            for left, right in (('baseline', 'v1'), ('v1', 'v2')):
                a, b = lookup[ratio, seed, left], lookup[ratio, seed, right]
                first = b['result']['recovery'].get('first_action_step') if right == 'v2' else None
                jobs.append({'ratio': ratio, 'seed': seed, 'systems': [left, right],
                             'left': a['run_directory'], 'right': b['run_directory'], 'stop': first - 1 if first else None})
            if ratio != 0:
                jobs.append({'ratio': ratio, 'seed': seed, 'systems': ['normal_baseline', 'disturbed_baseline'],
                             'left': lookup[0., seed, 'baseline']['run_directory'],
                             'right': lookup[ratio, seed, 'baseline']['run_directory'], 'stop': 430})
    return jobs

def pair_review(job):
    result = compare(ROOT / job['left'], ROOT / job['right'], job['stop'])
    return {'ratio': job['ratio'], 'seed': job['seed'], 'systems': job['systems'], **result}

def initial_checks():
    transfer = EXPECTED['transfer']
    assert digest(ARGS.archive) == transfer['archive_sha256']
    indexed = json.loads((ROOT / 'archive_index.json').read_text())['files']
    assert indexed == file_index(ROOT), 'Final file membership, size or SHA-256 differs'
    committed = json.loads(PROTOCOL_PATH.read_text())
    assert REPORT['protocol'] == committed == protocol() == json.loads((ROOT / 'protocol.json').read_text())
    assert REPORT['state'] == 'passed' and len(REPORT['trials']) == 360
    assert REPORT['scope'] == SCOPE and REPORT['fresh_native'] and REPORT['protocol_frozen']
    assert REPORT['model_training'] is False
    assert REPORT['native']['software']['git_commit'] == 'a51e5d2073c4033141b26e956804d593aa45d6df'
    assert REPORT['native']['software']['git_dirty'] is False
    assert REPORT['saved_archive'] == REPORT['archive'] == transfer['receipt']['archive']
    for item, trial in zip(plan(Path(REPORT['run_directory'])), REPORT['trials']):
        assert trial['state'] == 'passed' and all(trial[k] == v for k, v in item.items())
    assert Counter((t['ratio'], t['system']) for t in REPORT['trials']) == Counter({(r, s): 20 for r in RATIOS for s in ('baseline', 'v1', 'v2')})
    git_tree = EXPECTED['source_snapshots']
    snapshots = []
    for path in sorted((ROOT / 'source_snapshot').iterdir()):
        matches = [e for e in git_tree if e['path'].endswith('/' + path.name)]
        assert len(matches) == 1, path.name
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == matches[0]['git_blob'], path.name
        snapshots.append({'path': matches[0]['path'], 'git_blob': blob, 'sha256': hashlib.sha256(raw).hexdigest()})
    assert len(snapshots) == 15
    for name in SOURCES:
        assert digest(ROOT / 'source_snapshot' / name) == committed['sources_sha256'][name]
    inspection = json.loads((ROOT / 'source_snapshot/AETHER_CL_M7_Installed_Inspection.json').read_text())
    assert inspection['source_sha256'] == REPORT['native']['installed_sources_sha256']
    assert inspection['asset_sha256'] == REPORT['native']['installed_assets_sha256']
    assert digest(ROOT / 'source_snapshot/AETHER_CL_M7_Installed_Inspection.json') == REPORT['native']['inspection_receipt_sha256']
    for name, own_excluded in (('fresh_seed_history', False), ('resume_external_history', True)):
        history = REPORT[name]
        assert history['selected_overlap'] == [] and not set(history['recorded_reset_seeds']).intersection(SEEDS)
        assert history['own_validated_study_excluded'] is own_excluded
    assert REPORT['commissioning']['archive_sha256'] == committed['commissioning_archive_sha256']
    assert REPORT['native'] == PILOT['native'] and REPORT['trials'][:18] == PILOT['trials']
    pilot_hash = digest(ARGS.pilot_archive)
    assert pilot_hash == REPORT['immutable_pilot']['archive_sha256'] == '3ec98dea029d19d7237c6ff6579878c87d42d4992fe61563be340dcd62439c66'
    pilot_index = json.loads((PILOT_ROOT / 'archive_index.json').read_text())['files']
    assert pilot_index == file_index(PILOT_ROOT)
    retained = []
    for entry in pilot_index:
        if entry['path'].startswith(('ratio-', 'source_snapshot/')) or entry['path'] == 'protocol.json':
            path = ROOT / entry['path']
            assert path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'], entry['path']
            retained.append(entry)
    assert len(retained) == REPORT['immutable_pilot']['raw_child_source_protocol_files_retained'] == 106
    log = ARGS.resume_log.read_text()
    starts = [line for line in log.splitlines() if line.startswith('START ')]
    ends = [line for line in log.splitlines() if line.startswith('END ')]
    assert len(starts) == len(ends) == 342
    for number, trial, start, end in zip(range(19, 361), REPORT['trials'][18:], starts, ends):
        assert start == f"START {number}/360 ratio={trial['ratio']} seed={trial['seed']} {trial['system']}"
        r = trial['result']
        assert end == (f"END success={r['task_success_at_end']} legacy_velocity_success={r['final_reference']['legacy_velocity_task_success']} "
                       f"depth_mm={r['final_reference']['depth_m']*1000:.3f} recovery={r['recovery']['state']}")
    assert 'M7_FROZEN_EVIDENCE_VALID' in log.splitlines()
    assert 'Archive SHA-256: ' + transfer['archive_sha256'] in log.splitlines()
    print('INITIAL_IDENTITY_HASH_PILOT_LOG_CHECKS_PASS', len(indexed), 'final files', len(pilot_index), 'pilot files', len(retained), 'immutable raw files', flush=True)
    return {'transfer': transfer, 'final_index': indexed, 'pilot_index': pilot_index, 'retained_pilot_files': retained,
            'source_snapshots': snapshots, 'protocol_sha256': digest(PROTOCOL_PATH)}

def main():
    data = initial_checks()
    if ARGS.check_inputs_only:
        (OUT / 'input_review.json').write_text(json.dumps(data, indent=2) + '\n')
        print('M7_INPUT_CHECKS_ONLY_PASS; no controller replay claimed', flush=True)
        return
    completed = OUT / 'completed_replays.json'
    reviews = {}
    indices = list(range(360))
    with concurrent.futures.ProcessPoolExecutor(max_workers=ARGS.workers) as pool:
        futures = {pool.submit(trial_review, i): i for i in indices}
        for future in concurrent.futures.as_completed(futures):
            row = future.result(); reviews[row['index']] = row
            completed.write_text(json.dumps(sorted(reviews.values(), key=lambda r: r['index']), indent=2) + '\n')
            print('REPLAY', row['index'], row['seed'], row['ratio'], row['system'], 'PASS', f"{len(reviews)}/360", f"{row['review_seconds']:.2f}s", flush=True)
    ordered = sorted(reviews.values(), key=lambda r: r['index'])
    assert len(ordered) == 360 and all(r['passed'] for r in ordered)
    print('ALL360_REPLAYS_PASS', flush=True)
    jobs = pair_jobs()
    assert len(jobs) == 340
    pairs = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=ARGS.workers) as pool:
        for result in pool.map(pair_review, jobs):
            pairs.append(result)
            if len(pairs) % 20 == 0:
                print('PAIRS_PASS', len(pairs), '/340', flush=True)
    assert pairs == REPORT['pairs'] and all(p['passed'] for p in pairs)
    assert Counter(tuple(p['systems']) for p in pairs) == Counter({('baseline', 'v1'): 120, ('v1', 'v2'): 120, ('normal_baseline', 'disturbed_baseline'): 100})
    print('ALL340_EXACT_PAIRS_PASS', flush=True)
    summary = summarize(REPORT['trials'], SEEDS, RATIOS)
    assert summary == REPORT['summary'], 'Final aggregate report differs'
    csv_rows = []
    with tempfile.TemporaryDirectory() as temporary:
        write_csvs(Path(temporary), summary)
        for name in ('episodes.csv', 'curve.csv', 'paired.csv'):
            assert (ROOT / name).read_bytes() == (Path(temporary) / name).read_bytes(), name
            csv_rows.append({'name': name, 'sha256': digest(ROOT / name)})
    pilot_pairs = [p for p in pairs if p['seed'] in (140, 141) and p['ratio'] in (0., .5, 2.)]
    assert pilot_pairs == PILOT['pairs']
    gate = assess_pilot({**REPORT, 'trials': REPORT['trials'][:18], 'pairs': pilot_pairs})
    assert gate == REPORT['pilot_gate'] == PILOT['pilot_gate'] and gate['passed']
    data.update(audit_tool_sha256=digest(__file__), name='M7 frozen native independent audit', review_date_utc='2026-10-08',
        native_measurement_commit=REPORT['native']['software']['git_commit'], documentation_base_commit='c04ef54c76a2dcfd7f10b6d9a63e4815c9977847',
        native=REPORT['native'], commissioning=REPORT['commissioning'], fresh_seed_history=REPORT['fresh_seed_history'],
        resume_external_history=REPORT['resume_external_history'], immutable_pilot=REPORT['immutable_pilot'],
        auditor_versions={'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
        trials=ordered, pairs=pairs, total_actions=sum(r['steps'] for r in ordered),
        physics_substep_samples=sum(r['physics_substep_samples'] for r in ordered),
        raw_endpoint_reconstructions=sum(r['raw_endpoint_reconstructions'] for r in ordered),
        maximum_action_replay_error=max(r['maximum_action_replay_error'] for r in ordered),
        summary_exact=True, csv_bytes_exact=True, csvs=csv_rows, pilot_gate=gate,
        analysis_unit='20_common_reset_scenes_reused_across_six_conditions_and_three_systems_not360_independent_scenes',
        all360_retained=True, exclusions=0, seed_replacements=0, model_training=False, passed=True,
        limitations='privileged state; synthetic waypoint misalignment; one rigid peg and arm; external physics samples, no post-release or sensor verification')
    (OUT / 'native_audit.json').write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    print('M7_INDEPENDENT_NATIVE_AUDIT_PASS', data['total_actions'], 'actions', data['physics_substep_samples'], 'samples', flush=True)

if __name__ == '__main__':
    main()
