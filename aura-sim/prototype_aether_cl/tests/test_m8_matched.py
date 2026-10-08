"""Matched controller/retention fixtures; native force response is separate."""

import ast
from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl import m8_matched as matched
from aether_cl.m6r_runtime import run
from aether_cl.m6r_audit import check_trial
from aether_cl.m6_policy import FixedPlacement
from aether_cl.m8_force import release_precondition
from aether_cl.runtime import fixed_action_for_space, json_value
from test_m6 import reset_fixture, observe_fixture, SOFTWARE, NATIVE_SOURCES, state
from test_m6r import ContactConstrained
from test_policy import BASE


class GateTrace:
    """Record controller instrumentation only, not simulated force proof."""
    def __init__(self, records):
        self.records = records

    def begin(self, step, observation, info, phase):
        self.intent = {"step": step, "nominal_phase": phase,
            "release_support_precondition": release_precondition(observation, info, phase) if step == 296 else False}

    def end(self):
        self.records.append({"event": "physics_action", "step": self.intent["step"],
                             "intent": copy.deepcopy(self.intent), "substeps": []})

    def close(self):
        pass


class DisturbedFixture(ContactConstrained):
    """Endpoint perturbation fixture only; production uses engine force."""
    def step(self, action):
        super().step(action)
        if self.step_number == 296:
            self.obs["extra"]["obj_pose"][0][1] += .08
        return copy.deepcopy(self.obs), [0.], [False], [self.step_number == 800], self.info()


class LateFailureFixture(ContactConstrained):
    def step(self, action):
        super().step(action)
        if self.step_number == 750:
            self.obs["extra"]["obj_pose"][0][1] += .08
        return copy.deepcopy(self.obs), [0.], [False], [self.step_number == 800], self.info()


def fixture_case(output, system, environment=ContactConstrained, seed=100):
    gates, physics = [], []
    config = matched.legacy_config(output, seed, system)
    def create(c):
        return matched.DecisionTraceEnvironment(environment())
    def reset(env, s):
        observation, info, support = reset_fixture(env, s)
        env.initialize(observation, info, BASE, system, gates.append)
        env.trace = GateTrace(physics)
        return observation, info, support
    def observe(env, observation, info):
        observation, info = observe_fixture(env, observation, info)
        env.accept_observation(observation, info)
        return observation, info
    with patch("aether_cl.m6r_runtime.software_manifest", return_value=SOFTWARE):
        result = run(config, env_factory=create, reset_fn=reset, observe_fn=observe,
                     native_sources_fn=lambda: NATIVE_SOURCES)
    native = Path(result["run_directory"])
    carrier = {"run_relative": str(native.relative_to(output)), "seed": seed, "system": system,
               "point_id": "normal", "episode": result["episodes"][0]}
    matched.write_json(output / "m8_result.json", carrier)
    matched.write_json(output / "m8_manifest.json", {"system": system, "point": {"point_id": "normal"}})
    (output / "controller_gate.jsonl").write_text(''.join(json.dumps(json_value(g))+'\n' for g in gates))
    (output / "physics.jsonl").write_text(''.join(json.dumps(json_value(p))+'\n' for p in physics))
    checked = check_trial(native, config, SOFTWARE)
    return carrier, gates, physics, checked


