"""Read-only M8 diagnostics. Arguments: repository extracted-study output-json.

The full audit independently reconstructs the native summaries first. This
companion reports descriptive costs, phase failures and actual force response.
No intervention or threshold is selected from these outcomes.
"""
from collections import Counter
import json
from pathlib import Path
import statistics
import sys
import numpy as np

repo, study, output = map(Path, sys.argv[1:])
sys.path.insert(0, str(repo / 'aura-sim/prototype_aether_cl'))
from aether_cl.m6_policy import FixedPlacement, rotation_angle
from aether_cl.policies import pose_rotation, vector

suite = json.loads((study / 'suite.json').read_text())
trials, pairs = suite['trials'], suite['summary']['paired_outcomes']
lookup = {(t['seed'],t['point_id'],t['system']):t for t in trials}

def describe(values):
    values = [v for v in values if v is not None]
    return {'count':len(values),'minimum':min(values) if values else None,
            'median':statistics.median(values) if values else None,
            'mean':statistics.mean(values) if values else None,'maximum':max(values) if values else None}

cells = []
for point in suite['protocol']['points']:
    p = point['point_id']
    group = [r for r in pairs if r['point_id'] == p]
    v2 = [lookup[s,p,'v2']['result']['episode'] for s in suite['protocol']['seeds']]
    baseline = [lookup[s,p,'baseline'] for s in suite['protocol']['seeds']]
    cells.append({'point_id':p,'command_force_y_n':point['command_force_y_n'],
                  'successes':{y:sum(lookup[s,p,y]['result']['episode']['task_success_at_end'] for s in suite['protocol']['seeds']) for y in suite['protocol']['systems']},
                  'v2_rescues':sum(r['v2_rescue'] for r in group),
                  'v2_mean_recovery_actions_all20':statistics.mean(e['recovery']['action_steps'] for e in v2),
                  'v2_mean_added_tcp_path_m_all20':statistics.mean(r['v2_added_tcp_path_m'] for r in group),
                  'baseline_pre_intervention_peak_xy_displacement_m':describe(t['physical_diagnostics']['pre_intervention_peak_horizontal_displacement_m'] for t in baseline),
                  'baseline_pulse_y_displacement_m':describe(t['physical_diagnostics']['pulse_displacement_world_m'][1] for t in baseline),
                  'baseline_pulse_y_velocity_change_m_s':describe(t['physical_diagnostics']['pulse_delta_linear_velocity_world_m_s'][1] for t in baseline),
                  'baseline_pre_intervention_support_loss_count':sum(t['physical_diagnostics']['pre_intervention_support_loss'] for t in baseline)})
attempted = [t['result']['episode'] for t in trials if t['system']=='v2' and t['result']['episode']['recovery']['attempts']]
rescued = [e for e in attempted if e['task_success_at_end']]
failures = []
for trial in trials:
    episode = trial['result']['episode']
    if trial['system'] != 'v2' or episode['task_success_at_end']: continue
    native = study / trial['directory'] / trial['result']['run_relative']
    manifest = json.loads((native / 'manifest.json').read_text())
    records = [json.loads(line) for line in (native / 'events.jsonl').read_text().splitlines()]
    steps = [e for e in records if e['event']=='step']
    before = next(e for e in steps if e['step']==episode['recovery']['first_action_step']-1)
    retry = FixedPlacement(before['observation'],manifest['robot_base_pose'])
    abort = next(e for e in steps if e['recovery']['state']=='aborted')
    tcp = vector(abort['observation']['extra']['tcp_pose'],7,'tcp_pose')
    target = np.asarray(abort['controller_decision']['expected_tcp_position_world_m'])
    position_error = float(np.linalg.norm(tcp[:3]-target))
    rotation_error = float(rotation_angle(pose_rotation(tcp) @ retry.primitive.grasp_rotation.T))
    failures.append({'seed':trial['seed'],'point_id':trial['point_id'],'native_directory':trial['directory']+'/'+trial['result']['run_relative'],
                     'first_abort_action':abort['step'],'failed_phase':episode['recovery']['phase'],
                     'failure_detail':episode['recovery']['failure_detail'],'stage_actions_at_abort':episode['recovery']['phase_step'],
                     'recovery_actions':episode['recovery']['action_steps'],
                     'target_world_m':target.tolist(),'tcp_world_m_at_abort':tcp[:3].tolist(),
                     'tcp_target_error_m_at_abort':position_error,'arrival_tolerance_m':.02,
                     'rotation_error_rad_at_abort':rotation_error,'rotation_tolerance_rad':.15,
                     'position_gate_passed':position_error<=.02,'rotation_gate_passed':rotation_error<=.15,
                     'gripper_at_abort':abort['controller_decision']['gripper'],'is_grasped_at_abort':bool(abort['info']['is_grasped'][0]),
                     'lower_transition_step':episode['lower_transition_step'],'lower_timeout':episode['lower_phase_timeout'],
                     'recovery_release_executed':episode['recovery_release_executed'],'recovery_retraction_executed':episode['recovery_retraction_executed'],
                     'final_horizontal_error_m':episode['final_horizontal_error_m'],'final_reference':episode['final_reference'],
                     'physical_diagnostics':trial['physical_diagnostics'],
                     'interpretation':'Frozen phase deadline expires before target arrival; this does not independently prove kinematic unreachability or a unique controller/contact root cause.'})
