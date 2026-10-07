"""Insertion contract counterexamples, physical phase gates and isolated log replay."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from scipy.spatial.transform import Rotation

from aether_cl.runtime import json_value
from aether_cl.m7_task import geometry, InsertionReference, InsertionVerifier
from aether_cl.m7_policy import FixedInsertion, InsertionRecovery, INJECTION_STEP, command
from aether_cl.m7_runtime import M7DevelopmentConfig, run, perturb_waypoints
from aether_cl.m7_audit import independent_endpoint, replay, compare
from aether_cl import m7_runtime


def pose(p, rotation=None):
    r = np.eye(3) if rotation is None else rotation
    q = Rotation.from_matrix(r).as_quat()
    return np.r_[p, q[3], q[:3]].tolist()


def observation(p=(-.1, 0, .1), rotation=None, aperture=.04):
    r = np.eye(3) if rotation is None else rotation
    return {"extra": {"peg_pose": pose(p, r), "tcp_pose": pose(np.asarray(p) + r @ [-.06, 0, 0], r @ np.diag([1., -1., -1.])),
        "peg_half_size": [[.1, .02, .02]], "box_hole_pose": pose([0, 0, .1]), "box_hole_radius": [.023],
        "peg_linear_velocity": [0., 0., 0.], "peg_angular_velocity": [0., 0., 0.], "box_pose": pose([0, 0, .1])},
        "agent": {"qpos": [0.] * 7 + [aperture / 2, aperture / 2]}}


def info(held=True):
    return {"contact_grasped": held, "success": True,
        "left_finger_peg_force_world_n": [0., 1. if held else 0., 0.],
        "right_finger_peg_force_world_n": [0., -1. if held else 0., 0.],
        "left_finger_open_direction_world": [0., 1., 0.], "right_finger_open_direction_world": [0., -1., 0.],
        "peg_box_contact_force_world_n": [0., 0., 0.], "peg_table_contact_force_world_n": [0., 0., 0.]}


BASE = pose([-.615, 0, 0])


class ContractTests(unittest.TestCase):
    def test_fixed_target_accepts_equivalent_quaternion_and_bounded_roundoff(self):
        initial = observation()
        for translation, quaternion in ((0., [-1., 0., 0., 0.]),
                                        (2e-8, [1.0000001, 0., 0., 0.])):
            o = copy.deepcopy(initial)
            o['extra']['box_hole_pose'][0] += translation
            o['extra']['box_hole_pose'][3:] = quaternion
            state = InsertionReference(initial).observe(o, info(), 1, {'phase':'approach','phase_step':1})
            self.assertTrue(state['fixed_target_check']['passed'])
            self.assertFalse(state['fixed_target_check']['raw_pose_equal'])
            self.assertAlmostEqual(state['fixed_target_check']['translation_delta_m'], translation)

    def test_fixed_target_rejects_motion_and_exact_dimension_changes(self):
        initial = observation()
        for kind in ('translation', 'rotation', 'half', 'radius'):
            o = copy.deepcopy(initial)
            if kind == 'translation':
                o['extra']['box_hole_pose'][0] += 2e-6
            elif kind == 'rotation':
                o['extra']['box_hole_pose'] = pose([0, 0, .1], Rotation.from_euler('z', 2e-6).as_matrix())
            elif kind == 'half':
                o['extra']['peg_half_size'][0][0] += 1e-9
            else:
                o['extra']['box_hole_radius'][0] += 1e-9
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'Insertion target/geometry changed:'):
                InsertionReference(initial).observe(o, info(), 1, {'phase':'approach','phase_step':1})

    def test_target_roundoff_is_anchored_to_reset(self):
        initial = observation(); ref = InsertionReference(initial)
        for step in range(1, 6):
            o = copy.deepcopy(initial); o['extra']['box_hole_pose'][0] = step * 2e-7
            ref.observe(o, info(), step, {'phase':'approach','phase_step':step})
        o['extra']['box_hole_pose'][0] = 1.2e-6
        with self.assertRaises(ValueError):
            ref.observe(o, info(), 6, {'phase':'approach','phase_step':6})

    def test_healthy_volume_and_quarter_turn(self):
        for r in (np.eye(3), Rotation.from_euler('x', np.pi / 2).as_matrix()):
            self.assertTrue(geometry(observation(rotation=r))["relation_ready"])

    def test_head_only_false_positive_rejected(self):
        r = Rotation.from_euler('z', .04).as_matrix()
        o = observation(np.array([0., 0., .1]) - r[:, 0] * .1, r)
        g = geometry(o)
        self.assertLess(np.linalg.norm(g["head_position_hole_m"][1:]), 1e-12)
        self.assertLess(g["orientation_error_rad"], .05)
        self.assertFalse(g["relation_ready"])
        self.assertLess(g["channel_margin_m"], -.0002)

    def test_depth_bounds_and_reversed_axis(self):
        for o in (observation((-.25, 0, .1)), observation((2., 0, .1)),
                  observation((.1, 0, .1), Rotation.from_euler('z', np.pi).as_matrix())):
            self.assertFalse(geometry(o)["relation_ready"])

    def test_clearance_not_center_inside_hole(self):
        self.assertTrue(geometry(observation((-.1, .0025, .1)))["relation_ready"])
        self.assertFalse(geometry(observation((-.1, .005, .1)))["relation_ready"])

    def test_reference_requires_contact_acquisition_lift_and_ten_fresh_frames(self):
        initial = observation((-.3, 0, .02)); ref = InsertionReference(initial)
        d = {"phase": "settle", "phase_step": 20}
        o = observation()
        for step in range(1, 11):
            state = ref.observe(o, info(), step, d)
            self.assertFalse(state["task_success"])
        self.assertTrue(ref.observe(o, info(), 11, d)["task_success"])
        o["extra"]["peg_linear_velocity"][0] = .02
        self.assertFalse(ref.observe(o, info(), 12, d)["task_success"])
        with self.assertRaises(ValueError):ref.observe(o, info(), 12, d)

    def test_builtin_true_without_acquisition_or_lift_never_scores(self):
        for reset, held in ((observation((-.3, 0, .02)), False), (observation(), True)):
            ref = InsertionReference(reset)
            for step in range(1, 15):
                state = ref.observe(observation(), info(held), step, {"phase": "settle", "phase_step": step})
            self.assertFalse(state["task_success"])

    def test_raw_force_endpoint_detects_forged_acquisition(self):
        o = observation(); i = info(False); i["contact_grasped"] = True
        with self.assertRaises(ValueError):independent_endpoint(o, i, np.array(o["extra"]["peg_pose"]), True, .08)

    def test_contact_before_ungrasped_flight_is_not_valid_acquisition(self):
        reset=observation((-.3,0,.02));ref=InsertionReference(reset)
        ref.observe(reset,info(True),1,{"phase":"close","phase_step":30})
        for step in range(2,16):
            state=ref.observe(observation(),info(False),step,{"phase":"settle","phase_step":20})
        self.assertFalse(state['valid_acquisition']);self.assertFalse(state['task_success'])

    def test_independent_geometry_agrees_on_clipped_rotated_counterexamples(self):
        for angle in (0., .01, .04, .1):
            r = Rotation.from_euler('z', angle).as_matrix()
            o = observation(np.array([0., 0., .1]) - r[:, 0] * .1, r)
            raw = independent_endpoint(o, info(), np.array(o["extra"]["peg_pose"]), True, .08)
            g = geometry(o)
            self.assertEqual(raw["relation_ready"], g["relation_ready"])
            self.assertAlmostEqual(raw["channel_margin_m"], g["channel_margin_m"])

    def test_invalid_geometry_rejected(self):
        o = observation(); o["extra"]["box_hole_radius"] = [.024]
        with self.assertRaises(ValueError):geometry(o)


class PreflightTests(unittest.TestCase):
    def test_inspected_versions_sources_assets_and_clean_checkout_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pkg=root/'mani_skill';pkg.mkdir()
            (pkg/'task.py').write_bytes(b'task fixture\n')
            (pkg/'assets').mkdir();(pkg/'assets'/'robot.urdf').write_bytes(b'robot fixture\n')
            receipt={'packages':{'mani_skill':'3.0.1'},'source_sha256':{'task.py':hashlib.sha256((pkg/'task.py').read_bytes()).hexdigest()},
                     'asset_sha256':{'robot.urdf':hashlib.sha256((pkg/'assets'/'robot.urdf').read_bytes()).hexdigest()}}
            p=root/'receipt.json';p.write_text(json.dumps(receipt))
            with patch.object(m7_runtime,'RECEIPT_PATH',p),patch.object(m7_runtime.sys,'version_info',(3,10,22)),patch.object(m7_runtime,'version',return_value='3.0.1'),patch.object(m7_runtime,'distribution',return_value=SimpleNamespace(locate_file=lambda name:pkg)),patch.object(m7_runtime,'software_manifest',return_value={'git_commit':'fixture','git_dirty':False}):
                self.assertEqual(m7_runtime.preflight_native()['installed_sources_sha256'],receipt['source_sha256'])
                (pkg/'task.py').write_bytes(b'changed task\n')
                with self.assertRaises(ValueError):m7_runtime.preflight_native()
                (pkg/'task.py').write_bytes(b'task fixture\n')
                with patch.object(m7_runtime,'version',return_value='3.0.2'):
                    with self.assertRaises(ValueError):m7_runtime.preflight_native()
                with patch.object(m7_runtime,'software_manifest',return_value={'git_commit':'fixture','git_dirty':True}):
                    with self.assertRaises(ValueError):m7_runtime.preflight_native()

    def test_parent_archives_failed_slot_and_never_reuses_output(self):
        from aether_cl import m7_development
        receipt=json.loads(m7_runtime.RECEIPT_PATH.read_text())
        # No native report/simulator is needed to exercise failure retention.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report_path=root/'inspection.json';report_path.write_bytes(b'fixture inspection')
            receipt['inspection_report_sha256']=hashlib.sha256(report_path.read_bytes()).hexdigest()
            receipt_path=root/'receipt.json';receipt_path.write_text(json.dumps(receipt))
            output=root/'partial';archive=root/'partial.tar.gz'
            with patch.object(m7_development,'preflight_native',return_value={'software':{'git_commit':'fixture','git_dirty':False}}),patch.object(m7_development,'RECEIPT_PATH',receipt_path),patch.object(m7_development,'INSPECTION_REPORT_PATH',report_path),patch.object(m7_development,'history_guard',return_value={'preferred_overlap':[]}),patch.object(m7_development,'launch_child',side_effect=RuntimeError('injected child failure')):
                with self.assertRaises(RuntimeError):m7_development.run_suite(output,archive)
            report=json.loads((output/'suite.json').read_text())
            self.assertEqual(report['state'],'error');self.assertEqual(len(report['trials']),1)
            self.assertFalse(report['fresh_native']);self.assertTrue(archive.is_file())
            index=json.loads((output/'archive_index.json').read_text())['files']
            for entry in index:
                raw=(output/entry['path']).read_bytes()
                self.assertEqual(len(raw),entry['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256'])
            import tarfile
            with tarfile.open(archive) as tar:
                self.assertEqual({e.name for e in tar.getmembers() if e.isfile()},
                                 {str(Path(output.name)/e['path']) for e in index}|{str(Path(output.name)/'archive_index.json')})
            with self.assertRaises(ValueError):m7_development.run_suite(output,root/'second.tar.gz')


class PolicyTests(unittest.TestCase):
    def test_slow_insertion_preserves_transverse_correction_under_long_travel(self):
        rotation = Rotation.from_euler('z', .7).as_matrix()
        axis = rotation[:, 0]
        o = observation()
        current = np.asarray(o['extra']['tcp_pose'][:3])
        for travel in (.06, .2):
            target = current + travel * axis + .002 * rotation[:, 1] + .002 * rotation[:, 2]
            _, detail = command(o, BASE, target, np.eye(3), slow=True, axis_world=axis)
            delta = np.asarray(detail['commanded_tcp_position_world_m']) - current
            self.assertAlmostEqual(delta @ axis, .004)
            np.testing.assert_allclose(delta @ rotation[:, 1:], [.002, .002], atol=1e-14)
            self.assertLessEqual(np.linalg.norm(delta), np.sqrt(2) * .004)

    def test_insertion_under_loaded_tracking_fixture_holds_channel_alignment(self):
        # Finite tracking gain + downward load; isolates far-distance error scaling.
        # This is a controller counterexample, not native-physics commissioning.
        from aether_cl.policies import bounded
        start = np.array([-.32, 0., .1]); target = np.array([-.16, 0., .1])
        results = []
        for repaired in (False, True):
            tcp = start.copy(); worst_entry_error = 0.
            for _ in range(160):
                if repaired:
                    o = observation(tcp + [.06, 0, 0])
                    _, detail = command(o, BASE, target, np.diag([1.,-1.,-1.]),
                                        slow=True, axis_world=np.array([1.,0.,0.]))
                    commanded = np.asarray(detail['commanded_tcp_position_world_m'])
                else:
                    commanded = tcp + bounded(target - tcp, .004)
                tcp += .4 * (commanded - tcp) - [0., 0., .0006]
                if tcp[0] + .166 >= -.1:
                    worst_entry_error = max(worst_entry_error, abs(tcp[2] - .1))
            results.append(worst_entry_error)
        self.assertGreater(results[0], .01)
        self.assertLess(results[1], .003)

    def test_recovery_target_guard_uses_physical_pose_and_rejects_motion(self):
        initial = observation()
        for delta in (2e-8, 2e-6):
            recovery = InsertionRecovery(FixedInsertion(initial, BASE))
            recovery.action(initial, 635, {'status':'failed','failure':'INSERTION_DEPTH_NOT_ACHIEVED'})
            o = copy.deepcopy(initial)
            o['extra']['box_hole_pose'][0] += delta
            o['extra']['box_hole_pose'][3] = -1.
            recovery.observe(o)
            self.assertEqual(recovery.state, 'attempting' if delta < 1e-6 else 'aborted')
            self.assertEqual(recovery.snapshot()['fixed_target_check']['passed'], delta < 1e-6)

    def test_fresh_seeds_and_unfrozen_magnitudes_blocked(self):
        for config in (M7DevelopmentConfig(seed=140), M7DevelopmentConfig(offset_clearance_ratio=3.), M7DevelopmentConfig(system='v2-old')):
            with self.assertRaises(ValueError):config.validate()

    def test_bias_only_changes_post_alignment_cached_waypoints(self):
        o = observation((-.3, 0, .02)); p = FixedInsertion(o, BASE); p.calibrate(o)
        before = {k:v.copy() for k,v in p.targets.items()}
        p.bias_insertion_waypoints(np.array([0., .006, 0.]))
        for name in before:
            np.testing.assert_array_equal(p.targets[name], before[name] + ([0., .006, 0.] if name in ('offset','insert','settle') else [0,0,0]))
        with self.assertRaises(ValueError):p.bias_insertion_waypoints(np.array([0., .006, 0.]))

    def test_injection_requires_actual_safe_precontact_alignment_and_acquisition(self):
        o = observation((-.36, 0, .1)); p = FixedInsertion(o, BASE); p.calibrate(o)
        record = perturb_waypoints(p, o, {"valid_acquisition":True}, info(), 2., False)
        self.assertTrue(record['applied']);self.assertAlmostEqual(record['requested_magnitude_m'], .006)
        p = FixedInsertion(o, BASE);p.calibrate(o)
        i = info();i['peg_box_contact_force_world_n']=[1.,0.,0.]
        self.assertFalse(perturb_waypoints(p,o,{"valid_acquisition":True},i,2.,False)['applied'])
        self.assertFalse(perturb_waypoints(p,o,{"valid_acquisition":False},info(),2.,False)['applied'])

    def test_earlier_attachment_failure_consumes_single_episode(self):
        o = observation(aperture=0.); p = FixedInsertion(o, BASE); r = InsertionRecovery(p)
        r.action(o, 180, {'status':'failed','failure':'GRASP_FAILURE'})
        self.assertEqual(r.state, 'aborted');self.assertEqual(r.attempts,1)
        for step in range(181,185):r.action(observation(),step,{'status':'failed','failure':'INSERTION_DEPTH_NOT_ACHIEVED'})
        self.assertEqual(r.attempts,1);self.assertEqual(r.steps,0)

    def test_tcp_arrival_does_not_finish_backout(self):
        o=observation();p=FixedInsertion(o,BASE);r=InsertionRecovery(p)
        r.action(o,635,{'status':'failed','failure':'INSERTION_DEPTH_NOT_ACHIEVED'})
        r.stage_steps=3
        # TCP coordinates alone cannot establish the peg's safe physical relation.
        r.target=np.array(o['extra']['tcp_pose'][:3]);r.observe(o)
        self.assertEqual(r.stage,0);self.assertEqual(r.completed_stages,[])

    def test_effect_gates_refresh_and_complete_in_order(self):
        o=observation();p=FixedInsertion(o,BASE);r=InsertionRecovery(p)
        r.action(o,635,{'status':'failed','failure':'INSERTION_DEPTH_NOT_ACHIEVED'})
        safe=observation((-.36,0,.1));r.stage_steps=3;r.observe(safe)
        self.assertEqual(r.completed_stages,['backout']);self.assertIsNotNone(r.refresh_record)
        r.stage_steps=3;r.observe(safe);self.assertEqual(r.completed_stages,['backout','realign'])
        r.stage_steps=3;r.observe(o);self.assertEqual(r.completed_stages,['backout','realign','reinsert'])
        for _ in range(10):r.stage_steps+=1;r.observe(o)
        self.assertEqual(r.state,'attempt_complete');self.assertEqual(r.attempts,1)

    def test_stage_cap_aborts_without_reinsert(self):
        o=observation();p=FixedInsertion(o,BASE);r=InsertionRecovery(p)
        r.action(o,635,{'status':'failed','failure':'INSERTION_DEPTH_NOT_ACHIEVED'})
        r.stage_steps=120;r.observe(o)
        self.assertEqual(r.state,'aborted');self.assertEqual(r.completed_stages,[])

    def test_failed_verdict_is_required_to_start(self):
        o=observation();r=InsertionRecovery(FixedInsertion(o,BASE))
        for status in ('waiting','monitoring','succeeded'):
            r.action(o,1,{'status':status,'failure':None})
        self.assertEqual(r.attempts,0)


class Box:
    shape=(7,)
    def seed(self,seed):pass
    def contains(self,a):return a.shape==(7,) and np.isfinite(a).all()


class KinematicFixture:
    """Logging fixture, not native-physics commissioning evidence."""
    action_space=Box()
    def __init__(self):
        self.unwrapped=SimpleNamespace(agent=SimpleNamespace(robot=SimpleNamespace(pose=SimpleNamespace(raw_pose=BASE))))
        self.closed=False
    def reset(self,seed):
        self.o=observation((-.3,0,.02),aperture=.08)
        self.o['extra']['tcp_pose']=pose([-.36,0,.2],np.diag([1.,-1.,-1.]))
        self.steps=0;self.held=False;self.offset=None;self.rot_offset=None
        return copy.deepcopy(self.o),info(False)
    def step(self,action):
        old=np.array(self.o['extra']['peg_pose'][:3])
        old_tcp=np.array(self.o['extra']['tcp_pose'][:3]);old_r=Rotation.from_quat(np.array(self.o['extra']['tcp_pose'])[[4,5,6,3]]).as_matrix()
        target=action[:3]+np.array(BASE[:3]);r=Rotation.from_euler('XYZ',action[3:6]).as_matrix()
        if action[-1]<0 and not self.held and np.linalg.norm(old_tcp-(old+np.array([-.06,0,0])))<.025:
            self.held=True;self.offset=old_r.T@(old-old_tcp);self.rot_offset=old_r.T
        self.o['extra']['tcp_pose']=pose(target,r)
        if self.held:
            new=target+r@self.offset;self.o['extra']['peg_pose']=pose(new,r@self.rot_offset)
            self.o['extra']['peg_linear_velocity']=((new-old)/.05).tolist()
        self.o['agent']['qpos'][-2:]=[.02,.02] if self.held else [.04,.04]
        self.steps+=1
        return copy.deepcopy(self.o),np.array([0.]),np.array([False]),np.array([self.steps==1200]),info(self.held)
    def close(self):self.closed=True


class PipelineTests(unittest.TestCase):
    def test_failed_target_guard_retains_post_action_observation(self):
        class MovingTargetFixture(KinematicFixture):
            def step(self, action):
                o, reward, term, trunc, i = super().step(action)
                o['extra']['box_hole_pose'][0] += 2e-6
                return o, reward, term, trunc, i
        with tempfile.TemporaryDirectory() as d:
            env = MovingTargetFixture()
            with self.assertRaisesRegex(ValueError, 'translation_delta_m'):
                run(M7DevelopmentConfig(output=Path(d)), env_factory=lambda:env,
                    observe_fn=lambda env,o,i:(json_value(o),json_value(i)), preflight_fn=lambda:{})
            directory = next(Path(d).iterdir())
            events = [json.loads(line) for line in (directory/'events.jsonl').read_text().splitlines()]
            failed = next(e for e in events if e['event']=='post_action_check_failed')
            self.assertEqual(failed['step'], 1)
            self.assertEqual(failed['observation']['extra']['box_hole_pose'][0], 2e-6)
            self.assertEqual(len(failed['action']), 7)
            self.assertEqual(failed['info'], info(False))
            self.assertTrue(env.closed)
            result = json.loads((directory/'result.json').read_text())
            self.assertEqual(result['failed_step'], 1)
            self.assertEqual(result['state'], 'error')

    def test_matched_logs_replay_and_detect_action_or_physical_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            results=[]
            native={'software':{'git_commit':'fixture','git_dirty':False},'installed_sources_sha256':{},'installed_assets_sha256':{},'inspection_receipt_sha256':'fixture','startup_environment_sha256':'fixture'}
            for system in ('baseline','v1','v2'):
                result=run(M7DevelopmentConfig(system=system,output=Path(d)/system),env_factory=KinematicFixture,
                           observe_fn=lambda env,o,i:(json_value(o),json_value(i)),preflight_fn=lambda:native)
                results.append(result)
                self.assertTrue(replay(result['run_directory'])['passed'])
                self.assertTrue(result['task_success_at_end'])
            self.assertEqual(results[2]['recovery']['attempts'],0)
            self.assertEqual(compare(results[0]['run_directory'],results[1]['run_directory'])['exact_steps'],1200)
            self.assertEqual(compare(results[1]['run_directory'],results[2]['run_directory'])['exact_steps'],1200)
            directory=Path(results[1]['run_directory']);path=directory/'events.jsonl';original=path.read_text()
            events=[json.loads(line) for line in original.splitlines()]
            e=next(e for e in events if e['event']=='step');e['action'][0]+=.001
            path.write_text('\n'.join(json.dumps(e) for e in events)+'\n')
            with self.assertRaises(ValueError):replay(directory)
            with self.assertRaises(ValueError):compare(results[0]['run_directory'],directory)
            path.write_text(original)
            events=[json.loads(line) for line in original.splitlines()]
            # Target identity bounds do not relax exact physical matched-pair checks.
            e=next(e for e in events if e['event']=='step')
            e['observation']['extra']['box_hole_pose'][0] += 2e-8
            path.write_text('\n'.join(json.dumps(e) for e in events)+'\n')
            with self.assertRaises(ValueError):compare(results[0]['run_directory'],directory)
            path.write_text(original)
            result=json.loads((directory/'result.json').read_text());result['task_success_at_end']=False
            (directory/'result.json').write_text(json.dumps(result))
            with self.assertRaises(ValueError):replay(directory)


if __name__=='__main__':unittest.main()
