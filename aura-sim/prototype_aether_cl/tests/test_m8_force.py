"""M8 schedule/provenance fixtures; these do not establish native physics."""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl.m8_force import (ForceTrace, ForceEnvironment, candidate_points, receipt,
    release_precondition, verify_body, INJECTION_STEP)
from aether_cl.m8_force_commission import plan, validate_child, audit_physics, write_json, run_suite


def observation(cube=None):
    return {"extra": {"obj_pose": [[0., 0., .02, 1., 0., 0., 0.]] if cube is None else cube.pose.raw_pose.tolist(),
        "tcp_pose": [[0.,0.,.2,1.,0.,0.,0.]], "goal_pos": [[.1,.1,.02]],
        "obj_linear_velocity": [[0.,0.,0.]] if cube is None else cube.linear_velocity.tolist(),
        "obj_angular_velocity": [[0.,0.,0.]]},
        "agent": {"qpos": [[0.]*7+[.04,.04]], "qvel": [[0.]*9]}}


INFO = {"is_grasped": [False], "cube_table_contact_force_world_n": [[0.,0.,.5]]}


class Body:
    def __init__(self, expected):
        for n,v in expected["physical_properties"]["values"].items():
            setattr(self,n,v)
        self.calls = []
        self.collision_shapes = [SimpleNamespace(half_size=np.array(s["geometry"]["values"]["half_size"]),
            physical_material=SimpleNamespace(**s["material"]["values"])) for s in expected["collision_shapes"]]

    def add_force_torque(self, force, torque, mode):
        self.calls.append((force.copy(),torque.copy(),mode))


Body.add_force_torque.__doc__ = receipt()["force_binding_docs"]["add_force_torque"]


class Fixture:
    def __init__(self):
        r = receipt()
        self.unwrapped = self
        self.num_envs,self.sim_freq,self.control_freq,self._sim_steps_per_control = 1,100,20,5
        self.gpu_sim_enabled = False
        self.cube = SimpleNamespace(_bodies=[Body(r["cube"])], pose=SimpleNamespace(raw_pose=np.array([[0.,0.,.02,1.,0.,0.,0.]])),
            linear_velocity=np.zeros((1,3)),angular_velocity=np.zeros((1,3)))
        self.table_scene = SimpleNamespace(table=SimpleNamespace(_bodies=[Body(r["table"])]))
        self.agent = SimpleNamespace(finger1_link=object(),finger2_link=object())
        self.scene = SimpleNamespace(px=SimpleNamespace(timestep=r["actual_timestep_s"]),
            get_pairwise_contact_forces=lambda a,b: np.array([[0.,0.,.5]]) if b is self.table_scene.table else np.zeros((1,3)))
        self.sim_config = SimpleNamespace(scene_config=SimpleNamespace(gravity=np.array([0,0,-9.81])))

    def _before_simulation_step(self):
        pass

    def _after_simulation_step(self):
        pass

    def advance(self):
        # Fixture integration only; native response must be measured separately.
        body=self.cube._bodies[0]
        if body.calls:
            self.cube.linear_velocity[0] += body.calls[-1][0] / body.mass * self.scene.px.timestep
        self.cube.pose.raw_pose[0,:3] += self.cube.linear_velocity[0] * self.scene.px.timestep


