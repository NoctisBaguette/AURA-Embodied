"""Read-only M8 first18 archive reconstruction; run with matching NumPy/SciPy.

Arguments: repository archive log extraction-directory authoritative-blob-map receipt.
The extraction is checked for membership and hashes on every invocation. Archived
absolute native paths remain configuration evidence; reads use the extracted tree.
No simulator is constructed and no controller/scorer or tolerance is changed.
"""
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
from collections import Counter

repo, archive, log_path, destination, blob_map_path, receipt_path = map(Path, sys.argv[1:])
sys.path.insert(0, str(repo / 'aura-sim/prototype_aether_cl'))
from aether_cl import m8_frozen as frozen, m8_sweep as sweep
from aether_cl.m8_matched import legacy_config, LEGACY_SYSTEM, audit_gate
from aether_cl.m6r_audit import check_trial
from aether_cl.acceptance import load_trial
from aether_cl.runtime import json_value

def read(path):
    return json.loads(path.read_text())

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

digest = sha(archive.read_bytes())
assert digest == '535218e74854326946a157f8aa620aa1ca41db78351097074074702cd49d295c'
head = 'e8184217dc4b3c205666787441b87b13ba8a489c'
with tarfile.open(archive) as bundle:
    members = bundle.getmembers()
    assert len({m.name for m in members}) == len(members)
    for member in members:
        path = PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts
        assert path.parts[0] == sweep.ARCHIVE_ROOT and (member.isfile() or member.isdir())
    if not destination.exists():
        destination.mkdir()
        bundle.extractall(destination, filter='data')
