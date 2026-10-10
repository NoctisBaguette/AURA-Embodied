"""Observation access, temporal evidence, failure checks, and reference counts."""

import copy
import unittest

import numpy as np

from aether_cl.verification import StateVerifier, TaskReference, VerificationMetrics, initial_task


def state(cube=(0, 0, 0.02), tcp=None, goal=(0.08, 0, 0.2), aperture=0.0366, velocity=0):
    tcp = cube if tcp is None else tcp
    return {"agent": {"qpos": np.array([[0.] * 7 + [aperture / 2] * 2]),
                      "qvel": np.array([[velocity] * 7 + [0.] * 2])},
            "extra": {"obj_pose": np.array([[*cube, 1., 0, 0, 0]]),
                      "tcp_pose": np.array([[*tcp, 1., 0, 0, 0]]),
                      "goal_pos": np.array([goal]),
                      # Deliberately contradictory data must not enter the verifier.
                      "is_grasped": np.array([True]), "success": True}}


def attached(verifier):
    for step in (128, 129, 130):
        verifier.observe(state(cube=(0, 0, 0.1)), step)


class VerifierTests(unittest.TestCase):
    def test_reset_contact_and_extra_success_flags_do_not_establish_grasp(self):
        verifier = StateVerifier(state())
        self.assertFalse(verifier.ever_attached)
        result = verifier.observe(state(tcp=(0.15, 0, 0.15), aperture=0), 1)
        self.assertEqual(result["status"], "pending")
        self.assertFalse(verifier.ever_attached)
        self.assertNotIn("is_grasped", verifier.manifest()["inputs"])

    def test_missing_nonfinite_and_repeated_frames_are_uncertain(self):
        verifier = StateVerifier(state())
        invalid = state()
        invalid["agent"]["qpos"][0, 0] = np.nan
        self.assertEqual(verifier.observe(invalid, 1)["failure"], "UNCERTAIN")
        self.assertEqual(verifier.observe(state(), 1)["reason"], "stale_or_repeated_step")
        missing = state()
        del missing["agent"]["qvel"]
        self.assertEqual(verifier.observe(missing, 2)["failure"], "UNCERTAIN")
        self.assertEqual(verifier.observe(state(), 3)["status"], "pending")

    def test_grasp_failure_waits_for_deadline_and_persistence(self):
        verifier = StateVerifier(state())
        missed = state(tcp=(0.15, 0, 0.02), aperture=0)
        self.assertIsNone(verifier.observe(missed, 124)["failure"])
        self.assertIsNone(verifier.observe(missed, 125)["failure"])
        self.assertIsNone(verifier.observe(missed, 126)["failure"])
        self.assertEqual(verifier.observe(missed, 127)["failure"], "GRASP_FAILURE")
        self.assertEqual(verifier.first_failure, {"step": 127, "failure": "GRASP_FAILURE"})

    def test_drop_after_attachment_is_object_lost(self):
        verifier = StateVerifier(state())
        attached(verifier)
        self.assertTrue(verifier.ever_attached)
        dropped = state(cube=(0, .12, .02), tcp=(0, 0, .14), aperture=0)
        for step in (181, 182):
            self.assertIsNone(verifier.observe(dropped, step)["failure"])
        self.assertEqual(verifier.observe(dropped, 183)["failure"], "OBJECT_LOST")

    def test_changed_goal_and_failed_lift_are_state_mismatch(self):
        for altered in (state(goal=(.2, 0, .2)), state()):
            with self.subTest(goal=altered["extra"]["goal_pos"].tolist()):
                verifier = StateVerifier(state())
                for step in (170, 171, 172):
                    result = verifier.observe(altered, step)
                self.assertEqual(result["failure"], "STATE_MISMATCH")

    def test_goal_requires_lift_and_five_consecutive_static_frames(self):
        verifier = StateVerifier(state())
        attached(verifier)
        at_goal = state(cube=(.08, 0, .2))
        for step in range(320, 324):
            self.assertFalse(verifier.observe(at_goal, step)["success"])
        self.assertTrue(verifier.observe(at_goal, 324)["success"])
        self.assertFalse(verifier.observe(state(cube=(.08, 0, .2), velocity=.3), 325)["success"])
        # A skipped step cannot count as consecutive stability evidence.
        self.assertFalse(verifier.observe(at_goal, 327)["success"])

    def test_target_deadline_and_final_moving_state_are_distinct_failures(self):
        verifier = StateVerifier(state())
        attached(verifier)
        for step in (320, 321, 322):
            result = verifier.observe(state(cube=(0, 0, .14)), step)
        self.assertEqual(result["failure"], "TARGET_NOT_REACHED")
        moving = verifier.observe(state(cube=(.08, 0, .2), velocity=.3), 360, final=True)
        self.assertEqual(moving["failure"], "STATE_MISMATCH")
        self.assertIsNone(moving["confidence"])

    def test_eligibility_uses_geometry_and_preserves_boundary(self):
        self.assertFalse(initial_task(state(goal=(.025, 0, .02)))[2]["eligible"])
        self.assertTrue(initial_task(state(goal=(.026, 0, .02)))[2]["eligible"])
        self.assertEqual(initial_task(state(goal=(0, 0, .02)))[2]["exclusion_reason"], "initially_at_goal")

    def test_verifier_does_not_mutate_observation_storage(self):
        observation = state()
        original = copy.deepcopy(observation)
        verifier = StateVerifier(observation)
        verifier.observe(observation, 1)
        for group in observation:
            for key in observation[group]:
                np.testing.assert_array_equal(observation[group][key], original[group][key])


class ReferenceAndMetricsTests(unittest.TestCase):
    def test_reference_requires_fresh_contact_even_when_geometry_looks_attached(self):
        reference = TaskReference(state())
        for step in range(320, 326):
            result = reference.observe(state(cube=(.08, 0, .2)),
                                       {"is_grasped": [False], "is_robot_static": [True]}, step)
        self.assertFalse(result["task_success"])
        self.assertEqual(result["failure"], "GRASP_FAILURE")
        with self.assertRaisesRegex(ValueError, "increasing"):
            reference.observe(state(), {"is_grasped": [True], "is_robot_static": [True]}, 325)

    def test_metrics_keep_uncertainty_and_missing_denominators_explicit(self):
        metrics = VerificationMetrics()
        self.assertIsNone(metrics.result(True)["failure_detection_precision"])
        for truth, prediction in [(None, None), ("GRASP_FAILURE", None),
                                  ("GRASP_FAILURE", "GRASP_FAILURE"),
                                  (None, "OBJECT_LOST"), (None, "UNCERTAIN"),
                                  ("OBJECT_LOST", "UNCERTAIN")]:
            metrics.observe({"failure": truth}, {"failure": prediction})
        result = metrics.result(True)
        self.assertEqual(result["true_positive"], 1)
        self.assertEqual(result["false_positive"], 1)
        self.assertEqual(result["false_negative"], 2)
        self.assertEqual(result["true_negative"], 1)
        self.assertEqual(result["uncertain_on_negative"], 1)
        self.assertEqual(result["observation_coverage"], 4 / 6)
        self.assertIsNone(metrics.result(False)["failure_detection_recall"])


if __name__ == "__main__":
    unittest.main()
