"""M6 semantics, input isolation, exact causal pairing and evidence continuation."""

from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy.spatial.transform import Rotation

from aether_cl import m6_sweep as m6
from aether_cl.m6_audit import check_trial, compare
from aether_cl.m6_policy import FixedPlacement, PlacementRecovery, INJECTION_STEP, MAX_STEPS
from aether_cl.m6_runtime import UPSTREAM_SOURCE_MODULES, M6Config, run, reset_native, shift_native
from aether_cl.m6_task import PlacementReference, PlacementVerifier, SETTINGS, geometry
from aether_cl.verification import VerificationMetrics
from test_policy import Actions, BASE


SOFTWARE = {"git_commit": "fixture", "git_dirty": False, "python": "3.10.19", "packages": m6.NATIVE_PACKAGES}
NATIVE_SOURCES = {name: hashlib.sha256(name.encode()).hexdigest() for name in UPSTREAM_SOURCE_MODULES}


def state():
    return {"extra": {"obj_pose": [[-.04, -.03, .02, 1., 0., 0., 0.]], "goal_pos": [[.07, .04, .02]],
                      "tcp_pose": [[0., 0., .25, 0., 1., 0., 0.]], "obj_linear_velocity": [[0., 0., 0.]],
                      "obj_angular_velocity": [[0., 0., 0.]], "is_grasped": [False]},
            "agent": {"qpos": [[0.] * 7 + [.04, .04]], "qvel": [[0.] * 9]}}


class PlacementEnvironment:
    """Deterministic attachment/support fixture, not a native physics model."""

    def __init__(self, false_labels=False):
        self.unwrapped = self
        self.action_space = Actions()
        self.agent = SimpleNamespace(robot=SimpleNamespace(pose=SimpleNamespace(raw_pose=BASE)))
        self.closed = self.held = False
        self.false_labels = false_labels

    def reset(self, seed):
        self.seed, self.step_number = seed, 0
        self.obs = state()
        if seed == 111:
            self.obs["extra"]["obj_pose"][0][:3] = self.obs["extra"]["goal_pos"][0].copy()
        return copy.deepcopy(self.obs), self.info()

    def info(self):
        return {"is_grasped": [self.held and not self.false_labels], "success": [True], "is_robot_static": [True],
                "cube_table_contact_force_world_n": [[0., 0., 0. if self.held or self.false_labels else .5]]}

    def step(self, action):
        self.step_number += 1
        command = action.reshape(7)
        tcp = self.obs["extra"]["tcp_pose"][0]
        tcp[:3] = (command[:3].astype(float) + BASE[0, :3]).tolist()
        q = Rotation.from_euler("XYZ", command[3:6]).as_quat()
        tcp[3:] = [q[3], *q[:3]]
        cube = self.obs["extra"]["obj_pose"][0]
        if command[-1] > 0:
            if self.held:
                cube[2] = .02
            self.held = False
            self.obs["agent"]["qpos"][0][-2:] = [.04, .04]
        else:
            if np.linalg.norm(np.array(cube[:3]) - tcp[:3]) <= .04:
                self.held = True
            self.obs["agent"]["qpos"][0][-2:] = [.02, .02] if self.held else [0., 0.]
        if self.held:
            cube[:3] = tcp[:3].copy()
        self.obs["extra"]["is_grasped"] = [self.held]
        return copy.deepcopy(self.obs), [0.], [False], [self.step_number == MAX_STEPS], self.info()

    def close(self):
        self.closed = True


def reset_fixture(env, seed):
    obs, info = env.reset(seed)
    return obs, info, {"support_actor": "table-workspace", "table_pose_world": [-.12, 0., -.9196429, .70710678, 0., 0., .70710678],
                      "cube_half_size_m": .02, "original_sampled_goal_world_m": [*obs["extra"]["goal_pos"][0][:2], .20],
                      "goal_projection": "retain_sampled_xy_project_z_to_cube_center_on_table"}


def observe_fixture(env, observation, info):
    return observation, info


def shift_fixture(env, magnitude, observation, info, decision):
    class Cube:
        def set_pose(self, pose):
            env.obs["extra"]["obj_pose"][0] = [*pose[0], *pose[1]]
    env.cube, env.device = Cube(), "cpu"
    return shift_native(env, magnitude, observation, info, decision, pose_factory=lambda p, q, device: (p.tolist(), q.tolist()))


