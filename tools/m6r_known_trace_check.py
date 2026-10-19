"""Development-only M6R prefix checks on already observed frozen M6 traces.

Replays V2-old completely and V2R only while it shares the recorded physical
trajectory. Stops at the first differing lower-phase state transition; never
uses old post-divergence physics to claim a V2R rollout or recovery success.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aura-sim/prototype_aether_cl"))
from aether_cl.acceptance import load_trial
from aether_cl.m6_policy import FixedPlacement, PlacementRecovery
from aether_cl.m6r_policy import EffectAlignedRecovery
from aether_cl.m6r_audit import lower_predicates
from aether_cl.m6r_sweep import preflight
from aether_cl.runtime import json_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m6-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight()
    suite = json.loads((args.m6_root / "suite.json").read_text())
    assert suite["software"]["git_commit"] == "7059c713d3b36e3f032aab8d1f87662ed6fdab91"
    rows = []
    for trial in suite["episode_trials"]:
        if trial["system"] != "v2": continue
        assert 100 <= trial["seed"] <= 119
        directory = args.m6_root / Path(trial["run_directory"]).relative_to(suite["run_directory"])
        manifest, result, events = load_trial(directory)
        reset = next(e for e in events if e["event"] == "reset")
        obs = reset["observation"]
        policy = FixedPlacement(obs, manifest["robot_base_pose"])
        old = PlacementRecovery(policy, manifest["robot_base_pose"])
        repaired = EffectAlignedRecovery(policy, manifest["robot_base_pose"])
        verdict = {"status": "waiting", "failure": None}
        divergence = predicates = attempt_obs = None
        common_steps = 0
        steps = [e for e in events if e["event"] == "step"]
        for event in steps:
            if old.state == "nominal" and verdict.get("status") == "failed": attempt_obs = obs
            action, decision = old.action(obs, event["step"], verdict)
            expected = action[0] if manifest["action_space_shape"] == [7] else action
            assert np.array_equal(expected, np.asarray(event["action"], dtype=expected.dtype))
            assert decision == event["controller_decision"]
            if divergence is None:
                ra, rd = repaired.action(obs, event["step"], verdict)
                assert np.array_equal(ra, action) and rd == decision
            obs = event["observation"]
            old.observe(obs)
            assert json_value(old.snapshot()) == event["recovery"]
            if divergence is None:
                repaired.observe(obs)
                common_steps += 1
                if json_value(old.snapshot()) != json_value(repaired.snapshot()):
                    assert decision["phase"] == "recovery_lower"
                    predicates = lower_predicates(event, manifest, attempt_obs)
                    assert predicates["old_ready"] != predicates["repair_ready"]
                    assert (old.snapshot()["phase"] == "release") == predicates["old_ready"]
                    assert (repaired.snapshot()["phase"] == "release") == predicates["repair_ready"]
                    divergence = event["step"]
            verdict = event["verification"]
        rows.append({"point_id": trial["point_id"], "seed": trial["seed"], "excluded": result["episodes"][0]["excluded"],
                     "old_attempts": old.attempts, "old_steps_replayed": len(steps), "common_physical_steps": common_steps,
                     "first_lower_state_divergence_step": divergence, "predicates": predicates})
    assert len(rows) == 120
    report = {"scope": "engineering_known_M6_archived_observations_only", "confirmatory": False,
              "m6_suite_sha256": hashlib.sha256((args.m6_root / "suite.json").read_bytes()).hexdigest(),
              "all_passed": True, "trials": rows, "v2_old_trials": len(rows),
              "old_actions_replayed": sum(r["old_steps_replayed"] for r in rows),
              "repair_boundary_divergences": sum(r["first_lower_state_divergence_step"] is not None for r in rows),
              "no_v2r_post_divergence_rollout_or_success_claim": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream: json.dump(json_value(report), stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k != "trials"}, indent=2))


if __name__ == "__main__": main()
