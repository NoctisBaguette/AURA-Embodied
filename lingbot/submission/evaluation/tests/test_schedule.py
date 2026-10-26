import unittest
from pathlib import Path

from support import CHECKPOINT_SHA, TEMPLATE_PATH
from evaluate import build_plan, load_tasks


class ScheduleTests(unittest.TestCase):
    def test_all_settings_plan_has_100_cells_and_fixed_candidate_budget(self):
        tasks = load_tasks(TEMPLATE_PATH)
        plan = build_plan(
            tasks=tasks,
            setting="all",
            episodes=100,
            max_candidates=1000,
            seed_start=100000,
            manifest_sha256=CHECKPOINT_SHA,
            stage="baseline",
            output_dir=Path("out"),
        )
        self.assertEqual(100, len(plan["cells"]))
        by_key = {(cell["setting"], cell["task"]): cell for cell in plan["cells"]}
        self.assertEqual(100, len(by_key))
        clean = by_key[("clean", "lift_pot")]
        randomized = by_key[("randomized", "lift_pot")]
        self.assertEqual("seen", clean["instruction_type"])
        self.assertEqual("unseen", randomized["instruction_type"])
        self.assertEqual(100, clean["target_episodes"])
        self.assertEqual(1000, clean["candidate_budget"])
        self.assertEqual([100000, 100001, 100999], [
            clean["candidates"][i]["scene_seed"] for i in (0, 1, 999)
        ])
        ids = [item["episode_id"] for cell in plan["cells"] for item in cell["candidates"]]
        self.assertEqual(100000, len(set(ids)))
        request_prefixes = [item["request_id_prefix"] for cell in plan["cells"] for item in cell["candidates"]]
        self.assertEqual(100000, len(set(request_prefixes)))
        self.assertTrue(all(item["output_dir"] for cell in plan["cells"] for item in cell["candidates"]))

    def test_candidate_budget_below_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "candidate budget"):
            build_plan(
                tasks=["lift_pot"], setting="clean", episodes=100,
                max_candidates=64, seed_start=100000,
                manifest_sha256=CHECKPOINT_SHA, stage="baseline",
                output_dir=Path("out"),
            )

    def test_single_task_selector_builds_only_an_official_cell(self):
        tasks = load_tasks(TEMPLATE_PATH)
        plan = build_plan(
            tasks=tasks,
            selected_tasks=["lift_pot"],
            setting="clean",
            episodes=1,
            max_candidates=1,
            seed_start=100000,
            manifest_sha256=CHECKPOINT_SHA,
            stage="baseline",
            output_dir=Path("out"),
        )
        self.assertEqual(["lift_pot"], [cell["task"] for cell in plan["cells"]])
        with self.assertRaisesRegex(ValueError, "official task"):
            build_plan(
                tasks=tasks,
                selected_tasks=["made_up_task"],
                setting="clean",
                episodes=1,
                max_candidates=1,
                seed_start=100000,
                manifest_sha256=CHECKPOINT_SHA,
                stage="baseline",
                output_dir=Path("out"),
            )


if __name__ == "__main__":
    unittest.main()
