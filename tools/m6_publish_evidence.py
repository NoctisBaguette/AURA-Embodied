"""Publish inspectable M6 audit summaries, episode CSV and an exact-data figure.

Input is the complete output of audit_m6_return.py and the returned native CSV.
No simulator is launched. Repository evidence outputs are overwritten on request.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--curve", type=Path, required=True)
    parser.add_argument("--preview", type=Path, help="Optional PNG for rendered inspection")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] /
                        "docs/research/experiments/evidence")
    args = parser.parse_args()
    data = json.loads(args.audit.read_text())
    assert data["all_passed"] and len(data["trials"]) == 360
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in data.items() if k != "trials"}
    summary["full_replay_audit_sha256"] = hashlib.sha256(args.audit.read_bytes()).hexdigest()
    summary["full_replay_audit_note"] = "Regenerate full detail with tools/audit_m6_return.py and the three retained archives."
    summary["trials"] = []
    rows = []
    for trial in data["trials"]:
        replay = trial["replay"]
        assert replay["passed"] and trial["independent_endpoint"]["passed"]
        episode = replay["episodes"][0]
        final = episode.get("final_reference") or {}
        recovery = episode.get("recovery") or {}
        abort = trial.get("abort", {})
        summary["trials"].append({"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
                                  "replay_passed": replay["passed"], "checks": replay["checks"],
                                  "independent_endpoint": trial["independent_endpoint"],
                                  "abort": abort, "passive_4cm_drift": trial.get("passive_4cm_drift")})
        row = {"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
               "excluded": episode["excluded"], "exclusion_reason": episode.get("exclusion_reason"),
               "actions": episode["steps"], "task_success": episode["task_success_at_end"],
               "release_success": episode.get("release_success_at_end"),
               "support_stability_success": episode.get("support_stability_success_at_end"),
               "retracted": episode.get("retraction_success_at_end"), "final_contact_grasped": final.get("is_grasped"),
               "final_horizontal_error_m": episode.get("final_horizontal_error_m"),
               "first_task_success_step": episode.get("first_task_success_step"),
               "disturbance_applied": episode.get("disturbance_applied"),
               "first_reference_failure_step": (episode.get("first_reference_failure") or {}).get("step"),
               "first_detected_failure_step": (episode.get("first_detected_failure") or {}).get("step"),
               "retry_attempts": recovery.get("attempts", 0), "retry_state": recovery.get("state"),
               "retry_trigger_step": recovery.get("trigger_step"), "retry_first_action_step": recovery.get("first_action_step"),
               "retry_actions": recovery.get("action_steps", 0), "retry_path_m": recovery.get("observed_tcp_path_m"),
               "total_path_m": episode.get("total_observed_tcp_path_m"), "abort_reason": abort.get("reason"),
               "abort_step": abort.get("step"), "abort_lower_phase_step": abort.get("phase_step"),
               "abort_vertical_residual_m": abort.get("lower_vertical_error_m"),
               "abort_tcp_target_distance_m": abort.get("tcp_target_distance_m"),
               "abort_rotation_residual_rad": abort.get("rotation_error_rad"),
               "abort_cube_horizontal_error_m": abort.get("horizontal_error_m"),
               "abort_contact_grasped": abort.get("contact_grasped"), "abort_contact_supported": abort.get("contact_supported"),
               "abort_vertical_table_contact_force_n": abort.get("vertical_table_contact_force_n"),
               "recovery_release_executed": abort.get("release_phase_executed_during_attempt"),
               "terminal_actions_repeat_abort": abort.get("all_terminal_actions_repeat_abort"),
               "replay_passed": replay["passed"], "independent_endpoint_passed": trial["independent_endpoint"]["passed"],
               "max_action_replay_error": replay["max_action_replay_error"]}
        rows.append(row)
    assert sum(r["actions"] for r in rows) == 259200
    assert sum(r["excluded"] for r in rows) == 36
    assert sum(r["retry_attempts"] for r in rows) == 62
    with (args.output / "AETHER_CL_M6_Episode_Outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    (args.output / "AETHER_CL_M6_Native_Audit.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    shutil.copyfile(args.curve, args.output / "AETHER_CL_M6_Native_Curve.csv")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    labels = ["Normal", "1 cm", "4 cm", "8 cm", "12 cm", "20 cm"]
    colors = {"baseline": "#2766a3", "v1": "#ad6c12", "v2": "#6c5792"}
    markers = {"baseline": "o", "v1": "s", "v2": "^"}
    for i, system in enumerate(("baseline", "v1", "v2")):
        cells = [c for c in data["cells"] if c["system"] == system]
        assert [c["task_successes"] for c in cells] == [18, 18, 10, 0, 0, 0]
        axes[0].scatter(np.arange(6) + (i - 1) * .16, [100 * c["task_success_rate_at_end"] for c in cells],
                        color=colors[system], marker=markers[system], s=48, label={"baseline": "Baseline", "v1": "V1", "v2": "V2"}[system], zorder=3)
    axes[0].set_xticks(range(6), labels); axes[0].set_ylim(-5, 112)
    axes[0].set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    axes[0].set_ylabel("Released-placement success")
    axes[0].set_title("Equal endpoint outcomes across systems", loc="left", fontsize=13)
    axes[0].legend(loc="upper right", frameon=False)
    axes[0].text(.02, .68, "18 eligible seeds per cell\n2 initial exclusions retained", transform=axes[0].transAxes, fontsize=10)
    for x, n in enumerate((18, 18, 10, 0, 0, 0)):
        axes[0].text(x, n / 18 * 100 + 5, f"{n}/18", ha="center", fontsize=10)
    attempts = [t for t in data["trials"] if "abort" in t]
    for i, point in enumerate(("release-shift-040mm", "release-shift-080mm", "release-shift-120mm", "release-shift-200mm")):
        values = sorted(t["abort"]["lower_vertical_error_m"] * 1000 for t in attempts if t["point_id"] == point)
        axes[1].scatter(np.full(len(values), i) + np.linspace(-.14, .14, len(values)), values,
                        color=colors["v2"], s=26, alpha=.8)
        axes[1].text(i, 13.0, f"n={len(values)}", ha="center", fontsize=10)
    axes[1].axhline(3, color="#414141", linestyle="--", linewidth=1.2)
    axes[1].text(2.55, 3.4, "Lower gate: 3 mm", ha="right", fontsize=10)
    axes[1].set_xticks(range(4), ["4 cm", "8 cm", "12 cm", "20 cm"])
    axes[1].set_ylim(0, 14); axes[1].set_ylabel("TCP vertical residual at first abort (mm)")
    axes[1].set_title("All 62 retries miss the lower gate", loc="left", fontsize=13)
    for ax in axes:
        ax.set_xlabel("Synthetic post-release displacement")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e5e5e5", linewidth=.7); ax.set_axisbelow(True)
    fig.suptitle("M6 native evidence — seeds 100–119", fontsize=16, ha="left", x=.01)
    fig.savefig(args.output / "AETHER_CL_M6_Results.svg", metadata={"Date": None})
    if args.preview:
        fig.savefig(args.preview, dpi=120)
    plt.close(fig)
    print("Published 360 episode rows, native audit, curve and SVG")


if __name__ == "__main__": main()