study = destination / sweep.ARCHIVE_ROOT
index = frozen.verify_index(study)
assert {str(p.relative_to(study)) for p in study.rglob('*') if p.is_file()} == set(index) | {'file_index.json'}
suite = read(study / 'suite.json')
assert suite['state'] == 'paused_first18' and suite['scope'] == frozen.SCOPE and suite['confirmatory']
assert suite['fresh_study_started'] and suite['force_family_frozen_for_fresh_study']
assert not suite['performance_success_gate'] and not suite['model_training']
assert suite['next_boundary'] == 'independent_pilot_review_before342'
assert suite['plan'] == sweep.plan() and len(suite['plan']) == 360 and len(suite['trials']) == 18
protocol = frozen.protocol()
assert suite['protocol'] == protocol == read(frozen.PROTOCOL_PATH)
assert frozen.sha256(frozen.PROTOCOL_PATH) == '3e67b43747b4d52b73b39c64d2b1f159a855f91cde012b8a5ceffbaf6c40a031'
native_root = Path('/home/jiangle/aura-work/AURA-Embodied-offline/aura-sim/prototype_aether_cl/runs/m8-placement-seeds160-179')
assert suite['output_path'] == str(native_root)
assert suite['archive_path'] == '/home/jiangle/aura-work/aether-cl-m8-placement-seeds160-179.tar.gz'
assert suite['pilot_archive'] == suite['saved_archive'] == '/home/jiangle/aura-work/aether-cl-m8-placement-seeds160-179-pilot.tar.gz'
sweep.verify_snapshots(study)
git_blobs = read(blob_map_path)
snapshots = []
for p in sorted((study / 'sources').iterdir()):
    candidates = [repo / 'aura-sim/prototype_aether_cl/aether_cl' / p.name,
                  repo / 'docs/research/experiments/evidence' / p.name,
                  repo / 'tools' / p.name]
    current = next(c for c in candidates if c.exists())
    raw = p.read_bytes()
    assert raw == current.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    path = str(current.relative_to(repo))
    assert git_blobs[path] == blob
    snapshots.append({'name': p.name, 'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'git_blob': blob})
assert len(snapshots) == 21
identity = suite['identity']
assert identity['software']['git_commit'] == head and not identity['software']['git_dirty']
commissioned = frozen.reviewed_commission()['native_identity']
assert {k:v for k,v in identity['software'].items() if k != 'git_commit'} == {k:v for k,v in commissioned['software'].items() if k != 'git_commit'}
for key in ('receipt_sha256', 'installed_sources_sha256', 'accepted_placement_sources_sha256',
            'sapien_binaries', 'development_sources_sha256', 'response_review_sha256', 'dose_review_sha256'):
    assert identity[key] == commissioned[key]
assert identity['development_stage'] == 'frozen_fresh_M8'
assert identity['study_sources_sha256'] == protocol['sources_sha256']
assert identity['commissioning_review_sha256'] == frozen.REVIEW_SHA256
assert identity['startup_environment_sha256'] == frozen.environment_digest(suite['environment'])
assert not set(suite['environment']) & set(frozen.SESSION_FIELDS)
for key in ('accepted_placement_sources_sha256','development_sources_sha256','study_sources_sha256'):
    for name, h in identity[key].items():
        assert frozen.sha256(study / 'sources' / name) == h
history = suite['seed_history']
assert history['selected_seeds'] == list(frozen.SEEDS) and history['preferred_seeds'] == list(frozen.SEEDS)
assert history['selected_overlap'] == history['preferred_overlap'] == []
assert not set(history['recorded_reset_seeds']) & set(frozen.SEEDS)
assert history['selection_frozen'] and history['fresh_entry_must_recheck'] and not history['own_validated_study_excluded']
assert history['event_files_checked'] == 3216 and history['reset_records'] == 5719
assert history['development_seed100_witness'] and re.fullmatch('[0-9a-f]{64}', history['reset_index_sha256'])
commission_report = repo.parent / 'm8_matched_review_v1/m8-force-commission/suite.json'
assert suite['commissioning_validation'] == {
    'archive_sha256': frozen.COMMISSION_ARCHIVE_SHA256, 'producer_commit': frozen.COMMISSION_COMMIT,
    'indexed_files': 412, 'replayed_trials': 36, 'comparisons': 34,
    'review_sha256': frozen.REVIEW_SHA256, 'report_sha256': frozen.sha256(commission_report)}
outcomes = []
actions = samples = force_calls = gate_actions = 0
for item, trial in zip(sweep.plan()[:18], suite['trials']):
    directory = sweep.directory(item)
    assert all(trial[k] == v for k,v in item.items())
    assert trial['directory'] == directory and trial['output'] == str(native_root / directory) and trial['returncode'] == 0
    case = study / directory
    carrier, manifest = read(case / 'm8_result.json'), read(case / 'm8_manifest.json')
    assert carrier == trial['result'] and carrier['state'] == 'finished_valid_frozen_evidence'
    expected = legacy_config(native_root / directory, item['seed'], item['system'])
    assert carrier['native_config'] == manifest['legacy_config'] == json_value(asdict(expected))
    assert carrier['confirmatory'] and manifest['confirmatory']
    assert carrier['scope'] == manifest['scope'] == frozen.SCOPE
    assert manifest['output'] == trial['output'] and manifest['legacy_system_mapping'] == LEGACY_SYSTEM
    assert all(carrier[k] == manifest[k] == item[k] for k in ('seed','system','point_id'))
    assert all(manifest[k] == v for k,v in identity.items())
    assert manifest['preregistration'] == {'protocol_sha256': frozen.sha256(frozen.PROTOCOL_PATH), 'authority_commit': frozen.AUTHORITY}
    assert manifest['point'] == next(p for p in protocol['points'] if p['point_id'] == item['point_id'])
    assert manifest['motor_command_authority'] == 'accepted_runner_only_instrumentation_replay_must_match'
    native = (case / carrier['run_relative']).resolve()
    assert native.is_relative_to(case.resolve() / 'native')
    replay = check_trial(native, expected, identity['software'])
    physical = frozen.audit_physics(case, carrier, manifest['point'])
    gate = audit_gate(case, carrier)
    for name, audit in (('accepted_runner_replay.json', replay), ('physics_audit.json', physical), ('controller_gate_audit.json', gate)):
        assert audit['passed'] and json_value(audit) == read(case / name), (directory, name)
    assert replay['max_action_replay_error'] == 0
    nm, nr, events = load_trial(native)
    assert nm['upstream_sources_sha256'] == {n: identity['installed_sources_sha256'][n.removeprefix('mani_skill.').replace('.', '/') + '.py'] for n in nm['upstream_sources_sha256']}
    assert nr['episodes'] == [carrier['episode']] and nr['evaluation']['verification_metrics'] == carrier['verification_metrics']
    assert physical['effects'] == carrier['physical_effects'] and carrier['physical_force_applied'] == bool(physical['force_calls'])
    diagnostics = sweep.physical_diagnostics(case, carrier)
    assert diagnostics == trial['physical_diagnostics']
    steps = [e for e in events if e['event'] == 'step']
    assert len(steps) == 800 and not carrier['episode']['excluded']
    actions += len(steps); samples += physical['external_physics_samples']; force_calls += physical['force_calls']; gate_actions += gate['matched_actions']
    effects = {k:v for k,v in physical['effects'].items() if k not in ('before_pulse','after_pulse')}
    outcomes.append({**item, 'command_force_y_n': manifest['point']['command_force_y_n'],
                     'episode': carrier['episode'], 'verification_metrics': carrier['verification_metrics'],
                     'physical_effects': effects, 'physical_diagnostics': diagnostics,
                     'max_action_replay_error': replay['max_action_replay_error'], 'controller_gate_actions': gate['matched_actions']})
    print('AUDITED', item['slot'] + 1, item['point_id'], item['seed'], item['system'], flush=True)
comparisons = frozen.comparisons(suite['trials'], study)
counts = dict(Counter(c['kind'] for c in comparisons))
assert counts == protocol['pilot_comparison_counts'] and len(comparisons) == 16 and all(c['passed'] for c in comparisons)
summary = sweep.summarize(suite['trials'])
assert suite['pilot_gate'] == {'passed': True, 'performance_gate': False, 'complete_trial_replays': 18,
                             'comparison_counts': counts, 'comparisons': comparisons, 'summary': summary}
assert suite['summary'] == summary
csv_stream = io.StringIO(newline='')
writer = csv.DictWriter(csv_stream, fieldnames=summary['cells'][0]); writer.writeheader(); writer.writerows(summary['cells'])
assert csv_stream.getvalue().encode() == (study / 'cells.csv').read_bytes()
assert all(c['success_rate_requested'] is None and c['success_rate_eligible'] is None for c in summary['cells'])
log = log_path.read_text()
starts = re.findall(r'^START (\d+)/360 (\S+) seed(\d+) (\S+)$',log,re.M)
ends = re.findall(r'^END (\d+)/360 (\S+)$',log,re.M)
assert len(starts) == len(ends) == 18
for i, (start, end, item) in enumerate(zip(starts, ends, sweep.plan()[:18]), 1):
    assert start == (str(i), item['point_id'], str(item['seed']), item['system'])
    assert end == (str(i), 'finished_valid_frozen_evidence')
assert sweep.PILOT_READY in log and f'SHA-256: {digest}' in log and 'M8_ERROR_RETAIN_EVIDENCE' not in log
totals = {**summary['totals'], 'indexed_files': len(index), 'source_snapshots': 21,
          'replayed_control_actions': actions, 'independently_checked_physics_samples': samples,
          'matched_controller_gate_actions': gate_actions, 'engine_force_calls': force_calls, 'matched_comparisons': 16,
          'remaining_unstarted_episodes': 342,
          'successes_by_system': {s:sum(o['episode']['task_success_at_end'] for o in outcomes if o['system'] == s) for s in frozen.SYSTEMS},
          'v2_attempts':sum(o['episode']['recovery']['attempts'] for o in outcomes if o['system'] == 'v2'),
          'successful_recovery_episodes':sum(o['episode']['recovery_task_success'] for o in outcomes if o['system'] == 'v2')}
assert actions == gate_actions == 14400 and samples == 72000 and force_calls == 60
receipt = {'schema_version': 1, 'scope': 'M8_fresh_first18_independent_pilot_review',
           'measurement_commit': head, 'archive_name': archive.name, 'archive_bytes': archive.stat().st_size,
           'archive_sha256': digest, 'log_sha256': frozen.sha256(log_path),
           'protocol_sha256': frozen.sha256(frozen.PROTOCOL_PATH), 'all_audit_checks_passed': True,
           'performance_gate': False, 'M8_complete': False, 'M8_02_accepted': False,
           'totals': totals, 'source_snapshots': snapshots, 'native_identity': identity,
           'history': {k:history[k] for k in ('event_files_checked','reset_records','reset_index_sha256','selected_seeds','selected_overlap','scope')},
           'history_validation_limit': 'Recorded retained-history guard and fingerprint verified; the full remote historical event corpus is not included in this upload.',
           'commissioning_validation': suite['commissioning_validation'], 'comparisons': comparisons,
           'outcomes': outcomes, 'summary': summary,
           'checks': {'safe_unique_archive_complete_index': True, 'all21_snapshot_git_blobs_at_measurement_commit': True,
                      'protocol_plan_native_identity_environment_digest': True, 'all18_native_configuration_and_source_identities': True,
                      'all18_action_task_verifier_recovery_path_replays_exact': True, 'all18_physics_and_controller_gate_replays_exact': True,
                      'all16_exact_matched_comparisons': True, 'physical_diagnostics_summary_and_csv_regenerate_exactly': True,
                      'all18_log_start_end_slots_archive_hash_and_ready_marker': True,
                      'no_initial_goal_exclusions_or_missed_force_preconditions': all(o['physical_effects']['release_support_precondition'] and o['physical_effects']['force_calls'] == 5 for o in outcomes if o['point_id'] != 'normal')},
           'resume': {'expected_head': head, 'pilot_sha256': digest, 'unstarted_episodes': 342,
                      'retain_original18': True, 'retune_or_replace': False},
           'limitations': 'Two fresh common scenes and three of six frozen conditions; not the complete20-scene robustness curve. No training, physical robot execution or non-privileged perception.',
           'replay_environment': {'python': sys.version.split()[0], 'numpy': __import__('numpy').__version__, 'scipy': __import__('scipy').__version__}}
assert all(receipt['checks'].values())
receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
print('AUDIT_ALL_PASS', json.dumps(totals), 'receipt_sha256', frozen.sha256(receipt_path), flush=True)