class ForceCommissionTests(unittest.TestCase):
    def trace(self, fixture, point, records):
        hooks=receipt()["physics_hooks"]
        with patch("aether_cl.m8_force.inspect.getsource", lambda m: hooks[m.__name__]["source"]):
            return ForceTrace(fixture,point,records.append)

    def sample_action(self, fixture, trace):
        for _ in range(5):
            fixture._before_simulation_step()
            fixture.advance()
            fixture._after_simulation_step()
        return trace.end()

    def test_fixed_known_seed_plan_and_no_fresh_entry(self):
        slots=plan()
        self.assertEqual(len(slots),20)
        self.assertEqual({p["seed"] for p in slots},{100,101})
        self.assertEqual([sum(p["kind"]==k for p in slots) for k in ("original","main","repeat")],[2,12,6])
        for seed in (True,99,140,159,160,179,2022):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                validate_child(seed,"main","normal")
        with self.assertRaises(ValueError):validate_child(100,"original","model-drift-080mm")

    def test_candidates_are_monotonic_newtons_derived_from_measured_properties(self):
        points=candidate_points()
        self.assertEqual(points[0]["command_force_y_n"],0)
        self.assertTrue(all(a["command_force_y_n"]<b["command_force_y_n"] for a,b in zip(points,points[1:])))
        self.assertTrue(all(p["planned_nominal_duration_s"]==.05 for p in points))
        for p in points[1:]:
            self.assertGreater(p["command_force_y_n"],receipt()["cube"]["physical_properties"]["values"]["mass"]*.3*9.81)
            self.assertEqual(p["command_force_world_n"],[0.,p["command_force_y_n"],0.])

    def test_release_requires_nominal_retract_open_not_grasped_and_supported(self):
        self.assertTrue(release_precondition(observation(),INFO,"retract"))
        for phase,info in (("release",INFO),("recovery_retract",INFO),
            ("retract",{**INFO,"is_grasped":[True]}),
            ("retract",{**INFO,"cube_table_contact_force_world_n":[[0,0,0]]})):
            self.assertFalse(release_precondition(observation(),info,phase))

    def test_exactly_five_engine_force_calls_only_in_fixed_window(self):
        fixture=Fixture();records=[];trace=self.trace(fixture,candidate_points()[3],records)
        before_hook=trace.original_before
        trace.begin(INJECTION_STEP-1,observation(fixture.cube),INFO,"release")
        self.sample_action(fixture,trace)
        self.assertEqual(trace.total_calls,0)
        trace.begin(INJECTION_STEP,observation(fixture.cube),INFO,"retract")
        pulse=self.sample_action(fixture,trace)
        self.assertEqual(trace.total_calls,5)
        self.assertTrue(all(s["force_call_executed"] for s in pulse["substeps"]))
        self.assertEqual({c[2] for c in fixture.cube._bodies[0].calls},{"force"})
        self.assertTrue(all(c[0].dtype==np.float32 and not c[1].any() for c in fixture.cube._bodies[0].calls))
        trace.begin(INJECTION_STEP+1,observation(fixture.cube),INFO,"retract")
        self.sample_action(fixture,trace)
        self.assertEqual(trace.total_calls,5)
        trace.close()
        self.assertEqual(fixture._before_simulation_step,before_hook)
        self.assertNotIn("_before_simulation_step",fixture.__dict__)

    def test_zero_and_missed_precondition_never_apply_force_or_retime(self):
        for point,info in ((candidate_points()[0],INFO),(candidate_points()[1],{**INFO,"is_grasped":[True]})):
            fixture=Fixture();trace=self.trace(fixture,point,[])
            trace.begin(INJECTION_STEP,observation(),info,"retract")
            self.sample_action(fixture,trace)
            trace.begin(INJECTION_STEP+1,observation(),INFO,"retract")
            self.sample_action(fixture,trace)
            self.assertEqual(trace.total_calls,0)
            trace.close()

    def test_force_call_may_not_overwrite_pose_or_velocity(self):
        fixture=Fixture();records=[];trace=self.trace(fixture,candidate_points()[1],records)
        trace.body.add_force_torque=lambda **kw: fixture.cube.linear_velocity.fill(1)
        trace.begin(INJECTION_STEP,observation(),INFO,"retract")
        with self.assertRaisesRegex(ValueError,"before physics"):
            fixture._before_simulation_step()
        self.assertEqual(records[-1]["event"],"force_call_unexpected_state_change")
        trace.close()

    def test_changed_material_and_incomplete_sampling_block(self):
        fixture=Fixture()
        fixture.cube._bodies[0].collision_shapes[0].physical_material.dynamic_friction=.9
        with self.assertRaisesRegex(ValueError,"material"):
            verify_body(fixture.cube,receipt()["cube"])
        fixture=Fixture();trace=self.trace(fixture,candidate_points()[0],[])
        trace.begin(1,observation(),INFO,"approach")
        with self.assertRaisesRegex(ValueError,"five complete"):
            trace.end()
        trace.close()

    def test_proxy_passes_the_original_controller_action_unchanged(self):
        action=np.zeros(7,dtype=np.float32);seen=[]
        env=SimpleNamespace(step=lambda a: seen.append(a) or ("result",))
        proxy=ForceEnvironment(env)
        proxy.trace=SimpleNamespace(begin=lambda *args:None,end=lambda:None)
        proxy.policy=SimpleNamespace(phase=lambda index:("approach",1))
        self.assertEqual(proxy.step(action),("result",))
        self.assertIs(seen[0],action)

    def test_physics_audit_detects_tampered_force_and_endpoint(self):
        fixture=Fixture();records=[];point=candidate_points()[1];trace=self.trace(fixture,point,records)
        prior=observation(fixture.cube)
        trace.begin(INJECTION_STEP,prior,INFO,"retract")
        physical=self.sample_action(fixture,trace);trace.close()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/"native";native.mkdir()
            write_json(native/"manifest.json",{"config":{"disturbance":"none"}})
            write_json(native/"result.json",{})
            events=[{"event":"reset","observation":prior,"info":INFO},
                {"event":"step","step":INJECTION_STEP,"controller_decision":{"phase":"retract"},
                 "observation":observation(fixture.cube),"info":INFO}]
            (native/"events.jsonl").write_text("".join(json.dumps(e)+'\n' for e in events))
            starts={"event":"force_trace_started","seed":100,"point":point}
            def save():
                (root/"physics.jsonl").write_text(json.dumps(starts)+'\n'+json.dumps(physical)+'\n')
            save()
            carrier={"run_relative":"native","seed":100}
            self.assertTrue(audit_physics(root,carrier,point)["passed"])
            physical["substeps"][0]["force_world_n"][1]+=1
            save()
            self.assertFalse(audit_physics(root,carrier,point)["passed"])
            physical["substeps"][0]["force_world_n"][1]-=1
            physical["substeps"][-1]["after_physics"]["cube_pose_world"][0][1]+=1
            save()
            self.assertFalse(audit_physics(root,carrier,point)["passed"])

    def test_production_adapter_has_one_force_mode_and_no_cube_setters(self):
        from aether_cl import m8_force,m8_force_commission
        trees=[ast.parse(Path(m.__file__).read_text()) for m in (m8_force,m8_force_commission)]
        forbidden={"set_pose","set_linear_velocity","set_angular_velocity","set_velocity","apply_impulse","shift_native"}
        calls=[n for t in trees for n in ast.walk(t) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in forbidden for n in calls))
        forces=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=="add_force_torque"]
        self.assertEqual(len(forces),1)
        self.assertEqual(ast.unparse(next(k.value for k in forces[0].keywords if k.arg=="mode")),"'force'")
        configs=[n for n in calls if isinstance(n.func,ast.Name) and n.func.id=="M6RConfig"]
        self.assertEqual(len(configs),1)
        self.assertEqual(ast.unparse(next(k.value for k in configs[0].keywords if k.arg=="disturbance")),"'none'")

    def test_timeout_retains_started_slot_partial_evidence_and_indexed_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/"study";archive=root/"study.tar.gz"
            def timeout(command, **kwargs):
                case=Path(command[command.index("--output")+1])
                (case/"partial_events.jsonl").write_text('{"event":"reset","seed":100}\n')
                raise subprocess.TimeoutExpired(command,600)
            with patch("aether_cl.m8_force_commission.preflight",return_value={"software":{}}), \
                 patch("aether_cl.m8_force_commission.subprocess.run",side_effect=timeout), \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run_suite(output,archive,"fixture-head")
            report=json.loads((output/"suite.json").read_text())
            self.assertEqual(report["state"],"error_retained")
            self.assertEqual(len(report["trials"]),1)
            self.assertEqual(report["trials"][0]["result"]["state"],"child_timeout_retained")
            with tarfile.open(archive) as bundle:
                index=json.load(bundle.extractfile("m8-force-commission/file_index.json"))
                relative=report["trials"][0]["directory"]+"/partial_events.jsonl"
                self.assertIn(relative,index)
                self.assertEqual(bundle.extractfile("m8-force-commission/"+relative).read(),
                    b'{"event":"reset","seed":100}\n')
            original=archive.read_bytes()
            with self.assertRaises(FileExistsError):
                run_suite(output,archive,"fixture-head")
            self.assertEqual(archive.read_bytes(),original)

    def test_initial_goal_exclusion_retains_zero_action_physics_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/"native";native.mkdir()
            write_json(native/"manifest.json",{"config":{"disturbance":"none"}})
            write_json(native/"result.json",{})
            (native/"events.jsonl").write_text(json.dumps(
                {"event":"reset","observation":observation(),"info":INFO})+'\n')
            point=candidate_points()[1]
            (root/"physics.jsonl").write_text(json.dumps(
                {"event":"force_trace_started","seed":100,"point":point})+'\n')
            audit=audit_physics(root,{"run_relative":"native","seed":100},point)
            self.assertTrue(audit["passed"])
            self.assertEqual(audit["external_physics_samples"],0)
            self.assertEqual(audit["force_calls"],0)
            self.assertIsNone(audit["effects"]["before_pulse"])


if __name__=="__main__":
    unittest.main()
