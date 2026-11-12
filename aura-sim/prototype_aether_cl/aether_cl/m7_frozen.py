"""Frozen M7 configuration, source guards and isolated fresh-seed episode entry."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import tarfile

from .m7_runtime import run, preflight_native, SYSTEMS
from .m7_task import task_manifest
from .m7_policy import PHASES, DURATIONS, INJECTION_STEP, MAX_STEPS, RecoverySettings
from .m7_audit import replay, suite_pairs
from .m7_development import file_index, history_guard
from .m5_attribution import VOLATILE_ENVIRONMENT

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / 'docs/research/experiments/evidence/AETHER_CL_M7_Insertion_Protocol.json'
REVIEW_PATH = ROOT / 'docs/research/experiments/evidence/AETHER_CL_M7_Candidates_v5_Review.json'
SEEDS = tuple(range(140, 160))
RATIOS = (0., .5, 1., 2., 4., 8.)
SCOPE = 'm7_seed140_159_contact_rich_insertion'
COMMISSION_SHA256 = '21b58777ce05db80edd35c24457f7778dd2edbacfab729adb94005c7ff4f3f68'
COMMISSION_COMMIT = 'fff75c25f2b5d1dc01a224be86a4cb60b1152afb'
SOURCES = ('m7_task.py', 'm7_policy.py', 'm7_runtime.py', 'm7_audit.py', 'm7_development.py',
           'm7_frozen.py', 'm7_sweep.py', 'm7_summary.py', 'policies.py', 'runtime.py', 'verification.py')
SESSION_FIELDS = (*VOLATILE_ENVIRONMENT, 'XDG_SESSION_ID')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def frozen_contract():
    return {**task_manifest(), 'status': 'frozen_before_fresh_native_M7'}


def protocol():
    return {
        'name': SCOPE, 'date': '2026-10-07', 'authority': 'DEC-0006 and M6R 02 acceptance',
        'authority_commit': '145aadce249b23a49ecb899ff273e93f673dd03b',
        'seeds': list(SEEDS), 'systems': list(SYSTEMS), 'clearance_ratios': list(RATIOS),
        'nominal_magnitudes_m': [r * .003 for r in RATIOS],
        'actual_magnitude': 'ratio_times_reset_hole_radius_minus_peg_half_width; log achieved object_target offset',
        'requested_episodes': 360, 'cells': 18, 'episodes_per_cell': 20, 'max_steps': MAX_STEPS,
        'analysis_unit': '20_common_seed_scenes_reused_across_conditions_and_systems_not360_independent_scenes',
        'seed_selection': 'fresh140_159_only_if_retained_native_history_unused_no_adaptive_replacement',
        'task': 'PegInsertionSide-v1', 'robot': 'panda_wristcam', 'physics_backend': 'cpu',
        'observation_mode': 'state_dict', 'control_mode': 'pd_ee_pose', 'reward_mode': 'none', 'render': False,
        'task_contract': frozen_contract(), 'nominal_phases': list(PHASES), 'nominal_durations': list(DURATIONS),
        'nominal_source': 'commissioned_v5_motion_identical_source_no_new_action_or_transition_logic',
        'legacy_primitive_manifest_names': 'retained_producer_identifiers_enclosed_by_this_frozen_protocol',
        'recovery_settings': {**asdict(RecoverySettings()), 'stage_caps': list(RecoverySettings().stage_caps)},
        'recovery_attempts_maximum': 1,
        'recovery': 'backout_once_geometry_refresh_realign_reinsert_then_ten_eligible_pose_windows',
        'injection_step': INJECTION_STEP, 'injection_axis': 'hole_local_positive_y',
        'injection': 'synthetic_cached_nominal_waypoint_bias_before_contact_no_force_or_actor_teleport',
        'injection_precondition': 'acquired_calibrated_entire_peg40mm_before_entry_orientation_and_projected_fit_contact_force_at_most0.05N',
        'missed_injection_or_earlier_failure': 'retained_outcome_no_exclusion_replacement_or_second_recovery',
        'pilot': {'episodes': 18, 'ratios': [0., .5, 2.], 'seeds': [140, 141],
                  'order': 'ratio_then_seed_then_baseline_v1_v2', 'retained_in_final': True,
                  'gate': 'replay_identity_pairs_one_healthy_normal_baseline_and_precontact_injections_no_v2_success_gate'},
        'remaining_order': 'ratio_ascending_seed_ascending_system_order_skip_only_completed_pilot_slots',
        'comparison_counts': {'passive': 120, 'recovery': 120, 'control': 100},
        'pilot_comparison_counts': {'passive': 6, 'recovery': 6, 'control': 4},
        'action_replay_tolerance': 3e-7, 'derived_scalar_replay_tolerance': 1e-10,
        'physical_pair_tolerance': 'exact_including_all_physics_substeps_no_relaxation',
        'execution': 'fresh_python_interpreter_and_simulator_per_slot_all1200_actions',
        'model_training': False, 'performance_gate': 'none_after_pilot_task_failures_are_retained',
        'resume': 'only_unstarted_slots_from_valid_paused_checkpoint_full_hash_replay_identity_and_immutable_pilot_checks',
        'session_fields_removed_from_child_environment': list(SESSION_FIELDS),
        'environment': 'all_other_values_passed_to_children_and_hashed_unchanged_including_CUDA_and_LD_paths',
        'commissioning_archive_sha256': COMMISSION_SHA256, 'commissioning_commit': COMMISSION_COMMIT,
        'commissioning_review_sha256': sha256(REVIEW_PATH),
        'installed_inspection_receipt_sha256': sha256(ROOT / 'docs/research/experiments/evidence/AETHER_CL_M7_Installed_Inspection.json'),
        'sources_sha256': {name: sha256(Path(__file__).with_name(name)) for name in SOURCES},
        'history_guard_source_sha256': sha256(ROOT / 'tools/m7_task_inspection.py'),
        'old_sources': 'unchanged_M0_M6R_preflight_chain',
        'return_boundary': 'after_frozen_native_M7_audit_return_to02_before_any_further_scope',
        'limitations': 'privileged_state_synthetic_lateral_bias_one_peg_one_arm_no_force_disturbance_sensor_verifier_or_learning'
    }


def preflight():
    from .m6r_sweep import preflight as old_preflight
    old_preflight()
    expected = protocol()
    if json.loads(PROTOCOL_PATH.read_text()) != expected:
        raise ValueError('M7 sources/protocol differ from frozen preregistration')
    return expected


@dataclass(frozen=True)
class M7FreshConfig:
    seed: int = 140
    system: str = 'baseline'
    offset_clearance_ratio: float = 0.
    output: Path = Path('runs/m7-fresh-child')

    def validate(self):
        if type(self.seed) is not int or self.seed not in SEEDS or self.system not in SYSTEMS or self.offset_clearance_ratio not in RATIOS:
            raise ValueError('Frozen M7 accepts only preselected140-159, matched systems and frozen ratios')


def preregistration():
    return {'name': SCOPE, 'protocol_sha256': sha256(PROTOCOL_PATH),
            'authority_commit': '145aadce249b23a49ecb899ff273e93f673dd03b'}


def run_fresh(config, suite_path):
    preflight()
    report = json.loads(Path(suite_path).read_text())
    native = preflight_native()
    last = report['trials'][-1] if report.get('trials') else {}
    expected = {'seed': config.seed, 'system': config.system, 'ratio': config.offset_clearance_ratio,
                'output': str(config.output.resolve())}
    if (report.get('state') != 'running' or report.get('runner_pid') != os.getppid()
            or report.get('protocol') != protocol() or report.get('native') != native
            or last.get('state') != 'running' or any(last.get(k) != v for k,v in expected.items())):
        raise ValueError('Fresh episode must be the selected slot of its live guarded sweep parent')
    return run(config, preflight_fn=lambda:native, development_only=False,
               task_contract_fn=frozen_contract, preregistration=preregistration())


def checked_trial(directory, item, native):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    result = json.loads((directory / 'result.json').read_text())
    expected_config = {'seed': item['seed'], 'system': item['system'],
                       'offset_clearance_ratio': item['ratio'], 'output': item['output']}
    if manifest['config'] != expected_config or result['config'] != expected_config:
        raise ValueError('Fresh child configuration differs from selected slot')
    if any(manifest.get(k) != v for k,v in native.items()):
        raise ValueError('Fresh child software/source/startup identity differs from parent')
    if manifest.get('development_only') is not False or manifest.get('fresh_native') is not True:
        raise ValueError('Fresh manifest has incorrect execution scope')
    if result.get('development_only') is not False or result.get('fresh_native') is not True:
        raise ValueError('Fresh result has incorrect execution scope')
    if manifest.get('preregistration') != preregistration():
        raise ValueError('Fresh child preregistration differs')
    return result, replay(directory, config_type=M7FreshConfig, task_contract_fn=frozen_contract)


def validate_commission(report_path, archive_path):
    report_path, archive_path = Path(report_path), Path(archive_path)
    root = report_path.parent
    report = json.loads(report_path.read_text())
    receipt = json.loads(REVIEW_PATH.read_text())
    if sha256(archive_path) != COMMISSION_SHA256:
        raise ValueError('Commissioning archive differs from independently reviewed evidence')
    if report['state'] != 'passed' or report['fresh_native'] or report['protocol_frozen'] or not report['candidate_series']:
        raise ValueError('Expected completed known-seed candidate commissioning')
    selected = [{'ratio':r,'seed':s,'system':system} for r in RATIOS for s in (100,101) for system in SYSTEMS]
    if report['selected'] != selected or len(report['trials']) != 36 or report['native']['software']['git_commit'] != COMMISSION_COMMIT:
        raise ValueError('Commissioning selection or producer identity differs')
    indexed = json.loads((root/'archive_index.json').read_text())['files']
    if indexed != file_index(root):
        raise ValueError('Commissioning raw files differ from retained index')
    with tarfile.open(archive_path) as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith('/archive_index.json'))
        if json.load(tar.extractfile(member))['files'] != indexed:
            raise ValueError('Commissioning live index differs from independently reviewed immutable archive')
    for entry in receipt['execution_sources']:
        if sha256(root/'source_snapshot'/Path(entry['path']).name) != entry['sha256']:
            raise ValueError('Commissioning archived source differs')
    for item, trial in zip(selected, report['trials']):
        if any(trial.get(k) != v for k,v in item.items()):
            raise ValueError('Commissioning trial ordering differs')
        directory = root/trial['run_directory']
        manifest = json.loads((directory/'manifest.json').read_text())
        result = json.loads((directory/'result.json').read_text())
        if result != trial['result'] or any(manifest.get(k) != v for k,v in report['native'].items()):
            raise ValueError('Commissioning child copies or native identity differ')
        replay(directory)
    if suite_pairs(report['trials'], root, include_controls=True) != receipt['archived_source_replay']['pairs']:
        raise ValueError('Commissioning strict pairs differ from independent review')
    native = preflight_native()
    for field in ('installed_sources_sha256','installed_assets_sha256','inspection_receipt_sha256'):
        if native[field] != report['native'][field]:
            raise ValueError('Frozen installed environment differs from commissioning')
    return {'archive_sha256':COMMISSION_SHA256,'producer_commit':COMMISSION_COMMIT,
            'indexed_files':len(indexed),'replayed_trials':36,'strict_pairs':34,
            'report_sha256':sha256(report_path),'review_sha256':sha256(REVIEW_PATH)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--seed',type=int,choices=SEEDS,required=True)
    cli.add_argument('--system',choices=SYSTEMS,required=True)
    cli.add_argument('--offset-clearance-ratio',type=float,choices=RATIOS,required=True)
    cli.add_argument('--output',type=Path,required=True)
    cli.add_argument('--suite',type=Path,required=True,help='Live guarded sweep authorization; standalone fresh resets are blocked')
    args = cli.parse_args()
    values = vars(args); suite = values.pop('suite')
    result = run_fresh(M7FreshConfig(**values), suite)
    print(json.dumps({k:result[k] for k in ('state','run_directory','task_success_at_end')},allow_nan=False),flush=True)


if __name__ == '__main__':
    main()
