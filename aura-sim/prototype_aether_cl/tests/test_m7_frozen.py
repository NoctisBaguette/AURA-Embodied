"""Frozen-entry, pilot retention and resume counterexamples; no native simulator."""

import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aether_cl import m7_frozen as frozen, m7_sweep as sweep
from aether_cl.m7_runtime import run
from aether_cl.m7_audit import compare
from aether_cl.m7_summary import summarize
from test_m7 import KinematicFixture


class FrozenTests(unittest.TestCase):
    def test_complete_unique_plan_retains_first18_and_rejects_adaptive_seeds_or_magnitudes(self):
        selected=sweep.plan(Path('/fixed/output'))
        self.assertEqual(len(selected),360)
        self.assertEqual(len({(t['ratio'],t['seed'],t['system']) for t in selected}),360)
        self.assertEqual({t['ratio'] for t in selected[:18]},{0.,.5,2.})
        self.assertEqual({t['seed'] for t in selected[:18]},{140,141})
        for seed in range(140,160):frozen.M7FreshConfig(seed=seed).validate()
        for kwargs in ({'seed':139},{'seed':160},{'seed':True},{'offset_clearance_ratio':3.},
                       {'offset_clearance_ratio':float('nan')},{'system':'v2-old'}):
            with self.assertRaises(ValueError):frozen.M7FreshConfig(**kwargs).validate()

    def test_frozen_protocol_and_source_change_stop_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'protocol.json'
            value=frozen.protocol();path.write_text(json.dumps(value))
            with patch.object(frozen,'PROTOCOL_PATH',path):
                self.assertEqual(frozen.preflight(),value)
                bad=copy.deepcopy(value);bad['seeds'][0]=139;path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):frozen.preflight()
                path.write_text(json.dumps(value))
                original=frozen.sha256
                with patch.object(frozen,'sha256',side_effect=lambda p:'changed' if Path(p).name=='m7_policy.py' else original(p)):
                    with self.assertRaises(ValueError):frozen.preflight()

    def test_session_changes_do_not_change_child_environment_but_physical_settings_do(self):
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'1','LD_LIBRARY_PATH':'frozen','XDG_SESSION_ID':'876','SSH_CLIENT':'old'},clear=True):
            first=sweep.child_environment()
            os.environ['XDG_SESSION_ID']='879';os.environ['SSH_CLIENT']='new'
            self.assertEqual(first,sweep.child_environment())
            os.environ['CUDA_VISIBLE_DEVICES']='2'
            self.assertNotEqual(sweep.environment_digest(first),sweep.environment_digest(sweep.child_environment()))
            os.environ['CUDA_VISIBLE_DEVICES']='1';os.environ['LD_LIBRARY_PATH']='changed'
            self.assertNotEqual(sweep.environment_digest(first),sweep.environment_digest(sweep.child_environment()))

    def test_standalone_fresh_reset_requires_live_selected_parent(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=frozen.M7FreshConfig(output=Path(d)/'child')
            path=Path(d)/'suite.json';native={'software':{'git_commit':'fixture'}}
            report={'state':'running','runner_pid':os.getppid()+1000,'protocol':frozen.protocol(),'native':native,
                    'trials':[{'state':'running','seed':140,'system':'baseline','ratio':0.,'output':str(cfg.output.resolve())}]}
            path.write_text(json.dumps(report))
            with patch.object(frozen,'preflight'),patch.object(frozen,'preflight_native',return_value=native),patch.object(frozen,'run') as execute:
                with self.assertRaises(ValueError):frozen.run_fresh(cfg,path)
                execute.assert_not_called();self.assertFalse(cfg.output.exists())
                report['runner_pid']=os.getppid();report['trials'][0]['seed']=141;path.write_text(json.dumps(report))
                with self.assertRaises(ValueError):frozen.run_fresh(cfg,path)
                execute.assert_not_called()

    def test_native_history_rejects_external_resets_and_excludes_only_validated_own_study(self):
        with tempfile.TemporaryDirectory() as d:
            prototype=Path(d)/'prototype';own=prototype/'runs/study';own.mkdir(parents=True)
            prior=prototype/'runs/old';prior.mkdir();(prior/'events.jsonl').write_text('{"event":"reset","seed":139}\n')
            with patch.object(sweep,'__file__',str(prototype/'aether_cl/m7_sweep.py')):
                self.assertEqual(sweep.seed_history(own,False)['selected_overlap'],[])
                (own/'events.jsonl').write_text('{"event":"reset","seed":140}\n')
                with self.assertRaises(ValueError):sweep.seed_history(own,False)
                self.assertEqual(sweep.seed_history(own,True)['selected_overlap'],[])
                (prior/'events.jsonl').write_text('{"event":"reset","seed":141}\n')
                with self.assertRaises(ValueError):sweep.seed_history(own,True)

    def test_fresh_full_pipeline_metadata_independent_replay_and_matched_physics(self):
        with tempfile.TemporaryDirectory() as d:
            roots=[];native={'software':{'git_commit':'fixture','git_dirty':False},
                'installed_sources_sha256':{},'installed_assets_sha256':{},'startup_environment_sha256':'fixture'}
            for system in ('baseline','v1','v2'):
                cfg=frozen.M7FreshConfig(system=system,output=Path(d)/system)
                result=run(cfg,env_factory=KinematicFixture,observe_fn=lambda e,o,i:(o,i),
                    preflight_fn=lambda:native,development_only=False,task_contract_fn=frozen.frozen_contract,
                    preregistration=frozen.preregistration())
                root=Path(result['run_directory']);roots.append(root)
                item={'seed':140,'system':system,'ratio':0.,'output':str(cfg.output)}
                checked,audit=frozen.checked_trial(root,item,native)
                self.assertEqual(checked,result);self.assertEqual(audit['maximum_action_replay_error'],0.)
                self.assertTrue(result['fresh_native']);self.assertFalse(result['development_only'])
                if system=='v2':self.assertEqual(result['recovery']['attempts'],0)
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertEqual(manifest['task_contract']['status'],'frozen_before_fresh_native_M7')
            self.assertEqual(compare(roots[0],roots[1])['exact_steps'],1200)
            self.assertEqual(compare(roots[1],roots[2])['exact_steps'],1200)
            manifest=json.loads((roots[0]/'manifest.json').read_text());manifest['preregistration']['protocol_sha256']='tampered'
            (roots[0]/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):frozen.checked_trial(roots[0],{'seed':140,'system':'baseline','ratio':0.,'output':str(Path(d)/'baseline')},native)


def fixture_result(item,root):
    reference={'depth_m':.1,'orientation_error_rad':0.,'lateral_error_m':0.,'channel_margin_m':.003,
        'valid_acquisition':True,'legacy_velocity_task_success':False,'peg_head_position_hole_m':[0.,0.,0.],
        'object_target_relative_pose':{'position_m':[-.1,0.,0.],'rotation_matrix':[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]}}
    return {'state':'finished','steps':1200,'config':{'seed':item['seed'],'system':item['system'],
            'offset_clearance_ratio':item['ratio'],'output':item['output']},'run_directory':str(root),
        'task_success_at_end':True,'final_reference':reference,'controller_complete':True,
        'first_reference_failure':None,'first_detected_failure':None,'first_task_success_step':600,
        'injection':{'applied':item['ratio']!=0.,'precondition':True,'requested_magnitude_m':item['ratio']*.003},
        'pre_insert_state':{'reference':{**reference,'depth_m':-.06},'peg_box_contact_force_world_n':[0.,0.,0.]},
        'first_peg_box_contact_step':None,'first_positive_depth_step':530,'total_observed_tcp_path_m':1.,
        'recovery':{'attempts':0,'state':'nominal','completed_stages':[],'action_steps':0,'observed_tcp_path_m':0.}}


def fixture_launch(item,environment,suite):
    root=Path(item['output'])/'episode';root.mkdir(parents=True,exist_ok=False)
    (root/'result.json').write_text(json.dumps(fixture_result(item,root)))
    (root/'events.jsonl').write_text('fixture raw evidence\n')
    return root


def fixture_checked(root,item,native):
    return json.loads((root/'result.json').read_text()),{'passed':True,'steps':1200}


def fixture_pairs(trials,root,include_controls=False):
    lookup={(t['ratio'],t['seed'],t['system']):t for t in trials if t['state']=='passed'}
    pairs=[]
    for ratio,seed in sorted({(t['ratio'],t['seed']) for t in trials}):
        for a,b in (('baseline','v1'),('v1','v2')):
            if (ratio,seed,a) in lookup and (ratio,seed,b) in lookup:pairs.append({'ratio':ratio,'seed':seed,'systems':[a,b],'passed':True,'exact_steps':1200})
        if include_controls and ratio!=0. and (0.,seed,'baseline') in lookup and (ratio,seed,'baseline') in lookup:
            pairs.append({'ratio':ratio,'seed':seed,'systems':['normal_baseline','disturbed_baseline'],'passed':True,'exact_steps':430})
    return pairs


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.output=self.root/'study';self.archive=self.root/'study.tar.gz'
        self.environment={'CUDA_VISIBLE_DEVICES':'1','LD_LIBRARY_PATH':'frozen'}
        self.patches=[patch.object(sweep,'preflight_native',return_value={'software':{'git_commit':'fixture','git_dirty':False}}),
            patch.object(sweep,'child_environment',side_effect=lambda:self.environment.copy()),
            patch.object(sweep,'validate_commission',return_value={'reviewed':True}),
            patch.object(sweep,'seed_history',return_value={'selected_overlap':[]}),
            patch.object(sweep,'launch_child',side_effect=fixture_launch),
            patch.object(sweep,'checked_trial',side_effect=fixture_checked),
            patch.object(sweep,'suite_pairs',side_effect=fixture_pairs)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def start(self):
        return sweep.run_sweep(self.output,self.archive,'fixture-report','fixture-archive')
    def test_retained_pilot_pause_resume_only_unstarted_and_raw_or_environment_tampering_stops(self):
        first=self.start();self.assertEqual(first['state'],'paused');self.assertEqual(len(first['trials']),18)
        pilot=Path(first['saved_archive']);digest=frozen.sha256(pilot)
        second=sweep.run_sweep(self.output,self.archive,resume=True,stop_after=2)
        self.assertEqual(second['state'],'paused');self.assertEqual(len(second['trials']),20)
        self.assertEqual(frozen.sha256(pilot),digest)
        self.assertEqual(first['trials'],second['trials'][:18])
        self.environment['CUDA_VISIBLE_DEVICES']='2'
        with self.assertRaises(ValueError):sweep.run_sweep(self.output,self.archive,resume=True,stop_after=1)
        self.environment['CUDA_VISIBLE_DEVICES']='1'
        raw=self.output/first['trials'][0]['run_directory']/'events.jsonl';raw.write_text('changed raw evidence\n')
        with self.assertRaises(ValueError):sweep.run_sweep(self.output,self.archive,resume=True,stop_after=1)
        self.assertEqual(frozen.sha256(pilot),digest)
    def test_error_slot_is_archived_later_slots_not_launched_and_never_rerun(self):
        with patch.object(sweep,'launch_child',side_effect=RuntimeError('injected child failure')) as launch:
            result=self.start()
            self.assertEqual(result['state'],'error');self.assertEqual(len(result['trials']),1);self.assertEqual(launch.call_count,1)
        self.assertTrue(Path(result['saved_archive']).is_file())
        with self.assertRaises(ValueError):sweep.run_sweep(self.output,self.archive,resume=True)
        with self.assertRaises(ValueError):self.start()
    def test_immutable_pilot_archive_and_ownership_guard(self):
        first=self.start();pilot=Path(first['saved_archive']);pilot.write_bytes(pilot.read_bytes()+b'tampering')
        with self.assertRaises(ValueError):sweep.run_sweep(self.output,self.archive,resume=True)
        with (self.output/'runner.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(ValueError):sweep.run_sweep(self.output,self.archive,resume=True)
    def test_reporting_retains_failed_recovery_and_zero_attempt_costs(self):
        trials=[]
        for system in ('baseline','v1','v2'):
            item={'ratio':2.,'seed':140,'system':system,'output':'fixture'};r=fixture_result(item,Path('fixture'))
            r['task_success_at_end']=False;r['controller_complete']=False
            r['first_reference_failure']={'step':630,'failure':'DEPTH'}
            if system!='baseline':r['first_detected_failure']={'step':642,'failure':'DEPTH'}
            if system=='v2':r['recovery'].update(attempts=1,state='attempt_aborted',action_steps=140,failure_detail='reinsert_cap',completed_stages=['backout','realign'])
            trials.append({**item,'state':'passed','result':r})
        report=summarize(trials,(140,),(2.,));cell=next(c for c in report['cells'] if c['system']=='v2')
        self.assertEqual(cell['successful_recoveries'],0);self.assertEqual(cell['mean_retry_actions'],140)
        self.assertEqual(cell['stage_completions']['reinsert'],0);self.assertEqual(report['rescues'],0)
        self.assertEqual(report['paired_outcomes'][0]['extra_retry_actions_vs_v1'],140)
    def test_pilot_does_not_require_v2_success_or_drop_a_failed_outcome(self):
        trials=[]
        for item in sweep.plan(self.output)[:18]:
            r=fixture_result(item,Path(item['output']))
            if item['system']=='v2':
                r['task_success_at_end']=False;r['recovery'].update(attempts=1,state='attempt_aborted')
            trials.append({**item,'state':'passed','result':r})
        report={'trials':trials,'protocol':frozen.protocol(),'pairs':fixture_pairs(trials,self.output,True)}
        self.assertTrue(sweep.assess_pilot(report)['passed'])
        self.assertEqual(sum(not t['result']['task_success_at_end'] for t in trials),6)


if __name__=='__main__':unittest.main()