def fixture_run(config, environment=PlacementEnvironment, **kwargs):
    return run(config, env_factory=lambda _: environment(), reset_fn=reset_fixture, observe_fn=observe_fixture,
               shift_fn=shift_fixture, native_sources_fn=lambda: NATIVE_SOURCES, **kwargs)


class SemanticTests(unittest.TestCase):
    def test_success_requires_release_contact_support_retraction_and_fresh_stability(self):
        for failure in (None, "held", "no_contact", "not_retracted", "off_target", "velocity", "moving_frames", "angular"):
            with self.subTest(failure=failure):
                obs = state(); ref = PlacementReference(obs)
                close = {"phase": "close", "phase_step": 25, "gripper": "closed"}
                obs["extra"]["obj_pose"][0][2] = .14
                obs["extra"]["tcp_pose"][0][:3] = obs["extra"]["obj_pose"][0][:3].copy()
                obs["agent"]["qpos"][0][-2:] = [.02, .02]
                ref.observe(obs, {"is_grasped": [True], "cube_table_contact_force_world_n": [[0., 0., 0.]]}, 1, close)
                obs["extra"]["obj_pose"][0][:3] = [.07, .04, .02]
                obs["extra"]["tcp_pose"][0][:3] = [.07, .04, .14]
                obs["agent"]["qpos"][0][-2:] = [.04, .04]
                info = {"is_grasped": [False], "cube_table_contact_force_world_n": [[0., 0., .5]]}
                decision = {"phase": "release", "phase_step": 25, "gripper": "open"}
                if failure == "held": info["is_grasped"] = [True]
                if failure == "no_contact": info["cube_table_contact_force_world_n"] = [[0., 0., 0.]]
                if failure == "not_retracted": obs["extra"]["tcp_pose"][0][2] = .04
                if failure == "off_target": obs["extra"]["obj_pose"][0][1] += .04
                if failure == "velocity": obs["extra"]["obj_linear_velocity"] = [[.1, 0., 0.]]
                if failure == "angular": obs["extra"]["obj_angular_velocity"] = [[0., 0., 1.]]
                for step in range(2, 9):
                    if failure == "moving_frames": obs["extra"]["obj_pose"][0][0] += .002
                    truth = ref.observe(copy.deepcopy(obs), info, step, decision)
                    if step < 7: self.assertFalse(truth["task_success"])
                self.assertEqual(truth["task_success"], failure is None)
                if failure == "off_target": self.assertTrue(truth["support_stability_success"])
                with self.assertRaisesRegex(ValueError, "consecutive"):
                    ref.observe(obs, info, 8, decision)

    def test_held_target_and_environment_success_do_not_count_as_placement(self):
        obs = state(); ref = PlacementReference(obs)
        obs["extra"]["obj_pose"][0][:3] = [.07, .04, .14]
        obs["extra"]["tcp_pose"][0][:3] = [.07, .04, .14]
        obs["agent"]["qpos"][0][-2:] = [.02, .02]
        for step in range(1, 20):
            value = ref.observe(obs, {"is_grasped": [True], "success": [True], "cube_table_contact_force_world_n": [[0., 0., 0.]]},
                                step, {"phase": "transport", "phase_step": step, "gripper": "closed"})
            self.assertFalse(value["task_success"])

    def test_nominal_reuses_unchanged_servo_and_reads_only_tcp_after_reset(self):
        obs = state(); policy = FixedPlacement(obs, BASE)
        phases = []
        for i in range(MAX_STEPS):
            action, decision = policy.action(obs, i)
            if not phases or phases[-1] != decision["phase"]: phases.append(decision["phase"])
            stripped = {"extra": {"tcp_pose": obs["extra"]["tcp_pose"]}}
            aa, dd = policy.action(stripped, i)
            np.testing.assert_array_equal(action, aa); self.assertEqual(decision, dd)
        self.assertEqual(phases, list(m6.PHASES))
        self.assertEqual(INJECTION_STEP, 296)
        self.assertEqual(m6.NOMINAL_STEPS, 360)

    def test_verifier_invalid_state_is_uncertain_and_does_not_accept_stale_frames(self):
        obs = state(); verifier = PlacementVerifier(obs)
        bad = copy.deepcopy(obs); bad["extra"].pop("obj_linear_velocity")
        d = {"phase": "settle", "phase_step": 15, "gripper": "open"}
        self.assertEqual(verifier.observe(bad, 1, d)["status"], "uncertain")
        with self.assertRaises(ValueError): verifier.observe(obs, 1, d)
        self.assertIn(verifier.observe(obs, 2, d)["status"], ("pending", "failed"))

    def test_injection_skips_invalid_release_without_excluding_or_granting_retry(self):
        env = PlacementEnvironment(); obs, info = env.reset(100)
        record = shift_fixture(env, .08, obs, info, {"phase": "lift"})
        self.assertFalse(record["applied"])
        self.assertEqual(record["reason"], "release_precondition_not_satisfied")
        np.testing.assert_array_equal(env.obs["extra"]["obj_pose"], obs["extra"]["obj_pose"])

    def test_one_attempt_remains_consumed_after_abort_or_completion(self):
        obs = state(); recovery = PlacementRecovery(FixedPlacement(obs, BASE), BASE)
        recovery.action(obs, 1, {})
        recovery.action(obs, 2, {"status": "failed", "failure": "PLACEMENT_TARGET_NOT_REACHED"})
        self.assertEqual(recovery.attempts, 1)
        recovery.abort("fixture_abort")
        snapshot = recovery.snapshot()
        for step in range(3, 20):
            recovery.action(obs, step, {"status": "failed", "failure": "OBJECT_LOST"})
            recovery.observe(obs)
            self.assertEqual(recovery.snapshot(), snapshot)


