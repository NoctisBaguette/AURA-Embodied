"""Guard tests for source-pinned camera commissioning; no native simulator."""

import ast
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "aura-sim/prototype_aether_cl"))
import m9_camera_commission as COMMISSION
from aether_cl import m9_camera as CAMERA


def packet():
    rgb = np.zeros((CAMERA.HEIGHT, CAMERA.WIDTH, 3), dtype=np.uint8)
    rgb[..., 0] = np.arange(CAMERA.WIDTH, dtype=np.uint16).astype(np.uint8)
    depth = np.full((CAMERA.HEIGHT, CAMERA.WIDTH), 743, dtype=np.int16)
    depth[0, 0] = 0
    return {"primary_rgb": rgb, "secondary_rgb": rgb[..., ::-1].copy(),
        "primary_depth_mm": depth, "primary_validity": (depth > 0).astype(np.uint8),
        "qpos": np.arange(9, dtype=np.float32)/10}


class CameraCommissionGuards(unittest.TestCase):
    def test_json_writer_preserves_numpy_audit_values_including_failed_checks(self):
        from aether_cl.m6r_audit import finish
        audit = finish({"healthy": np.bool_(True), "failed": np.bool_(False)},
                       {"episodes": [{"steps": np.int64(800)}]}, np.float32(0.), {})
        audit["native_array"] = np.array([1, 2], dtype=np.int32)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit.json"
            COMMISSION.write_json(path, audit)
            saved = json.loads(path.read_text())
            self.assertFalse(saved["passed"])
            self.assertIs(saved["checks"]["healthy"], True)
            self.assertIs(saved["checks"]["failed"], False)
            self.assertEqual(saved["failed_checks"], ["failed"])
            self.assertEqual(saved["episodes"][0]["steps"], 800)
            self.assertEqual(saved["native_array"], [1, 2])
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                COMMISSION.write_json(path, {"replacement": True})
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_json_never_creates_an_empty_audit_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            for bad in (np.float32(np.nan), np.array([np.inf]), object()):
                path = Path(temporary) / "invalid.json"
                with self.assertRaises((TypeError, ValueError)):
                    COMMISSION.write_json(path, {"bad": bad})
                self.assertFalse(path.exists())

    def failure_archive_fixture(self, path, change=None):
        from dataclasses import asdict
        from aether_cl.m6r_runtime import M6RConfig
        from aether_cl.runtime import json_value
        identity = {"development_witness": "fixture"}
        episode = {"task_success": True, "steps": 800}
        carrier = {"state": "error_retained", "error": COMMISSION.REPORTING_FAILURE_ERROR,
            "traceback": "original bool_ serialization failure", "mode": "unrendered",
            "seed": 100, "system": "baseline", "run_relative": "native/retained",
            "episode": episode, "native_config": json_value(asdict(M6RConfig(
                seed=100, system="baseline", verification=False, render=False, disturbance="none",
                output=Path("/original/retained/unrendered/native"))))}
        body = {
            "commissioning.json": {"native_head": COMMISSION.REPORTING_FAILURE_HEAD,
                "state": "error_retained_no_replacement", "fresh_matrix_started": False,
                "sensor_verifier_implemented": False, "preflight": identity,
                "trials": [{"mode": "unrendered", "returncode": 1, "result": carrier}]},
            "unrendered/camera_result.json": carrier,
            "unrendered/camera_manifest.json": identity,
            "unrendered/native/retained/manifest.json": {"software": {
                "git_commit": COMMISSION.REPORTING_FAILURE_HEAD, "git_dirty": False}},
            "unrendered/native/retained/result.json": {"state": "finished", "episodes": [episode]},
        }
        if change:
            change(body)
        raw = {name: (value if isinstance(value, bytes) else json.dumps(value).encode()) for name, value in body.items()}
        raw["unrendered/native/retained/events.jsonl"] = b"".join(
            json.dumps({"event": "step", "step": step}).encode()+b"\n" for step in range(1, 801))
        raw["unrendered/robot_state.jsonl"] = b"".join(
            json.dumps({"step": step}).encode()+b"\n" for step in range(801))
        raw["unrendered/frames.jsonl"] = b""
        raw["unrendered/accepted_runner_replay.json"] = b""
        raw["unrendered/physics.jsonl"] = b"retained fixture physics bytes\n"
        raw["unrendered/controller_gate.jsonl"] = b"retained fixture controller bytes\n"
        for name in json.loads(COMMISSION.REVIEW.read_text())["frozen_sources_sha256"]:
            raw["source_snapshot/"+name] = (ROOT / name).read_bytes()
        raw["file_index.json"] = json.dumps({name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                                             for name, data in raw.items()}).encode()
        with tarfile.open(path, "w:gz") as archive:
            for name, data in raw.items():
                member = tarfile.TarInfo("m9-camera-commissioning/"+name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return identity, raw

    def repair_fixture(self, temporary, change=None, passed=True):
        from argparse import Namespace
        root = Path(temporary)
        source = root / "failure.tar.gz"
        identity, raw = self.failure_archive_fixture(source, change)
        output = root / "continuation"
        output.mkdir()
        args = Namespace(recover_reporting_archive=source, output=output, expected_head="corrected-head")
        report = {"preflight": identity, "trials": []}
        audit = {"passed": passed, "checks": {"sample": np.bool_(passed)},
                 "force_calls": 0, "external_physics_samples": 4000}
        # Fixture archives stand in for the immutable native archive. Its exact
        # production digest remains required outside this narrowly scoped patch.
        with patch.object(COMMISSION.inspection, "sha256", return_value=COMMISSION.REPORTING_FAILURE_ARCHIVE_SHA256), \
             patch("aether_cl.m6r_audit.check_trial", return_value=audit), \
             patch("aether_cl.m8_force_commission.audit_physics", return_value=audit), \
             patch("aether_cl.m8_matched.audit_gate", return_value=audit):
            COMMISSION.recover_reporting_failure(args, report)
        return args, report, raw

    def test_guarded_reporting_repair_preserves_native_bytes_and_does_not_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, report, raw = self.repair_fixture(temporary)
            for name in ("native/retained/events.jsonl", "physics.jsonl", "controller_gate.jsonl", "robot_state.jsonl"):
                self.assertEqual((args.output/"unrendered"/name).read_bytes(), raw["unrendered/"+name])
            self.assertEqual((args.output/"unrendered/camera_result_before_reporting_repair.json").read_bytes(), raw["unrendered/camera_result.json"])
            self.assertEqual((args.output/"unrendered/accepted_runner_replay.json").read_bytes(), b"")
            self.assertEqual((args.output/"preserved_reporting_failure_v1.tar.gz").read_bytes(), args.recover_reporting_archive.read_bytes())
            self.assertEqual(report["trials"][0]["state"], "finished")
            self.assertFalse(report["trials"][0]["native_motion_rerun"])
            repaired = json.loads((args.output/"unrendered/camera_result.json").read_text())
            self.assertEqual(repaired["external_physics_samples"], 4000)
            self.assertEqual(repaired["camera_frames"], 0)
            self.assertEqual(json.loads((args.output/"unrendered/accepted_runner_replay_revalidated.json").read_text())["checks"], {"sample": True})

    def test_reporting_repair_rejects_other_failures_and_started_camera_slots(self):
        changes = (
            lambda body: body["unrendered/camera_result.json"].update(error="ValueError: physical failure"),
            lambda body: body["commissioning.json"]["trials"].append({"mode": "render_idle"}),
            lambda body: body.update({"render_idle/camera_result.json": {}}),
            lambda body: body["unrendered/native/retained/result.json"].update(state="error"),
        )
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(ValueError):
                    self.repair_fixture(temporary, change)

    def test_failed_retained_audit_blocks_reporting_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "re-audit failed"):
                self.repair_fixture(temporary, passed=False)
            output = Path(temporary)/"continuation/unrendered"
            self.assertFalse((output/"camera_result.json").exists())
            self.assertFalse(json.loads((output/"accepted_runner_replay_revalidated.json").read_text())["checks"]["sample"])

    def test_reporting_repair_requires_exact_archive_and_has_no_native_execution_calls(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/"wrong.tar.gz"
            path.write_bytes(b"wrong archive")
            with self.assertRaisesRegex(ValueError, "pinned"):
                COMMISSION.recover_reporting_failure(Namespace(recover_reporting_archive=path), {})
        tree = ast.parse(Path(COMMISSION.__file__).read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "recover_reporting_failure")
        names = {n.id for n in ast.walk(function) if isinstance(n, ast.Name)}
        self.assertEqual(names & {"accepted_run", "build_env", "reset_native", "observe_native", "CameraPair", "child"}, set())
        attributes = {n.attr for n in ast.walk(function) if isinstance(n, ast.Attribute)}
        self.assertEqual(attributes & {"reset", "step", "Popen", "set_pose", "add_force_torque"}, set())

    def test_continuation_driver_starts_only_the_four_unstarted_modes(self):
        identity, commands, reports = {"fixture": "unchanged"}, [], []
        class FinishedChild:
            def __init__(self, command, **kwargs):
                commands.append(command)
                directory = Path(command[command.index("--output")+1])
                directory.mkdir()
                COMMISSION.write_json(directory/"camera_manifest.json", identity)
                COMMISSION.write_json(directory/"camera_result.json", {"state": "finished_valid_development_camera_evidence"})
                self.stdout, self.returncode = io.StringIO("fixture child finished\n"), 0
            def wait(self):
                return self.returncode
            def poll(self):
                return self.returncode
        identity["renderer_python_source_sha256"] = {}
        def repaired(args, report):
            report["trials"].append({"mode": "unrendered", "state": "finished", "native_motion_rerun": False})
        runs = COMMISSION.PROTOTYPE/"runs"
        runs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runs) as native, tempfile.TemporaryDirectory() as external:
            with patch.object(COMMISSION, "preflight", return_value=identity), \
                 patch.object(COMMISSION, "recover_reporting_failure", side_effect=repaired), \
                 patch.object(COMMISSION.subprocess, "Popen", FinishedChild), \
                 patch.object(COMMISSION, "compare_modes", return_value={"fixture": {"passed": True}}), \
                 patch.object(COMMISSION.inspection, "git", side_effect=lambda *args: "fixed-head" if args[0]=="rev-parse" else ""), \
                 patch.object(COMMISSION, "bundle", side_effect=lambda args, report: reports.append(report)):
                COMMISSION.main(["--expected-head", "fixed-head", "--inspection-archive", str(Path(external)/"inspection.tar.gz"),
                    "--recover-reporting-archive", str(Path(external)/"original-failure.tar.gz"),
                    "--output", str(Path(native)/"continuation"), "--archive", str(Path(external)/"new.tar.gz"),
                    "--replay-service-seconds", "0"])
        self.assertEqual([c[c.index("--mode")+1] for c in commands], list(COMMISSION.MODES[1:]))
        self.assertEqual([t["mode"] for t in reports[0]["trials"]], list(COMMISSION.MODES))
        self.assertEqual(reports[0]["retained_episodes"], 5)

    def test_continuation_guard_failure_starts_no_child(self):
        runs = COMMISSION.PROTOTYPE/"runs"
        runs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runs) as native, tempfile.TemporaryDirectory() as external:
            with patch.object(COMMISSION, "preflight", return_value={}), \
                 patch.object(COMMISSION, "recover_reporting_failure", side_effect=ValueError("wrong retained failure")), \
                 patch.object(COMMISSION.subprocess, "Popen") as spawn, patch.object(COMMISSION, "bundle"), self.assertRaises(SystemExit):
                COMMISSION.main(["--expected-head", "fixed-head", "--inspection-archive", str(Path(external)/"inspection.tar.gz"),
                    "--recover-reporting-archive", str(Path(external)/"wrong.tar.gz"),
                    "--output", str(Path(native)/"continuation"), "--archive", str(Path(external)/"new.tar.gz"),
                    "--replay-service-seconds", "0"])
            spawn.assert_not_called()

    def test_lossless_packet_preserves_depth_dtype_invalidity_and_all_pixels(self):
        sample = packet()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "frame.npz"
            CAMERA.save_packet(path, sample)
            with np.load(path, allow_pickle=False) as saved:
                restored = {key: saved[key] for key in saved.files}
            self.assertEqual(CAMERA.packet_hashes(restored), CAMERA.packet_hashes(sample))
            self.assertEqual(restored["primary_depth_mm"].dtype, np.int16)
            self.assertEqual(restored["primary_depth_mm"][0, 0], 0)
            with self.assertRaises(FileExistsError):
                CAMERA.save_packet(path, sample)

    def test_truth_segmentation_and_condition_fields_cannot_enter_camera_packet(self):
        for forbidden in ("segmentation", "obj_pose", "contact", "is_grasped", "success", "seed", "condition", "recovery_completion"):
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(ValueError, "allowlisted"):
                CAMERA.validate_packet({**packet(), forbidden: True})

    def test_mask_cannot_encode_segmentation_and_depth_cannot_be_float_or_saturated(self):
        for kind in ("mask", "float_depth", "far", "negative"):
            sample = packet()
            if kind == "mask":
                sample["primary_validity"][2, 2] = 5
            elif kind == "float_depth":
                sample["primary_depth_mm"] = sample["primary_depth_mm"].astype(np.float32)
            elif kind == "far":
                sample["primary_depth_mm"][2, 2] = 3001
            else:
                sample["primary_depth_mm"][2, 2] = -1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                CAMERA.validate_packet(sample)

    def test_native_depth_fetch_disables_position_segmentation_normal_and_albedo(self):
        tree = ast.parse(Path(CAMERA.__file__).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get_obs"]
        self.assertEqual(len(calls), 2)
        for call in calls:
            flags = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
            self.assertTrue(flags["rgb"])
            for key in ("position", "segmentation", "normal", "albedo"):
                self.assertFalse(flags[key])
        self.assertTrue(calls[0].keywords[1].value.value)

    def test_camera_adapter_has_no_task_truth_policy_or_state_mutation_interface(self):
        tree = ast.parse(Path(CAMERA.__file__).read_text())
        attributes = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        forbidden = {"cube", "goal_site", "evaluate", "is_grasping", "linear_velocity", "angular_velocity",
            "set_pose", "set_velocity", "add_force_torque", "apply_impulse", "step", "set_state"}
        self.assertEqual(attributes & forbidden, set())
        self.assertNotIn("PlacementVerifier", Path(CAMERA.__file__).read_text())

    def test_review_pins_accepted_sources_and_never_allocates_fresh_banks(self):
        self.assertEqual(COMMISSION.inspection.sha256(COMMISSION.REVIEW), COMMISSION.REVIEW_SHA256)
        review = json.loads(COMMISSION.REVIEW.read_text())
        self.assertFalse(review["next_scope"]["fresh_evaluation_started"])
        self.assertFalse(review["next_scope"]["calibration_allocation_frozen"])
        self.assertEqual(review["next_scope"]["seed"], 100)
        self.assertEqual(review["next_scope"]["modes"], list(COMMISSION.MODES))
        for name, digest in review["frozen_sources_sha256"].items():
            self.assertEqual(COMMISSION.inspection.sha256(ROOT / name), digest)

    def test_cli_has_no_fresh_seed_recovery_force_or_success_threshold_options(self):
        tree = ast.parse(Path(COMMISSION.__file__).read_text())
        options = [ast.literal_eval(n.args[0]) for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument"]
        for forbidden in ("--seed", "--system", "--force", "--threshold", "--resume", "--replace"):
            self.assertNotIn(forbidden, options)
        self.assertEqual(COMMISSION.SEED, 100)
        self.assertEqual(COMMISSION.ACTIONS, 800)

    def test_output_stays_in_retained_history_and_archive_cannot_overwrite_inspection(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            args = Namespace(output=path/"elsewhere", archive=path/"new.tar.gz", inspection_archive=path/"inspection.tar.gz")
            with self.assertRaisesRegex(ValueError, "history"):
                COMMISSION.require_paths(args)
            args.output = COMMISSION.PROTOTYPE / "runs/m9-test-not-created"
            args.archive = args.inspection_archive
            with self.assertRaisesRegex(ValueError, "new archive"):
                COMMISSION.require_paths(args)

    def test_web_client_reads_cached_bytes_and_start_is_only_a_pre_action_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            viewer = CAMERA.LiveView(Path(temporary), port=0)
            base = f"http://127.0.0.1:{viewer.port}"
            try:
                self.assertEqual(viewer.server.server_address[0], "127.0.0.1")
                with self.assertRaises(HTTPError):
                    urlopen(Request(base+"/start", method="POST"))
                sample = packet()
                image = CAMERA.display_frame(sample, 0, "record_with_view")
                viewer.publish(image, "waiting_for_start", 0)
                with urlopen(base+"/frame.jpg") as response:
                    self.assertTrue(response.read().startswith(b"\xff\xd8"))
                with urlopen(Request(base+"/start", method="POST")) as response:
                    self.assertEqual(response.status, 200)
                self.assertTrue(viewer.start.is_set())
                viewer.publish(image, "running", 1)
                with self.assertRaises(HTTPError):
                    urlopen(Request(base+"/start", method="POST"))
                with self.assertRaises(HTTPError):
                    urlopen(base+"/../../etc/passwd")
                viewer.complete("finished")
                with urlopen(base+"/status") as response:
                    status = json.load(response)
                self.assertEqual(status["state"], "finished")
                self.assertEqual(status["step"], 1)
            finally:
                viewer.close()

    def test_source_pins_use_python310_compatible_syntax(self):
        for path in (Path(CAMERA.__file__), Path(COMMISSION.__file__)):
            ast.parse(path.read_text(), feature_version=(3, 10))

    def fixture_cases(self, root):
        from aether_cl.m6r_audit import PHYSICAL_FIELDS
        events = [{"event": "reset", "observation": {}, "info": {}}]
        events += [{"event": "step", **{key: 0 for key in (*PHYSICAL_FIELDS, "verification", "recovery")}, "step": step}
                   for step in range(1, 801)]
        physics = [{"event": "physics_action", "step": step, "substeps": [{"substep": i, "z": 0.0} for i in range(1, 6)]}
                   for step in range(1, 801)]
        for mode in COMMISSION.MODES:
            directory = root / mode
            directory.mkdir()
            (directory / "camera_result.json").write_text(json.dumps({"run_relative": "native"}))
            (directory / "physics.jsonl").write_text("".join(json.dumps(r)+"\n" for r in physics))
            (directory / "robot_state.jsonl").write_text("".join(json.dumps({"step": step})+"\n" for step in range(801)))
        return events

    def test_exact_neutrality_rejects_a_tiny_physics_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events = self.fixture_cases(root)
            with patch("aether_cl.acceptance.load_trial", return_value=({}, {}, events)):
                self.assertTrue(all(r["passed"] for r in COMMISSION.compare_modes(root).values()))
                target = root / "record_with_view/physics.jsonl"
                rows = COMMISSION.read_lines(target)
                rows[-1]["substeps"][-1]["z"] = 1e-12
                target.write_text("".join(json.dumps(r)+"\n" for r in rows))
                result = COMMISSION.compare_modes(root)
                self.assertFalse(result["record_with_view"]["passed"])
                self.assertFalse(result["record_with_view"]["checks"]["exact_all_100Hz_physics_samples_and_contacts"])

    def test_equal_but_missing_physics_samples_cannot_pass_neutrality(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events = self.fixture_cases(root)
            for mode in COMMISSION.MODES:
                (root / mode / "physics.jsonl").write_text("")
            with patch("aether_cl.acceptance.load_trial", return_value=({}, {}, events)):
                self.assertTrue(all(not r["passed"] for r in COMMISSION.compare_modes(root).values()))

    def test_failed_preflight_is_archived_with_index_and_without_native_execution(self):
        runs = COMMISSION.PROTOTYPE / "runs"
        runs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runs) as run_container, tempfile.TemporaryDirectory() as external:
            output = Path(run_container) / "failed"
            archive = Path(external) / "retained.tar.gz"
            with patch.object(COMMISSION, "preflight", side_effect=ValueError("forced missing installed API")), self.assertRaises(SystemExit):
                COMMISSION.main(["--expected-head", "fixture", "--inspection-archive", str(Path(external)/"absent.tar.gz"),
                                 "--output", str(output), "--archive", str(archive), "--replay-service-seconds", "0"])
            self.assertTrue(archive.is_file())
            with tarfile.open(archive) as tar:
                report = json.load(tar.extractfile("m9-camera-commissioning/commissioning.json"))
                self.assertEqual(report["state"], "error_retained_no_replacement")
                self.assertFalse(report["fresh_matrix_started"])
                self.assertEqual(report["trials"], [])
                index = json.load(tar.extractfile("m9-camera-commissioning/file_index.json"))
                for name, record in index.items():
                    raw = tar.extractfile("m9-camera-commissioning/"+name).read()
                    self.assertEqual(len(raw), record["bytes"])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])


if __name__ == "__main__":
    unittest.main()
