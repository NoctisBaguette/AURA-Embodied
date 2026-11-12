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

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / 'AURA-Embodied/aura-sim/prototype_aether_cl'))
from aether_cl.m7_frozen import checked_trial, protocol, SEEDS, RATIOS, SOURCES, SCOPE, PROTOCOL_PATH
from aether_cl.m7_development import file_index
from aether_cl.m7_audit import compare
from aether_cl.m7_sweep import assess_pilot, plan
from aether_cl.m7_summary import summarize, write_csvs
import numpy as np
import scipy

OUT = Path(__file__).resolve().parent
ROOT = OUT / 'm7-insertion-seeds140-159'
REPORT = json.loads((ROOT / 'suite.json').read_text())
PILOT_ROOT = WORK / 'm7_pilot_audit/m7-insertion-seeds140-159'
PILOT = json.loads((PILOT_ROOT / 'suite.json').read_text())

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
    transfer = json.loads((OUT / 'transfer_review.json').read_text())
    assert digest(OUT / 'aether-cl-m7-insertion-seeds140-159.tar.gz') == transfer['archive_sha256']
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
    git_tree = json.loads((OUT / 'git_tree.json').read_text())['tree']
    snapshots = []
    for path in sorted((ROOT / 'source_snapshot').iterdir()):
        matches = [e for e in git_tree if e['type'] == 'blob' and e['path'].endswith('/' + path.name)]
        assert len(matches) == 1, path.name
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == matches[0]['sha'], path.name
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
    pilot_hash = digest(WORK / 'upload/aether-cl-m7-insertion-seeds140-159-pilot.tar.gz')
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
    log = (WORK / 'upload/m7-insertion-seeds140-159-resume.log').read_text()
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
    completed = OUT / 'completed_replays.json'
    previous = json.loads(completed.read_text()) if completed.exists() else []
    reviews = {row['index']: row for row in previous}
    indices = [i for i in range(360) if i + 1 not in reviews]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
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
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
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
    data.update(name='M7 frozen native independent audit', review_date_utc='2026-10-08',
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