class RuntimeTests(unittest.TestCase):
    def test_native_adapter_projects_goal_and_queries_designated_support(self):
        env = PlacementEnvironment()
        original_reset = env.reset
        class Goal:
            pose = SimpleNamespace(p=np.array([[.07, .04, .20]]))
            def set_pose(self, p): self.pose.p = np.array([p])
        env.goal_site = Goal()
        env.device = "cpu"
        env.cube_half_size = .02
        env.table_scene = SimpleNamespace(table=SimpleNamespace(name="table-workspace", pose=SimpleNamespace(raw_pose=np.array([[-.12, 0, -.9196429, 2**-.5, 0, 0, 2**-.5]]))))
        env.cube = SimpleNamespace(pose=SimpleNamespace(p=np.array([[-.04, -.03, .02]])), linear_velocity=np.zeros((1, 3)), angular_velocity=np.zeros((1, 3)))
        query = unittest.mock.Mock(return_value=np.array([[0., 0., .5]]))
        env.scene = SimpleNamespace(get_pairwise_contact_forces=query)
        env.evaluate = env.info
        env.reset = original_reset
        obs, info, support = reset_native(env, 100, pose_factory=lambda p, device: p)
        np.testing.assert_array_equal(obs["extra"]["goal_pos"], [[.07, .04, .02]])
        self.assertEqual(support["original_sampled_goal_world_m"], [.07, .04, .20])
        query.assert_called_once_with(env.cube, env.table_scene.table)
        np.testing.assert_array_equal(info["cube_table_contact_force_world_n"], [[0., 0., .5]])
        env.gpu_sim_enabled = True
        with self.assertRaisesRegex(RuntimeError, "CPU"): reset_native(env, 100)

    def test_three_systems_pair_exactly_and_recovery_replaces_and_releases(self):
        with tempfile.TemporaryDirectory() as temp, patch("aether_cl.m6_runtime.software_manifest", return_value=SOFTWARE):
            root = Path(temp); paths = {}
            for name, magnitude in (("none", .08), ("post_release_shift", .01), ("post_release_shift", .08), ("post_release_shift", .20)):
                for system in m6.SYSTEMS:
                    c = M6Config(system=system, verification=system != "baseline", seed=100, disturbance=name,
                                 disturbance_magnitude=magnitude, output=root / f"{name}-{magnitude}-{system}")
                    result = fixture_run(c); directory = Path(result["run_directory"])
                    checked = check_trial(directory, c, SOFTWARE)
                    self.assertTrue(checked["passed"], checked["failed_checks"])
                    paths[(name, magnitude, system)] = directory
                    e = result["episodes"][0]
                    expected = name == "none" or magnitude == .01 or system == "v2"
                    self.assertEqual(e["task_success_at_end"], expected)
                    self.assertTrue(e["release_success_at_end"])
                    self.assertTrue(e["controller_complete"])
                    self.assertEqual(e["recovery"]["attempts"], int(system == "v2" and name != "none" and magnitude > .01))
                self.assertTrue(compare(paths[(name, magnitude, "baseline")], paths[(name, magnitude, "v1")], "passive")["passed"])
                self.assertTrue(compare(paths[(name, magnitude, "v1")], paths[(name, magnitude, "v2")], "recovery")["passed"])
                if name != "none": self.assertTrue(compare(paths[("none", .08, "baseline")], paths[(name, magnitude, "baseline")], "control")["passed"])
            # A plausible altered reference must fail reconstruction even when final success is unchanged.
            directory = paths[("post_release_shift", .20, "v2")]
            p = directory / "events.jsonl"; events = [json.loads(l) for l in p.read_text().splitlines()]
            next(e for e in events if e["event"] == "step" and e["step"] == 50)["reference"]["supported"] = False
            # At this stage cube is on table and not yet lifted, so support is true.
            p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
            self.assertFalse(check_trial(directory, c, SOFTWARE)["passed"])

    def test_reference_contact_labels_never_change_actions_and_exclusions_are_zero_action(self):
        with tempfile.TemporaryDirectory() as temp, patch("aether_cl.m6_runtime.software_manifest", return_value=SOFTWARE):
            root = Path(temp); traces = []
            for i, factory in enumerate((PlacementEnvironment, lambda: PlacementEnvironment(false_labels=True))):
                # No injection here: changing its physical precondition changes the intervention itself.
                c = M6Config(seed=100, output=root / str(i))
                result = fixture_run(c, environment=factory)
                events = [json.loads(l) for l in (Path(result["run_directory"]) / "events.jsonl").read_text().splitlines()]
                traces.append([{k: e[k] for k in ("action", "controller_decision", "verification", "recovery")} for e in events if e["event"] == "step"])
            self.assertEqual(traces[0], traces[1])
            c = M6Config(seed=111, output=root / "excluded")
            result = fixture_run(c)
            self.assertTrue(result["episodes"][0]["excluded"])
            self.assertEqual(result["episodes"][0]["steps"], 0)
            checked = check_trial(Path(result["run_directory"]), c, SOFTWARE)
            self.assertTrue(checked["passed"], checked["failed_checks"])

    def test_stop_keeps_evidence_and_has_no_complete_rate(self):
        stop = threading.Event()
        class Stopped(PlacementEnvironment):
            def step(self, action):
                value = super().step(action)
                if self.step_number == 2: stop.set()
                return value
        with tempfile.TemporaryDirectory() as temp:
            result = fixture_run(M6Config(output=Path(temp)), environment=Stopped, stop=stop)
            self.assertEqual(result["state"], "stopped")
            self.assertFalse(result["evaluation"]["complete"])
            self.assertIsNone(result["evaluation"]["task_success_rate_at_end"])


