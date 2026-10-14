"""Frozen scheduling/checkpoint fixtures; no native force response is invented."""

from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from aether_cl import m8_frozen as frozen, m8_sweep as sweep
from aether_cl.m8_matched import LEGACY_SYSTEM, compare
from aether_cl.acceptance import load_trial
from aether_cl.runtime import json_value
from dataclasses import asdict
from test_m6 import SOFTWARE
from test_m8_matched import fixture_case, DisturbedFixture
from test_m6r import ContactConstrained


def fixture_result(item):
    failed = item['point_id'].startswith('force-probe')
    active = item['system']=='v2'
    excluded = item['seed']==179
    success = not failed or active
    episode={'excluded':excluded,'task_success_at_end':success and not excluded,'controller_complete':not excluded,
        'release_success_at_end':not excluded,'support_stability_success_at_end':not excluded,
        'retraction_success_at_end':not excluded,'first_failure_latency_steps':0 if failed else None,
        'final_horizontal_error_m':.005 if success else .08,'total_observed_tcp_path_m':1.2 if active else 1.,
        'first_detected_failure':{'step':342,'failure':'PLACEMENT_TARGET_NOT_REACHED'} if failed else None,
        'recovery':{'attempts':int(failed and active and not excluded),'action_steps':125 if failed and active and not excluded else 0},
        'recovery_task_success':failed and active and not excluded,'lower_transition_step':400 if active else None,
        'recovery_release_executed':failed and active,'recovery_retraction_executed':failed and active}
    return {'state':'finished_valid_frozen_evidence','episode':episode,'verification_metrics':None,
            'physical_force_applied':item['point_id']!='normal' and not excluded}


class Harness:
    def __init__(self,root):
        self.root=root;self.output=root/'study';self.final=root/'final.tar.gz';self.pilot=root/'pilot.tar.gz'
        self.commands=[];self.history_calls=[];self.failure=None
    def child(self,command,stream):
        self.commands.append(command)
        case=Path(command[command.index('--output')+1]);parent=Path(command[command.index('--suite')+1])
        report=json.loads(parent.read_text());item=report['trials'][-1]
        assert report['state']=='running' and item['result']['state']=='started_pending_child_result'
        assert item['output']==str(case) and report['runner_pid']==os.getpid()
        (case/'events.jsonl').write_text(json.dumps({'event':'reset','seed':item['seed']})+'\n')
        if self.failure:raise self.failure
        sweep.write_json(case/'m8_result.json',fixture_result(item))
        return 0
    def history(self,output,resume=False):
        self.history_calls.append(resume)
        return {'selected_seeds':list(frozen.SEEDS),'selected_overlap':[],'own_validated_study_excluded':resume}
    def comparisons(self,trials,output):
        locate={(t['seed'],t['point_id'],t['system']) for t in trials};rows=[]
        for seed in frozen.SEEDS:
            for p in frozen.POINT_IDS:
                for kind,a,b in (('passive','baseline','v1'),('recovery','v1','v2')):
                    if (seed,p,a) in locate and (seed,p,b) in locate:rows.append({'kind':kind,'passed':True})
                if p!='normal' and (seed,p,'baseline') in locate and (seed,'normal','baseline') in locate:
                    rows.append({'kind':'pre_force_control','passed':True})
        return rows
    def install(self,stack):
        settings=frozen.protocol();identity={'software':{},'startup_environment_sha256':frozen.environment_digest(frozen.environment())}
        stack.enter_context(patch.object(frozen,'preflight',return_value=(settings,identity)))
        stack.enter_context(patch.object(frozen,'validate_commission',return_value={'replayed_trials':36}))
        stack.enter_context(patch.object(frozen,'seed_history',side_effect=self.history))
        stack.enter_context(patch.object(sweep,'launch',side_effect=self.child))
        stack.enter_context(patch.object(frozen,'checked_trial',side_effect=lambda output,item,identity:json.loads((output/'m8_result.json').read_text())))
        stack.enter_context(patch.object(frozen,'comparisons',side_effect=self.comparisons))
        stack.enter_context(patch.object(sweep,'physical_diagnostics',return_value={'fixture_only':True}))
        stack.enter_context(redirect_stdout(io.StringIO()))
    def run(self,**kwargs):
        return sweep.run_suite(self.output,self.final,self.pilot,'fixture',self.root/'commission.json',self.root/'commission.tar.gz',**kwargs)