detection = {}
for system in ('v1','v2'):
    episodes = [t['result']['episode'] for t in trials if t['system']==system]
    detected = [e for e in episodes if e['first_detected_failure']]
    references = [e for e in episodes if e['first_reference_failure']]
    detection[system] = {'reference_first_onsets':len(references),'detected_first_onsets':len(detected),
                         'diagnosis_matches_first_reference':sum(e['first_detected_failure']['failure']==e['first_reference_failure']['failure'] for e in detected if e['first_reference_failure']),
                         'detection_without_reference_or_before_reference':sum(not e['first_reference_failure'] or e['first_detected_failure']['step']<e['first_reference_failure']['step'] for e in detected),
                         'latency_steps':dict(Counter(e['first_failure_latency_steps'] for e in detected)),
                         'failure_labels':dict(Counter(e['first_reference_failure']['failure'] for e in references)),
                         'frame_counts':{k:sum(c['verification_counts'][k] for c in suite['summary']['cells'] if c['system']==system) for k in suite['summary']['cells'][1]['verification_counts']},
                         'frame_metric_interpretation':'V2 changes recovery phases and reference exposure; frame ratios are not independent sensor accuracy or directly comparable static-classifier performance.'}
transitions = []
points = [p['point_id'] for p in suite['protocol']['points']][2:]
for seed in suite['protocol']['seeds']:
    successes = [lookup[seed,p,'baseline']['result']['episode']['task_success_at_end'] for p in points]
    for left,right,a,b in zip(points,points[1:],successes,successes[1:]):
        if not a and b: transitions.append({'seed':seed,'lower_force_condition_failed':left,'higher_force_condition_succeeded':right})
report = {'schema_version':1,'measurement_commit':suite['identity']['software']['git_commit'],
          'analysis_unit':'20 common scenes reused across conditions; descriptive counts, no independent360-scene inference',
          'cells':cells,'distinct_scenes_with_at_least_one_rescue':len({r['seed'] for r in pairs if r['v2_rescue']}),
          'recovery':{'attempts':len(attempted),'successful_episodes':len(rescued),'failed_episodes':len(failures),
                      'success_fraction_of_attempts':len(rescued)/len(attempted),'all_attempt_action_cost':describe(e['recovery']['action_steps'] for e in attempted),
                      'successful_attempt_action_cost':describe(e['recovery']['action_steps'] for e in rescued),
                      'all120_mean_recovery_actions':statistics.mean(t['result']['episode']['recovery']['action_steps'] for t in trials if t['system']=='v2'),
                      'all120_mean_added_tcp_path_m':statistics.mean(r['v2_added_tcp_path_m'] for r in pairs),
                      'rescue_conditioned_added_tcp_path_m':describe(r['v2_added_tcp_path_m'] for r in pairs if r['v2_rescue']),
                      'successful_lower_release_retract_count':sum(e['lower_transition_step'] is not None and e['recovery_release_executed'] and e['recovery_retraction_executed'] for e in rescued),
                      'failed_phases':dict(Counter(f['failed_phase'] for f in failures)),
                      'all_attempts_total_budget_exhausted_count':sum(e['recovery']['failure_detail']=='remaining_action_budget_exhausted' for e in attempted)},
          'detection':detection,'failures':failures,'nonmonotonic_baseline_success_transitions':transitions,
          'limits':'All failures are retained. One bounded strategy with phase deadlines; privileged state and one cube/arm/task. No M8 retuning or second attempt.',
          'application_milestone':'M6R/M7 are accepted; completed independently audited M8 evidence returns to02 before acceptance or verifier work.'}
output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'cells':cells,'recovery':report['recovery'],'failure_gate_diagnostics':[{k:f[k] for k in ('seed','point_id','first_abort_action','tcp_target_error_m_at_abort','rotation_error_rad_at_abort')} for f in failures],
                  'nonmonotonic_transitions':transitions},indent=2))