class SweepTests(unittest.TestCase):
    def child(self, config, environment):
        config.validate(); self.calls.append((config.seed, config.system, config.disturbance, config.disturbance_magnitude))
        self.environments.append(environment.copy())
        directory = config.output / "fixture"; directory.mkdir(parents=True)
        (directory / "raw.json").write_text(json.dumps({"seed": config.seed, "system": config.system}))
        return {"run_directory": str(directory)}

    def check(self, trial, software):
        c = trial["config"]; excluded = c["seed"] == 111
        good = c["disturbance"] == "none" or c["disturbance_magnitude"] == .01
        attempt = not excluded and c["system"] == "v2" and not good
        success = not excluded and (good or attempt and c["disturbance_magnitude"] < .20)
        e = {"seed": c["seed"], "excluded": excluded, "steps": 0 if excluded else MAX_STEPS, "task_success_at_end": success,
             "release_success_at_end": not excluded, "support_stability_success_at_end": success, "retraction_success_at_end": not excluded,
             "controller_complete": not attempt or success, "first_detected_failure": None, "first_failure_latency_steps": None,
             "disturbance_attempted": not excluded and c["disturbance"] != "none", "disturbance_applied": not excluded and c["disturbance"] != "none",
             "recovery_task_success": attempt and success, "total_observed_tcp_path_m": 1.5 if attempt else .8, "final_horizontal_error_m": .01 if success else .2,
             "recovery": {"attempts": int(attempt), "state": "attempt_complete" if attempt and success else "aborted" if attempt else "nominal",
                          "action_steps": 200 if attempt else 0, "observed_tcp_path_m": .7 if attempt else 0., "failure_detail": "fixture" if attempt and not success else None}}
        return {"passed": True, "checks": {"fixture": True}, "failed_checks": [], "episodes": [e], "max_action_replay_error": 0.,
                "native_sources_sha256": NATIVE_SOURCES,
                "evaluation": {"verification_metrics": VerificationMetrics().result(True) if c["verification"] else None}}

    def mocks(self, stack):
        self.calls, self.environments = [], []
        stack.enter_context(patch.object(m6, "software_manifest", return_value=SOFTWARE))
        stack.enter_context(patch.object(m6, "launch_child", side_effect=self.child))
        stack.enter_context(patch.object(m6, "checked_trial", side_effect=self.check))
        stack.enter_context(patch.object(m6, "compare", return_value={"passed": True, "checks": {"fixture": True}}))
        stack.enter_context(redirect_stdout(io.StringIO()))

    def verify_archive(self, path):
        with tarfile.open(path) as bundle:
            index = json.load(bundle.extractfile("m6-placement/archive_index.json"))
            self.assertEqual(len(bundle.getnames()), len(set(bundle.getnames())))
            self.assertEqual(set(bundle.getnames()), {i["path"] for i in index["files"]} | {"m6-placement/archive_index.json"})
            for entry in index["files"]:
                data = bundle.extractfile(entry["path"]).read()
                self.assertEqual(len(data), entry["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])

    def test_360_slots_first18_resume_and_all_340_comparisons(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            self.mocks(stack); root = Path(temp); output, archive = root / "study", root / "evidence.tar.gz"
            a = m6.run_sweep(output, archive, stop_after=18)
            self.assertEqual(a["state"], "paused")
            self.assertEqual(len(a["episode_trials"]), 18)
            self.assertTrue(m6.check_pilot(a)["passed"])
            changed = copy.deepcopy(a)
            for t in changed["episode_trials"]:
                if t["system"] == "v2": t["episodes"][0]["task_success_at_end"] = False
            self.assertTrue(m6.check_pilot(changed)["passed"])
            self.assertEqual([t["system"] for t in a["episode_trials"][:3]], list(m6.SYSTEMS))
            partial = Path(a["saved_archive"]); digest = hashlib.sha256(partial.read_bytes()).hexdigest()
            self.verify_archive(partial)
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in a["cells"]))
            b = m6.run_sweep(output, archive, resume=True)
            self.assertEqual(b["state"], "passed")
            self.assertEqual(len(self.calls), 360)
            self.assertEqual(len(set(self.calls)), 360)
            self.assertEqual(len(b["cells"]), 18)
            for group, count in m6.protocol()["comparison_counts"].items(): self.assertEqual(len(b[group]), count)
            normal = b["paired_outcomes"][0]
            self.assertEqual(normal["unnecessary_recovery_rate_on_baseline_success"], 0.)
            self.assertEqual(normal["regression_rate_on_baseline_success"], 0.)
            hard = b["paired_outcomes"][-1]
            self.assertEqual(hard["success_rate_difference_v2_minus_v1"], 0.)
            self.assertIsNone(hard["unnecessary_recovery_rate_on_baseline_success"])
            self.assertEqual(hard["mean_paired_extra_retry_actions"], 200.)
            self.assertTrue(all(c["excluded_seeds"] == [111] for c in b["cells"]))
            self.assertTrue(all(e == self.environments[0] for e in self.environments))
            self.assertEqual(hashlib.sha256(partial.read_bytes()).hexdigest(), digest)
            self.verify_archive(archive)

    def test_failed_slots_are_retained_and_resume_guards_hash_environment_and_lock(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            self.mocks(stack); root = Path(temp); output, archive = root / "study", root / "evidence.tar.gz"
            with patch.object(m6, "launch_child", side_effect=RuntimeError("fixture error")):
                a = m6.run_sweep(output, archive, stop_after=1)
            b = m6.run_sweep(output, archive, resume=True, stop_after=2)
            self.assertEqual(b["episode_trials"][0], a["episode_trials"][0])
            self.assertEqual(self.calls[0][1], "v1")
            with patch.dict("os.environ", {"M6_CHANGED": "1"}):
                with self.assertRaisesRegex(ValueError, "environment"): m6.run_sweep(output, archive, resume=True)
            with (output / "runner.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError, "owns"): m6.run_sweep(output, archive, resume=True)
            raw = Path(b["episode_trials"][1]["run_directory"]) / "raw.json"; raw.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "hashes"): m6.run_sweep(output, archive, resume=True)

    def test_preregistration_guard_precedes_output_and_plan_is_fixed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); value = m6.protocol(); value["max_steps"] = 801
            p = root / "bad_protocol.json"; p.write_text(json.dumps(value))
            with patch.object(m6, "PROTOCOL_PATH", p):
                with self.assertRaisesRegex(ValueError, "preregistration"): m6.run_sweep(root / "absent", root / "evidence.tar.gz")
            self.assertFalse((root / "absent").exists())
            self.assertEqual(m6.SEEDS, tuple(range(100, 120)))
            self.assertEqual(len(m6.plan(root)), 360)

    def test_native_source_drift_invalidates_all_scientific_rates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trials = []
            for item in m6.plan(root):
                t = {**item, **self.check(item, SOFTWARE), "run_directory": str(root / "fixture")}
                trials.append(t)
            trials[-1]["native_sources_sha256"] = {"fixture": "drifted-source"}
            report = {"episode_trials": trials}
            with patch.object(m6, "compare", return_value={"passed": True}): m6.summarize(report, root)
            self.assertFalse(report["native_source_identity_consistent"])
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in report["cells"]))
            self.assertTrue(all(p["success_rate_difference_v2_minus_v1"] is None for p in report["paired_outcomes"]))


