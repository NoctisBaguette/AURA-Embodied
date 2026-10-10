"""Preview pause, release, and cleanup without native graphics."""

from pathlib import Path
import tempfile
import threading
import unittest

import numpy as np

from aether_cl.m3 import PreviewSnapshot
from aether_cl.m3_runtime import M3Config, run
from test_m2 import inject
from test_recovery import RetryEnvironment


class PreviewTests(unittest.TestCase):
    def test_preview_is_visible_and_publisher_waits_until_explicit_release(self):
        snapshot = PreviewSnapshot(threading.Event())
        finished = threading.Event()
        def publish():
            snapshot.publish({"state": "running", "step": 0}, b"first-frame")
            finished.set()
        thread = threading.Thread(target=publish)
        thread.start()
        try:
            self.assertTrue(snapshot.ready.wait(2))
            status, jpeg = snapshot.read()
            self.assertEqual(status["state"], "ready_to_start")
            self.assertEqual(status["step"], 0)
            self.assertEqual(jpeg, b"first-frame")
            self.assertFalse(finished.is_set())
            snapshot.release.set()
            self.assertTrue(finished.wait(2))
            snapshot.publish({"state": "running", "step": 1}, b"second-frame")
            self.assertEqual(snapshot.read()[0]["frame_number"], 2)
        finally:
            snapshot.release.set()
            thread.join(timeout=2)

    def test_cancel_before_enter_executes_no_actions_and_closes_environment(self):
        class RenderedFixture(RetryEnvironment):
            def render(self):
                frame = np.zeros((10, 10, 3), dtype=np.uint8)
                frame[:5, :, 0] = 100
                return frame
        stop = threading.Event()
        snapshot = PreviewSnapshot(stop)
        env = RenderedFixture()
        results = []
        with tempfile.TemporaryDirectory() as temporary:
            def worker():
                results.append(run(M3Config(render=True, output=Path(temporary)),
                                   publish=snapshot.publish, stop=stop,
                                   env_factory=lambda _: env, disturbance_fn=inject))
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(snapshot.ready.wait(3))
                self.assertEqual(env.step_number, 0)
                self.assertEqual(snapshot.read()[0]["state"], "ready_to_start")
                stop.set()
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                self.assertTrue(env.closed)
                self.assertEqual(env.step_number, 0)
                self.assertEqual(results[0]["state"], "stopped")
            finally:
                stop.set()
                snapshot.release.set()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
