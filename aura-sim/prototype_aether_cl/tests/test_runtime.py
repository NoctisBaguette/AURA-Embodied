"""Check experiment records, failure cleanup, and the viewer without a GPU."""

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np

from aether_cl.runtime import RunConfig, encode_frame, run
from aether_cl.viewer import Snapshot, make_server


class Actions:
    def seed(self, seed):
        self.rng = np.random.default_rng(seed)

    def sample(self):
        return self.rng.uniform(-1, 1, size=(1, 2))


class Environment:
    def __init__(self, fail=False, fail_close=False):
        self.action_space = Actions()
        self.unwrapped = self
        self.closed = False
        self.fail = fail
        self.fail_close = fail_close

    def reset(self, seed):
        self.step_number = 0
        return {"seed": seed}, {"success": [False]}

    def step(self, action):
        if self.fail:
            raise RuntimeError("execution failed")
        action[:] = 99  # Simulate a backend reusing/mutating action storage.
        self.step_number += 1
        return {"step": self.step_number}, [0], [False], [self.step_number == 2], {"success": [False]}

    def close(self):
        self.closed = True
        if self.fail_close:
            raise RuntimeError("cleanup failed")


class RuntimeTests(unittest.TestCase):
    def test_records_seeds_actions_and_episode_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment()
            config = RunConfig(render=False, output=Path(temporary), episodes=2, seed=4)
            result = run(config, env_factory=lambda _: env)
            events = [json.loads(line) for line in
                      (Path(result["run_directory"]) / "events.jsonl").read_text().splitlines()]
            self.assertEqual(result["state"], "finished")
            self.assertEqual([e["seed"] for e in result["episodes"]], [4, 5])
            self.assertTrue(all(e["truncated"] for e in result["episodes"]))
            self.assertTrue(all(e["steps"] == 2 for e in result["episodes"]))
            self.assertTrue(env.closed)
            actions = [e["action"] for e in events if e["event"] == "step"]
            self.assertTrue(all(abs(number) <= 1 for action in actions for row in action for number in row))

    def test_failed_execution_closes_environment_and_records_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment(fail=True)
            with self.assertRaisesRegex(RuntimeError, "execution failed"):
                run(RunConfig(render=False, output=Path(temporary)), env_factory=lambda _: env)
            directory = next(Path(temporary).iterdir())
            result = json.loads((directory / "result.json").read_text())
            self.assertEqual(result["state"], "error")
            self.assertIn("execution failed", result["error"])
            self.assertTrue(env.closed)

    def test_stop_is_distinct_from_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            stop = threading.Event()
            stop.set()
            result = run(RunConfig(render=False, output=Path(temporary)), stop=stop,
                         env_factory=lambda _: Environment())
            self.assertEqual(result["state"], "stopped")
            self.assertEqual(result["episodes"], [])

    def test_cleanup_failure_cannot_be_reported_as_a_finished_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Environment(fail_close=True)
            with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
                run(RunConfig(render=False, output=Path(temporary)), env_factory=lambda _: env)
            directory = next(Path(temporary).iterdir())
            result = json.loads((directory / "result.json").read_text())
            self.assertEqual(result["state"], "error")
            self.assertIn("cleanup failed", result["error"])

    def test_invalid_config_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "missing"
            with self.assertRaises(ValueError):
                run(RunConfig(episodes=0, output=output))
            self.assertFalse(output.exists())

    def test_empty_or_wrong_frames_fail(self):
        with self.assertRaises(RuntimeError):
            encode_frame(np.zeros((1, 4, 4, 3), dtype=np.uint8))
        with self.assertRaises(RuntimeError):
            encode_frame(np.ones((1, 4, 4, 3), dtype=np.float32))

    def test_render_encoding(self):
        frame = np.zeros((1, 4, 4, 3), dtype=np.uint8)
        frame[:, :2, :, 0] = 255
        self.assertTrue(encode_frame(frame).startswith(b"\xff\xd8"))

    def test_http_viewer_serves_only_status_frame_and_page(self):
        snapshot = Snapshot()
        snapshot.publish({"state": "running", "step": 2}, b"jpeg-test-payload")
        server = make_server(0, snapshot)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/status") as response:
                status = json.load(response)
            self.assertEqual(status["frame_number"], 1)
            self.assertEqual(status["step"], 2)
            with urlopen(base + "/frame.jpg?v=1") as response:
                self.assertEqual(response.read(), b"jpeg-test-payload")
            with urlopen(base + "/") as response:
                self.assertIn(b"Seeded random actions", response.read())
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/../requirements.txt")
            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