class MatchedTests(unittest.TestCase):
    def test36_slots_preserve_entire_geometric_grid_and_never_accept_fresh(self):
        plan = matched.plan()
        self.assertEqual(len(plan), 36)
        self.assertEqual(len({(p['seed'],p['point_id'],p['system']) for p in plan}),36)
        self.assertEqual({p['seed'] for p in plan},{100,101})
        self.assertEqual({p['system'] for p in plan},{'baseline','v1','v2'})
        self.assertEqual(tuple(p['point_id'] for p in matched.candidate_points()),matched.POINT_IDS)
        self.assertIn('force-probe-2',matched.POINT_IDS)
        self.assertNotIn('force-reference-v1-high',matched.POINT_IDS)
        for seed in (True,99,140,159,160,179,2022):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                matched.validate_child(seed,'v2','normal')
        for system in ('v2-old','v2r','v3'):
            with self.assertRaises(ValueError):matched.validate_child(100,system,'normal')
        config=matched.legacy_config(Path('fixture'),100,'v2')
        self.assertEqual(config.system,'v2r');self.assertEqual(config.disturbance,'none')
        self.assertEqual(config.max_steps,800);self.assertTrue(config.verification)

    def test_authoritative_action_is_forwarded_by_identity_and_mismatch_blocks_native(self):
        native=ContactConstrained();obs,info=native.reset(100)
        env=matched.DecisionTraceEnvironment(native);gates=[];physics=[]
        env.initialize(obs,info,BASE,'baseline',gates.append);env.trace=GateTrace(physics)
        action,_=FixedPlacement(obs,BASE).action(obs,0)
        action=fixed_action_for_space(action,native.action_space)
        with patch.object(native,'step',wraps=native.step) as stepped:
            env.step(action)
            self.assertIs(stepped.call_args.args[0],action)
        env.accept_observation(copy.deepcopy(native.obs),native.info())
        action,_=FixedPlacement(obs,BASE).action(native.obs,1)
        changed=fixed_action_for_space(action,native.action_space).copy();changed.flat[0]+=.01
        with patch.object(native,'step',wraps=native.step) as stepped:
            with self.assertRaisesRegex(ValueError,'authoritative action'):env.step(changed)
            stepped.assert_not_called()
        self.assertEqual(gates[-1]['event'],'controller_action_mismatch_before_native_step')

    def test_full_accepted_replays_passive_pairs_recovery_prefix_and_gate_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for scenario,environment in (('healthy',ContactConstrained),('failure',DisturbedFixture)):
                cases={}
                for system in matched.SYSTEMS:
                    case=root/scenario/system;case.mkdir(parents=True)
                    carrier,gates,physics,checked=fixture_case(case,system,environment)
                    self.assertTrue(checked['passed'],checked['failed_checks'])
                    self.assertEqual(checked['max_action_replay_error'],0.)
                    self.assertTrue(matched.audit_gate(case,carrier)['passed'])
                    self.assertEqual(carrier['episode']['task_success_at_end'],scenario=='healthy' or system=='v2')
                    self.assertEqual(carrier['episode']['recovery']['attempts'],int(scenario=='failure' and system=='v2'))
                    cases[system]=case
                for kind,left,right in (('passive','baseline','v1'),('recovery','v1','v2')):
                    checked=matched.compare(cases[left],cases[right],kind)
                    self.assertTrue(checked['passed'],checked)
                    if scenario=='healthy':self.assertEqual(checked['matched_steps'],800)
                    elif kind=='recovery':self.assertLess(checked['matched_steps'],800)
                path=cases['v2']/'controller_gate.jsonl'
                records=[json.loads(l) for l in path.read_text().splitlines()]
                records[99]['controller_decision']['phase']='poison'
                path.write_text(''.join(json.dumps(g)+'\n' for g in records))
                carrier=json.loads((cases['v2']/'m8_result.json').read_text())
                self.assertFalse(matched.audit_gate(cases['v2'],carrier)['passed'])
                path=cases['v1']/'physics.jsonl'
                records=[json.loads(l) for l in path.read_text().splitlines()]
                records[99]['intent']['nominal_phase']='poison'
                path.write_text(''.join(json.dumps(g)+'\n' for g in records))
                self.assertFalse(matched.compare(cases['baseline'],cases['v1'],'passive')['passed'])

    def test_early_recovery_uses_actual_phase_at296_not_nominal_retract(self):
        native=ContactConstrained();obs,info=native.reset(100)
        env=matched.DecisionTraceEnvironment(native);gates=[];physics=[]
        env.initialize(obs,info,BASE,'v2',gates.append);env.trace=GateTrace(physics)
        env.step_number=295
        env.verifier.last_step=295
        env.verdict={'status':'failed','failure':'PLACEMENT_TARGET_NOT_REACHED'}
        authoritative=matched.EffectAlignedRecovery(FixedPlacement(obs,BASE),BASE,800)
        action,decision=authoritative.action(obs,296,env.verdict)
        env.step(fixed_action_for_space(action,native.action_space))
        self.assertEqual(decision['phase'],'recovery_retry_retract')
        self.assertEqual(physics[0]['intent']['nominal_phase'],decision['phase'])
        self.assertFalse(physics[0]['intent']['release_support_precondition'])
        env.accept_observation(copy.deepcopy(native.obs),native.info())
        self.assertEqual(gates[0]['recovery']['attempts'],1)

    def test_initial_goal_exclusion_has_zero_actions_gates_and_no_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            case=Path(directory)
            carrier,gates,physics,checked=fixture_case(case,'v2',seed=111)
            self.assertTrue(checked['passed']);self.assertTrue(carrier['episode']['excluded'])
            self.assertEqual(gates,[]);self.assertEqual(physics,[])
            self.assertTrue(matched.audit_gate(case,carrier)['passed'])

    def test_budget_rejected_invocation_retains_exact_trigger_prefix_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            cases={}
            for system in ('v1','v2'):
                case=Path(directory)/system;case.mkdir()
                carrier,gates,physics,checked=fixture_case(case,system,LateFailureFixture)
                self.assertTrue(checked['passed'],checked['failed_checks'])
                self.assertTrue(matched.audit_gate(case,carrier)['passed'])
                self.assertFalse(carrier['episode']['task_success_at_end'])
                if system=='v2':
                    recovery=carrier['episode']['recovery']
                    self.assertEqual(recovery['attempts'],0)
                    self.assertEqual(recovery['failure_detail'],'insufficient_remaining_budget')
                    self.assertIsNone(recovery['first_action_step'])
                cases[system]=case
            paired=matched.compare(cases['v1'],cases['v2'],'recovery')
            self.assertTrue(paired['passed'],paired)
            self.assertIsNone(paired['first_recovery_action_step'])
            self.assertEqual(paired['prefix_through_step'],recovery['trigger_step'])
            self.assertLess(paired['matched_steps'],800)

    def test_receipt_guard_retains_error_archive_before_native_or_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bad=root/'bad.json';bad.write_text('{}')
            with patch.object(matched,'DOSE_REVIEW',bad),patch.object(matched,'dose_preflight') as native, \
                    patch.object(matched.subprocess,'run') as child,redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):matched.run_suite(root/'study',root/'error.tar.gz','fixture')
                native.assert_not_called();child.assert_not_called()
                report=json.loads((root/'study/suite.json').read_text())
                self.assertEqual(report['state'],'error_retained');self.assertEqual(report['trials'],[])
                self.assertTrue((root/'error.tar.gz').exists())

    def test_parent_runs_fixed36_compares34_and_indexes_all15_snapshots(self):
        commands=[]
        def child(command,**kwargs):
            commands.append(command);case=Path(command[command.index('--output')+1])
            matched.write_json(case/'m8_result.json',{'state':'finished_valid_development_evidence'})
            return subprocess.CompletedProcess(command,0)
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            stack.enter_context(patch.object(matched,'preflight',return_value={'software':{}}))
            stack.enter_context(patch.object(matched.subprocess,'run',side_effect=child))
            stack.enter_context(patch.object(matched,'compare',return_value={'passed':True}))
            stack.enter_context(patch.object(matched,'paired_outcomes',return_value=[]))
            stack.enter_context(redirect_stdout(io.StringIO()))
            report=matched.run_suite(root/'study',root/'archive.tar.gz','fixture')
            self.assertEqual(len(commands),36);self.assertEqual(len(report['comparisons']),34)
            self.assertFalse(report['fresh_study_started']);self.assertFalse(report['force_family_frozen_for_fresh_study'])
            self.assertEqual(report['state'],'valid_development_evidence')
            with tarfile.open(root/'archive.tar.gz') as bundle:
                index=json.load(bundle.extractfile('m8-force-commission/file_index.json'))
                snapshots=[n for n in index if n.startswith('sources/')]
                self.assertEqual(len(snapshots),15)
                self.assertIn('sources/'+matched.DOSE_REVIEW.name,snapshots)
            with self.assertRaises(FileExistsError):matched.run_suite(root/'study',root/'archive.tar.gz','fixture')

    def test_timeout_retains_first_started_slot_partial_evidence_without_resume(self):
        calls=[]
        def timeout(command,**kwargs):
            calls.append(command);case=Path(command[command.index('--output')+1])
            (case/'partial.jsonl').write_text('{"event":"reset","seed":100}\n')
            raise subprocess.TimeoutExpired(command,600)
        with tempfile.TemporaryDirectory() as directory,patch.object(matched,'preflight',return_value={}), \
                patch.object(matched.subprocess,'run',side_effect=timeout),redirect_stdout(io.StringIO()):
            root=Path(directory)
            with self.assertRaises(SystemExit):matched.run_suite(root/'study',root/'archive.tar.gz','fixture')
            self.assertEqual(len(calls),1)
            report=json.loads((root/'study/suite.json').read_text())
            self.assertEqual(len(report['trials']),1)
            self.assertEqual(report['trials'][0]['result']['state'],'child_timeout_retained')
            with tarfile.open(root/'archive.tar.gz') as bundle:
                index=json.load(bundle.extractfile('m8-force-commission/file_index.json'))
                self.assertIn(report['trials'][0]['directory']+'/partial.jsonl',index)

    def test_paired_outcomes_distinguish_rescue_unnecessary_retry_and_regression(self):
        trials=[]
        for item in matched.plan():
            is_v2=item['system']=='v2';is_baseline_healthy=item['point_id'] in ('normal','force-easy-v1')
            episode={'task_success_at_end':is_baseline_healthy or is_v2,'excluded':False,
                'recovery':{'attempts':int(is_v2),'action_steps':10 if is_v2 else 0},
                'recovery_task_success':is_v2,'total_observed_tcp_path_m':1.2 if is_v2 else 1.,
                'first_detected_failure':None,'lower_transition_step':450 if is_v2 else None,
                'recovery_release_executed':is_v2,'recovery_retraction_executed':is_v2}
            trials.append({**item,'result':{'episode':episode,'physical_effects':{'force_calls':0}}})
        rows=matched.paired_outcomes(trials)
        self.assertEqual(sum(r['v2_rescue'] for r in rows),8)
        self.assertEqual(sum(r['v2_unnecessary_attempt'] for r in rows),4)
        self.assertEqual(sum(r['v2_final_regression'] for r in rows),0)
        self.assertEqual(sum(r['v2_successful_recovery_episode'] for r in rows),12)

    def test_new_module_has_no_new_force_api_or_actor_state_mutator(self):
        tree=ast.parse(Path(matched.__file__).read_text())
        forbidden={'set_pose','set_linear_velocity','set_angular_velocity','add_force_torque','apply_impulse','shift_native'}
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in forbidden for n in calls))
        self.assertFalse(any(isinstance(n.func,ast.Name) and n.func.id=='shift_native' for n in calls))


if __name__=='__main__':
    unittest.main()
