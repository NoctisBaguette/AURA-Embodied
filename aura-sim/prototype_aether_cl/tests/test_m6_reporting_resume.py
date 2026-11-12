"""Report-only serialization failure recovery without a scientific rerun."""

from contextlib import ExitStack, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl import m6_sweep as sweep
from test_m6 import SOFTWARE, fixture_run


spec = importlib.util.spec_from_file_location("m6_reporting_resume", Path(__file__).resolve().parents[3] / "tools/m6_reporting_resume.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class ReportingRepairTests(unittest.TestCase):
    def setup_case(self, stack, output, archive):
        stack.enter_context(patch.object(sweep, "software_manifest", return_value=SOFTWARE))
        stack.enter_context(patch("aether_cl.m6_runtime.software_manifest", return_value=SOFTWARE))
        stack.enter_context(redirect_stdout(io.StringIO()))
        original = sweep.checked_trial
        def numpy_check(trial, software):
            checked = original(trial, software)
            checked["checks"]["forced_numpy_bool_transport"] = np.bool_(True)
            return checked
        stack.enter_context(patch.object(sweep, "checked_trial", side_effect=numpy_check))
        self.calls = []
        def child(config):
            self.calls.append((config.seed, config.system, config.disturbance, config.disturbance_magnitude))
            return fixture_run(config)
        self.child = child
        with self.assertRaisesRegex(TypeError, "not JSON serializable"):
            sweep.run_sweep(output, archive, stop_after=18, run_fn=child)
        report = json.loads((output / "suite.json").read_text())
        self.assertEqual(report["episode_trials"][0]["state"], "running")
        self.assertEqual(len(self.calls), 1)

    def test_reproduced_bool_crash_retains_raw_first_slot_and_completes_first18_without_rerun(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp); output, archive, backup = root / "study", root / "final.tar.gz", root / "before.tar.gz"
            self.setup_case(stack, output, archive)
            raw_before = sweep.files(Path(sweep.plan(output)[0]["config"]["output"]), output)
            original_suite = (output / "suite.json").read_bytes()
            recovered = repair.repair_initial(sweep, output, archive, backup, SOFTWARE)
            self.assertTrue(recovered["episode_trials"][0]["passed"])
            self.assertIs(type(recovered["episode_trials"][0]["checks"]["forced_numpy_bool_transport"]), bool)
            self.assertEqual(sweep.files(Path(sweep.plan(output)[0]["config"]["output"]), output), raw_before)
            with tarfile.open(backup) as bundle:
                self.assertEqual(bundle.extractfile("m6-before-report-repair/suite.json").read(), original_suite)
                for entry in recovered["reporting_repair"]["backup_files"]:
                    data = bundle.extractfile("m6-before-report-repair/" + entry["path"]).read()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
            before_digest = repair.digest(backup)
            with repair.reporting_encoder(sweep):
                final = sweep.run_sweep(output, archive, resume=True, stop_after=17, run_fn=self.child)
            self.assertEqual(final["state"], "paused")
            self.assertEqual(len(self.calls), 18)
            self.assertEqual(len(set(self.calls)), 18)
            self.assertTrue(sweep.check_pilot(final)["passed"])
            self.assertEqual(repair.digest(backup), before_digest)
            self.assertEqual(final["reporting_repair"], recovered["reporting_repair"])
            with self.assertRaises(ValueError):
                repair.repair_initial(sweep, output, archive, root / "second.tar.gz", SOFTWARE)

    def test_incomplete_child_and_identity_drift_fail_without_mutating_report(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp); output, archive, backup = root / "study", root / "final.tar.gz", root / "before.tar.gz"
            self.setup_case(stack, output, archive)
            original_suite = (output / "suite.json").read_bytes()
            with self.assertRaises(ValueError):
                repair.repair_initial(sweep, output, archive, backup, {**SOFTWARE, "git_commit": "different"})
            result = next(output.glob("normal/seed-100/baseline/*/result.json"))
            original_result = result.read_text()
            data = json.loads(original_result); data["state"] = "stopped"; result.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "not complete"):
                repair.repair_initial(sweep, output, archive, backup, SOFTWARE)
            data = json.loads(original_result); data["episodes"][0]["steps"] -= 1; result.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "replay failed"):
                repair.repair_initial(sweep, output, archive, backup, SOFTWARE)
            self.assertEqual((output / "suite.json").read_bytes(), original_suite)
            self.assertFalse(backup.exists())
            self.assertEqual(len(self.calls), 1)

    def test_encoder_preserves_false_true_values_and_nan_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            original = sweep.write_json
            with repair.reporting_encoder(sweep):
                sweep.write_json(path, {"checks": [np.bool_(False), np.bool_(True)], "value": np.float64(1.25)})
                self.assertEqual(json.loads(path.read_text()), {"checks": [False, True], "value": 1.25})
                with self.assertRaises(ValueError):
                    sweep.write_json(path, {"invalid": np.float64(float("nan"))})
            self.assertIs(sweep.write_json, original)


if __name__ == "__main__":
    unittest.main()
