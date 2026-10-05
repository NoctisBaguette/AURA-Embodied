"""Archive and candidate acceptance boundaries, without native contacts."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from aether_cl.acceptance import run_in_process
from aether_cl.m3_acceptance import check_v2, run_acceptance
from aether_cl.m3_runtime import M3Config, run
from aether_cl.runtime import software_manifest
from test_m2 import inject
from test_recovery import RetryEnvironment


class M3AcceptanceTests(unittest.TestCase):
    def runner(self, config):
        return run(config, env_factory=lambda _: RetryEnvironment(), disturbance_fn=inject)

    def test_nine_cell_evidence_and_four_pairs_pass_and_archive_matches(self):
        software = {**software_manifest(), "git_commit": "fixture", "git_dirty": False}
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.m3_runtime.software_manifest", return_value=software):
            archive = Path(temporary) / "evidence.tar.gz"
            report = run_acceptance(Path(temporary) / "runs", archive, run_fn=self.runner)
            self.assertEqual(report["state"], "passed")
            self.assertEqual(len(report["trials"]), 9)
            self.assertEqual(len(report["pairs"]), 4)
            with tarfile.open(archive) as bundle:
                archived = json.load(bundle.extractfile("m3-acceptance/suite.json"))
                self.assertEqual(archived["state"], "passed")
                index = json.load(bundle.extractfile("m3-acceptance/archive_index.json"))
                self.assertEqual(set(bundle.getnames()), {e["path"] for e in index["files"]} | {"m3-acceptance/archive_index.json"})
            trial = next(t for t in report["trials"] if t["condition"] == "object_shift" and t["system"] == "v2")
            passive = next(t for t in report["trials"] if t["condition"] == "object_shift" and t["system"] == "v1")
            result_path = Path(trial["run_directory"]) / "result.json"
            result = json.loads(result_path.read_text())
            result["episodes"][0]["recovery"]["action_steps"] = 231
            result_path.write_text(json.dumps(result))
            check = check_v2(Path(trial["run_directory"]), Path(passive["run_directory"]),
                             M3Config(output=Path(trial["config"]["output"]), disturbance="object_shift", render=False, render_device="cuda:0"))
            self.assertFalse(check["passed"])
            self.assertIn("bounded_attempt", check["failed_checks"])

    def test_trial_error_is_preserved_in_failed_archive(self):
        def fail(config):
            raise RuntimeError("native failure fixture")
        with tempfile.TemporaryDirectory() as temporary:
            report = run_acceptance(Path(temporary) / "runs", Path(temporary) / "failed.tar.gz", run_fn=fail)
            self.assertEqual(report["state"], "failed")
            self.assertTrue(all(t["state"] == "error" for t in report["trials"]))
            self.assertTrue(Path(report["archive"]).is_file())

    def test_m3_subprocess_uses_v2_cli_and_captured_environment(self):
        real_popen = subprocess.Popen
        commands = []
        program = "from pathlib import Path; import sys,json,os; p=Path(sys.argv[1])/'child'; p.mkdir(); (p/'result.json').write_text(json.dumps({'state':'finished','environment':os.environ['M3_TEST_ENV']}))"
        def launch(command, **kwargs):
            commands.append(command)
            return real_popen([sys.executable, "-c", program, command[command.index("--output") + 1]], **kwargs)
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.acceptance.subprocess.Popen", side_effect=launch):
            result = run_in_process(M3Config(render=False, output=Path(temporary) / "trial"),
                                    {**os.environ, "M3_TEST_ENV": "captured"}, module="aether_cl.m3")
        self.assertEqual(commands[0][2], "aether_cl.m3")
        self.assertEqual(commands[0][commands[0].index("--system") + 1], "v2")
        self.assertEqual(result["environment"], "captured")

    def test_actual_child_parser_round_trips_every_parent_config_field(self):
        from dataclasses import asdict
        from aether_cl.runtime import json_value
        program = """
from dataclasses import asdict
import json, sys
from aether_cl.m3 import parser, config_from_args
from aether_cl.runtime import json_value
config = config_from_args(parser().parse_args(sys.argv[1:]))
config.validate()
p = config.output / 'parsed-child'
p.mkdir()
(p / 'result.json').write_text(json.dumps(json_value(asdict(config))))
"""
        real_popen = subprocess.Popen
        def launch(command, **kwargs):
            return real_popen([sys.executable, "-c", program, *command[3:]], **kwargs)
        with tempfile.TemporaryDirectory() as temporary, patch("aether_cl.acceptance.subprocess.Popen", side_effect=launch):
            for fps in (5.0, 7.25):
                config = M3Config(render=False, fps=fps, seed=4, episodes=2,
                                  disturbance="object_drop", output=Path(temporary) / str(fps))
                actual = run_in_process(config, os.environ.copy(), module="aether_cl.m3")
                self.assertEqual(actual, json_value(asdict(config)))


if __name__ == "__main__":
    unittest.main()