class FrozenTests(unittest.TestCase):
    def test_fixed360_pilot18_then342_no_replacements(self):
        rows=sweep.plan();self.assertEqual(len(rows),360)
        self.assertEqual(len({(r['seed'],r['point_id'],r['system']) for r in rows}),360)
        self.assertEqual({r['seed'] for r in rows},set(range(160,180)))
        self.assertEqual({r['seed'] for r in rows[:18]},{160,161})
        self.assertEqual({r['point_id'] for r in rows[:18]},set(frozen.PILOT_POINTS))
        self.assertEqual([r['slot'] for r in rows],list(range(360)))
        self.assertEqual(rows[18],{'slot':18,'point_id':'normal','seed':162,'system':'baseline'})
        for system in frozen.SYSTEMS:self.assertEqual(frozen.legacy_config(Path('case'),160,system).system,LEGACY_SYSTEM[system])

    def test_frozen_contract_receipt_and_source_identity(self):
        settings=frozen.protocol()
        self.assertEqual(json.loads(frozen.PROTOCOL_PATH.read_text()),settings)
        self.assertEqual(settings['requested_episodes'],360);self.assertFalse(settings['model_training'])
        self.assertEqual(settings['performance_gate'],'none_task_failures_retained')
        self.assertEqual(len(settings['sources_sha256']),15)
        self.assertEqual(settings['points'],frozen.candidate_points())
        self.assertEqual(settings['commissioning_review_sha256'],frozen.REVIEW_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'review.json';bad.write_text('{}')
            with patch.object(frozen,'REVIEW',bad),self.assertRaisesRegex(ValueError,'audited'):frozen.protocol()

    def test_direct_fresh_child_blocked_before_native_construction(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);settings=frozen.protocol();identity={}
            report={'state':'paused_first18','trials':[],'protocol':settings,'identity':identity,'runner_pid':os.getppid()}
            sweep.write_json(root/'suite.json',report)
            with patch.object(frozen,'preflight',return_value=(settings,identity)),patch.object(frozen,'build_env') as native:
                with self.assertRaisesRegex(ValueError,'live guarded'):frozen.run_fresh(root/'case','fixture',160,'v2','normal',root/'suite.json')
                native.assert_not_called();self.assertFalse((root/'case').exists())
            for seed in (True,100,159,180,2022):
                with self.assertRaises(ValueError):frozen.run_fresh(root/'case','fixture',seed,'v2','normal',root/'suite.json')

    def test_selected_seed_changes_only_physical_scope_predicate(self):
        old={'passed':False,'checks':{'one_known_reset':False,'fixed_window_and_precondition':True,'continuous_sample_state':False},
             'failed_checks':['one_known_reset','continuous_sample_state'],'force_calls':5,'effects':{'value':1}}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'physics.jsonl').write_text('{"event":"force_trace_started","seed":160}\n')
            with patch.object(frozen,'known_physics',return_value=copy.deepcopy(old)):
                checked=frozen.audit_physics(root,{'seed':160},{})
                self.assertEqual(checked['checks'],{'one_selected_fresh_reset':True,'fixed_window_and_precondition':True,'continuous_sample_state':False})
                self.assertFalse(checked['passed']);self.assertEqual(checked['effects'],old['effects'])
                self.assertEqual(checked['failed_checks'],['continuous_sample_state'])
                self.assertFalse(frozen.audit_physics(root,{'seed':100},{})['checks']['one_selected_fresh_reset'])

    def test_history_reuses_legacy_resolution_and_blocks_unknown_or_overlapping_resets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);case=root/'old';case.mkdir();file=case/'events.jsonl'
            file.write_text('{"event":"controller_reset","episode":0,"policy":{}}\n{"event":"reset","episode":0,"seed":100}\n')
            import importlib.util
            spec=importlib.util.spec_from_file_location('guard',frozen.HISTORY_SOURCE)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            history=module.inspect_history(frozen.HistoryView(root))
            self.assertEqual(history['reset_records'],2);self.assertEqual(history['recorded_reset_seeds'],[100])
            own=root/'study';own.mkdir();(own/'events.jsonl').write_text('{"event":"reset","seed":160}\n')
            self.assertIn(160,module.inspect_history(frozen.HistoryView(root))['recorded_reset_seeds'])
            self.assertNotIn(160,module.inspect_history(frozen.HistoryView(root,own))['recorded_reset_seeds'])
            file.write_text('{"event":"reset"}\n')
            with self.assertRaisesRegex(ValueError,'Missing/invalid'):module.inspect_history(frozen.HistoryView(root))
            runs=root/'runs';runs.mkdir();(runs/'events.jsonl').write_text('{"event":"reset","seed":100}\n{"event":"reset","seed":160}\n')
            with patch.object(frozen,'__file__',str(root/'aether_cl/m8_frozen.py')):
                with self.assertRaisesRegex(ValueError,'already reset'):frozen.seed_history(own)

    def test_native_identity_change_or_unfrozen_source_blocks_preflight(self):
        original=copy.deepcopy(frozen.reviewed_commission()['native_identity'])
        original['software']['git_commit']='fixture'
        with patch.object(frozen,'matched_preflight',return_value=original):
            settings,identity=frozen.preflight('fixture')
            self.assertEqual(identity['study_sources_sha256'],settings['sources_sha256'])
            original['software']['native_library_environment']['LD_PRELOAD']='different.so'
            with self.assertRaisesRegex(ValueError,'Native environment'):frozen.preflight('fixture')
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'protocol.json';bad.write_text('{}')
            with patch.object(frozen,'PROTOCOL_PATH',bad),patch.object(frozen,'matched_preflight') as native:
                with self.assertRaisesRegex(ValueError,'preregistration'):frozen.preflight('fixture')
                native.assert_not_called()

    def test_parent18_then342_immutable_pilot_full340_pairs_and_all_outcomes(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            h=Harness(Path(folder));h.install(stack)
            first=h.run();self.assertEqual(first['state'],'paused_first18');self.assertEqual(len(h.commands),18)
            self.assertEqual(len(first['pilot_gate']['comparisons']),16);self.assertFalse(first['pilot_gate']['performance_gate'])
            self.assertTrue(all(c['success_rate_requested'] is None for c in first['summary']['cells']))
            self.assertFalse(h.final.exists());pilot_hash=frozen.sha256(h.pilot)
            indexed=frozen.verify_index(h.output);self.assertEqual(len([p for p in indexed if p.startswith('sources/')]),21)
            pilot_trials=copy.deepcopy(first['trials'])
            final=h.run(resume=True,pilot_sha256=pilot_hash)
            self.assertEqual(final['state'],'valid_frozen_evidence');self.assertEqual(len(h.commands),360)
            self.assertEqual(len(final['final_gate']['comparisons']),340);self.assertEqual(final['trials'][:18],pilot_trials)
            self.assertEqual(frozen.sha256(h.pilot),pilot_hash);self.assertEqual(h.history_calls,[False,True])
            self.assertEqual(len({c[c.index('--output')+1] for c in h.commands}),360)
            self.assertEqual(final['summary']['totals']['v2_rescues'],76)
            self.assertEqual(final['summary']['totals']['v2_unnecessary_attempts'],0)
            self.assertEqual(final['summary']['totals']['v2_regressions'],0)
            self.assertTrue(all(c['completed']==20 and c['excluded']==1 and c['eligible']==19 for c in final['summary']['cells']))
            for cell in final['summary']['cells']:
                self.assertEqual(cell['success_rate_requested'],cell['task_successes']/20)
            with self.assertRaises(ValueError):h.run(resume=True,pilot_sha256=pilot_hash)
            with self.assertRaises(FileExistsError):h.run()

    def test_pilot_archive_environment_source_and_pending_slot_tamper_block_before_history(self):
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            h=Harness(Path(folder));h.install(stack);h.run();digest=frozen.sha256(h.pilot)
            original=(h.output/'suite.json').read_bytes();archive_bytes=h.pilot.read_bytes()
            def rejected():
                with self.assertRaises((ValueError,KeyError)):h.run(resume=True,pilot_sha256=digest)
                self.assertEqual(len(h.commands),18);self.assertEqual(h.history_calls,[False])
            h.pilot.write_bytes(archive_bytes+b'changed');rejected();h.pilot.write_bytes(archive_bytes)
            suite=json.loads(original);suite['trials'][-1]['result']['state']='started_pending_child_result'
            sweep.write_json(h.output/'suite.json',suite);rejected();(h.output/'suite.json').write_bytes(original)
            source=h.output/'sources/m8_frozen.py';source_bytes=source.read_bytes();source.write_bytes(b'changed');rejected();source.write_bytes(source_bytes)
            with patch.object(frozen,'environment',return_value={'changed':'native setting'}):rejected()
            self.assertFalse(h.final.exists());self.assertEqual((h.output/'suite.json').read_bytes(),original)

    def test_initial_preflight_failure_retains_empty_archive_without_fresh_reset(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(frozen,'preflight',side_effect=ValueError('bad source')), \
                patch.object(sweep,'launch') as child,redirect_stdout(io.StringIO()):
            h=Harness(Path(folder))
            with self.assertRaises(SystemExit):h.run()
            child.assert_not_called();self.assertEqual(json.loads((h.output/'suite.json').read_text())['trials'],[])
            self.assertTrue(h.pilot.exists());frozen.verify_index(h.output)

    def test_task_failure_and_healthy_case_regression_do_not_become_pilot_exclusions(self):
        original=fixture_result
        def outcomes(item):
            result=original(item)
            if item['system']=='v2':result['episode']['task_success_at_end']=False
            return result
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            h=Harness(Path(folder));h.install(stack)
            stack.enter_context(patch('test_m8_frozen.fixture_result',side_effect=outcomes))
            report=h.run()
            self.assertEqual(report['state'],'paused_first18');self.assertEqual(len(report['trials']),18)
            self.assertEqual(report['summary']['totals']['v2_regressions'],4)
            self.assertFalse(report['pilot_gate']['performance_gate'])

    def test_timeout_and_interrupt_retain_first_started_slot_no_resume_or_replacement(self):
        for failure in (subprocess.TimeoutExpired(['fixture'],600),KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__),tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
                h=Harness(Path(folder));h.install(stack);h.failure=failure
                with self.assertRaises(SystemExit):h.run()
                report=json.loads((h.output/'suite.json').read_text());self.assertEqual(report['state'],'error_retained')
                self.assertEqual(len(report['trials']),1);self.assertEqual(len(h.commands),1)
                self.assertIn(report['trials'][0]['directory']+'/events.jsonl',frozen.verify_index(h.output))
                with self.assertRaises(ValueError):h.run(resume=True,pilot_sha256=frozen.sha256(h.pilot))
                self.assertEqual(len(h.commands),1)

    def test_process_group_interrupt_waits_for_child_before_archive(self):
        from unittest.mock import MagicMock
        process=MagicMock();process.poll.return_value=None
        with patch.object(sweep.os,'killpg') as kill:
            sweep.stop_child(process)
            kill.assert_called_once_with(process.pid,sweep.signal.SIGINT);process.wait.assert_called_once_with(timeout=15)
        process.wait.side_effect=[subprocess.TimeoutExpired(['fixture'],15),0]
        with patch.object(sweep.os,'killpg') as kill:
            sweep.stop_child(process)
            self.assertEqual(kill.call_args_list[-1].args,(process.pid,sweep.signal.SIGKILL))

    def test_separate_physical_pulse_and_pre_intervention_cost_window(self):
        def state(y,v):return {'cube_pose_world':[[0,y,.02,1,0,0,0]],'cube_linear_velocity_m_s':[[0,v,0]],'cube_table_contact_force_world_n':[[0,0,.6]]}
        with tempfile.TemporaryDirectory() as folder:
            case=Path(folder);carrier={'episode':{'recovery':{'first_action_step':343}},
                'physical_effects':{'before_pulse':state(0,0),'after_pulse':state(.01,.2)}}
            rows=[{'event':'physics_action','step':step,'substeps':[{'after_physics':state(y,.2)}]} for step,y in ((296,.01),(342,.08),(343,.3),(800,.5))]
            (case/'physics.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            values=sweep.physical_diagnostics(case,carrier)
            self.assertEqual(values['pulse_displacement_world_m'],[0.,.01,0.])
            self.assertEqual(values['pre_intervention_peak_horizontal_displacement_m'],.08)
            self.assertEqual(values['window_end_action_before_first_recovery_or_episode_end'],342)

    def test_fresh_seed_full800_accepted_actions_and_active_gate_remain_identical(self):
        # Endpoint fixtures test mechanics/replay, not the physical efficacy claim.
        with tempfile.TemporaryDirectory() as folder:
            for system in frozen.SYSTEMS:
                case=Path(folder)/system;case.mkdir()
                carrier,gates,physics,checked=fixture_case(case,system,DisturbedFixture,seed=160)
                self.assertTrue(checked['passed'],checked['failed_checks']);self.assertEqual(checked['max_action_replay_error'],0.)
                self.assertEqual(len(gates),800);self.assertTrue(frozen.audit_gate(case,carrier)['passed'])
                self.assertEqual(carrier['episode']['task_success_at_end'],system=='v2')
            for kind,a,b in (('passive','baseline','v1'),('recovery','v1','v2')):
                self.assertTrue(compare(Path(folder)/a,Path(folder)/b,kind)['passed'])

    def test_fresh_child_parent_metadata_and_raw_action_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            case=Path(folder);item={'seed':160,'system':'v2','point_id':'normal'}
            carrier,gates,physics,checked=fixture_case(case,'v2',ContactConstrained,seed=160)
            config=frozen.legacy_config(case,160,'v2');physical={'passed':True,'effects':{},'force_calls':0}
            _,native_result,_=load_trial(case/carrier['run_relative'])
            carrier.update(scope=frozen.SCOPE,confirmatory=True,state='finished_valid_frozen_evidence',
                native_config=json_value(asdict(config)),verification_metrics=native_result['evaluation']['verification_metrics'],
                physical_effects={},physical_force_applied=False)
            manifest={**item,'scope':frozen.SCOPE,'confirmatory':True,'output':str(case.resolve()),
                'point':frozen.candidate_points()[0],'legacy_config':json_value(asdict(config)),
                'legacy_system_mapping':frozen.LEGACY_SYSTEM,'software':SOFTWARE,
                'preregistration':{'protocol_sha256':frozen.sha256(frozen.PROTOCOL_PATH),'authority_commit':frozen.AUTHORITY}}
            for name,value in (('m8_manifest.json',manifest),('m8_result.json',carrier),
                               ('accepted_runner_replay.json',checked),('physics_audit.json',physical),
                               ('controller_gate_audit.json',frozen.audit_gate(case,carrier))):sweep.write_json(case/name,value)
            with patch.object(frozen,'audit_physics',return_value=physical):
                self.assertEqual(frozen.checked_trial(case,item,{'software':SOFTWARE}),carrier)
                manifest['preregistration']['protocol_sha256']='poison';sweep.write_json(case/'m8_manifest.json',manifest)
                with self.assertRaisesRegex(ValueError,'scope/configuration'):frozen.checked_trial(case,item,{'software':SOFTWARE})
                manifest['preregistration']['protocol_sha256']=frozen.sha256(frozen.PROTOCOL_PATH);sweep.write_json(case/'m8_manifest.json',manifest)
                events=case/carrier['run_relative']/'events.jsonl';rows=[json.loads(l) for l in events.read_text().splitlines()]
                next(e for e in rows if e['event']=='step')['action'][0]+=.1
                events.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaisesRegex(ValueError,'replay'):frozen.checked_trial(case,item,{'software':SOFTWARE})


if __name__=='__main__':unittest.main()
