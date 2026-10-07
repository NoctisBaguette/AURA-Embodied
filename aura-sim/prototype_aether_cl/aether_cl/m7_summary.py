"""M7 retained outcome, detection, recovery-stage and paired-cost reporting."""

from collections import Counter
import csv
import statistics

from .m7_runtime import SYSTEMS


def outcome(trial):
    r = trial['result']; f = r['final_reference']; recovery = r['recovery']
    onset, detection = r['first_reference_failure'], r['first_detected_failure']
    return {'ratio':trial['ratio'],'seed':trial['seed'],'system':trial['system'],
        'task_success':r['task_success_at_end'],'legacy_velocity_success':f['legacy_velocity_task_success'],
        'controller_complete':r['controller_complete'],'valid_acquisition':f['valid_acquisition'],
        'depth_m':f['depth_m'],'orientation_error_rad':f['orientation_error_rad'],'lateral_error_m':f['lateral_error_m'],
        'channel_margin_m':f['channel_margin_m'],'object_target_relative_pose':f['object_target_relative_pose'],
        'depth_error_from_nominal_m':abs(f['peg_head_position_hole_m'][0]),
        'object_target_goal_position_error_m':sum(v*v for v in f['peg_head_position_hole_m'])**.5,
        'injection_applied':r['injection']['applied'],'injection_precondition':r['injection']['precondition'],
        'requested_magnitude_m':r['injection']['requested_magnitude_m'],
        'preinsert_relative_pose':r['pre_insert_state']['reference']['object_target_relative_pose'],
        'preinsert_head_hole_m':r['pre_insert_state']['reference']['peg_head_position_hole_m'],
        'first_box_contact_step':r['first_peg_box_contact_step'],'first_positive_depth_step':r['first_positive_depth_step'],
        'reference_failure':onset,'detected_failure':detection,
        'detection_latency_steps':detection['step']-onset['step'] if onset and detection else None,
        'diagnosis_matches':onset['failure']==detection['failure'] if onset and detection else None,
        'recovery_attempts':recovery['attempts'],'recovery_success':bool(recovery['attempts'] and r['task_success_at_end']),
        'recovery_state':recovery['state'],'recovery_abort_reason':recovery.get('failure_detail'),
        'recovery_reason':recovery.get('reason'),
        'completed_stages':recovery['completed_stages'],'retry_actions':recovery['action_steps'],
        'retry_tcp_path_m':recovery['observed_tcp_path_m'],'total_tcp_path_m':r['total_observed_tcp_path_m'],
        'first_task_success_step':r['first_task_success_step']}


def summarize(trials, seeds, ratios):
    rows = [outcome(t) for t in trials if t.get('state') == 'passed']
    lookup = {(r['ratio'],r['seed'],r['system']):r for r in rows}
    cells, paired = [], []
    for ratio in ratios:
        for system in SYSTEMS:
            selected = [r for r in rows if r['ratio']==ratio and r['system']==system]
            attempted = [r for r in selected if r['recovery_attempts']]
            def mean(key):
                return statistics.mean(r[key] for r in selected) if selected else None
            cells.append({'ratio':ratio,'nominal_magnitude_m':ratio*.003,'system':system,
                'complete':len(selected)==len(seeds),'observed_episodes':len(selected),'expected_episodes':len(seeds),
                'task_successes':sum(r['task_success'] for r in selected),
                'observed_success_rate':sum(r['task_success'] for r in selected)/len(selected) if selected else None,
                'legacy_velocity_successes':sum(r['legacy_velocity_success'] for r in selected),
                'controller_completions':sum(r['controller_complete'] for r in selected),
                'valid_acquisitions':sum(r['valid_acquisition'] for r in selected),
                'injections_applied':sum(r['injection_applied'] for r in selected),
                'missed_injection_preconditions':sum(not r['injection_precondition'] for r in selected),
                'recovery_attempts':sum(r['recovery_attempts'] for r in selected),
                'successful_recoveries':sum(r['recovery_success'] for r in selected),
                'failure_detections':sum(bool(r['detected_failure']) for r in selected),
                'reference_failures_detected':sum(bool(r['reference_failure'] and r['detected_failure']) for r in selected),
                'reference_failures_missed':sum(bool(r['reference_failure'] and not r['detected_failure']) for r in selected),
                'false_detections':sum(bool(r['detected_failure'] and not r['reference_failure']) for r in selected),
                'premature_detections':sum(r['detection_latency_steps'] is not None and r['detection_latency_steps']<0 for r in selected),
                'matching_diagnoses':sum(r['diagnosis_matches'] is True for r in selected),
                'failure_counts':dict(Counter(r['detected_failure']['failure'] for r in selected if r['detected_failure'])),
                'abort_counts':dict(Counter(r['recovery_abort_reason'] for r in attempted if r['recovery_abort_reason'])),
                'stage_completions':{stage:sum(stage in r['completed_stages'] for r in attempted)
                                     for stage in ('backout','realign','reinsert','verify')},
                'detection_latencies_steps':[r['detection_latency_steps'] for r in selected if r['detection_latency_steps'] is not None],
                'mean_depth_m':mean('depth_m'),'mean_orientation_error_rad':mean('orientation_error_rad'),
                'mean_lateral_error_m':mean('lateral_error_m'),'mean_retry_actions':mean('retry_actions'),
                'mean_retry_tcp_path_m':mean('retry_tcp_path_m'),'mean_total_tcp_path_m':mean('total_tcp_path_m')})
        for seed in seeds:
            base, v1, v2 = (lookup.get((ratio,seed,system)) for system in SYSTEMS)
            if not base or not v1 or not v2:
                continue
            normal = lookup.get((0.,seed,'baseline'))
            delta = ([a-b for a,b in zip(base['preinsert_relative_pose']['position_m'], normal['preinsert_relative_pose']['position_m'])]
                     if normal else None)
            paired.append({'ratio':ratio,'seed':seed,'baseline_success':base['task_success'],'v1_success':v1['task_success'],
                'v2_success':v2['task_success'],'rescued':not base['task_success'] and v2['task_success'],
                'unnecessary_recovery':base['task_success'] and bool(v2['recovery_attempts']),
                'regression':base['task_success'] and not v2['task_success'],
                'extra_retry_actions_vs_v1':v2['retry_actions']-v1['retry_actions'],
                'extra_total_path_m_vs_v1':v2['total_tcp_path_m']-v1['total_tcp_path_m'],
                'baseline_achieved_preinsert_delta_hole_m':delta})
    return {'episodes':rows,'cells':cells,'paired_outcomes':paired,
            'total_actions':sum(t['result']['steps'] for t in trials if t.get('state')=='passed'),
            'unnecessary_recoveries':sum(p['unnecessary_recovery'] for p in paired),
            'regressions':sum(p['regression'] for p in paired),'rescues':sum(p['rescued'] for p in paired)}


def write_csvs(root, summary):
    for filename, key in (('episodes.csv','episodes'),('curve.csv','cells'),('paired.csv','paired_outcomes')):
        rows = summary[key]
        with (root/filename).open('w',newline='') as stream:
            if rows:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
                writer.writeheader();writer.writerows(rows)