class ViewerTests(unittest.TestCase):
    def test_m6_page_labels_systems_and_preserves_final_status_and_frame(self):
        from urllib.request import urlopen
        from aether_cl.m6 import make_server
        from aether_cl.viewer import Snapshot
        snapshot = Snapshot(); snapshot.publish({"state": "finished", "system": "v2", "step": 800}, b"final-frame")
        server = make_server(0, snapshot)
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            with urlopen(url) as r: page = r.read().decode()
            self.assertIn("AETHER-CL M6", page)
            self.assertIn("V2 — verification and one recovery", page)
            self.assertNotIn("Policy Baseline", page)
            for _ in range(2):
                with urlopen(url + "/api/status") as r: status = json.load(r)
                self.assertEqual(status["state"], "finished")
                self.assertEqual(status["system"], "v2")
                with urlopen(url + "/frame.jpg") as r: self.assertEqual(r.read(), b"final-frame")
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=2)

    def test_preview_cancel_executes_zero_actions_and_closes_environment(self):
        from aether_cl.m3 import PreviewSnapshot
        class Rendered(PlacementEnvironment):
            def render(self):
                frame = np.zeros((10, 10, 3), dtype=np.uint8)
                frame[:5, :, 0] = 100
                return frame
        stop = threading.Event(); snapshot = PreviewSnapshot(stop); env = Rendered()
        results = []
        with tempfile.TemporaryDirectory() as temp:
            def worker():
                results.append(run(M6Config(render=True, output=Path(temp)), snapshot.publish, stop,
                                   env_factory=lambda _: env, reset_fn=reset_fixture, observe_fn=observe_fixture,
                                   shift_fn=shift_fixture, native_sources_fn=lambda: NATIVE_SOURCES))
            thread = threading.Thread(target=worker); thread.start()
            try:
                self.assertTrue(snapshot.ready.wait(3))
                self.assertEqual(snapshot.read()[0]["state"], "ready_to_start")
                self.assertEqual(env.step_number, 0)
                stop.set(); thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertTrue(env.closed)
                self.assertEqual(env.step_number, 0)
                self.assertEqual(results[0]["state"], "stopped")
            finally:
                stop.set(); snapshot.release.set(); thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
