"""Generate inspectable M6R evidence and an exact-data figure from the full audit."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--audit", type=Path, required=True)
    cli.add_argument("--curve", type=Path, required=True)
    cli.add_argument("--preview", type=Path, required=True)
    cli.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "docs/research/experiments/evidence")
    args = cli.parse_args()
    data = json.loads(args.audit.read_text())
    assert data["all_passed"] and data["counts"]["trial_records"] == 480
    assert data["counts"]["actions_replayed"] == 364800
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in data.items() if k != "trials"}
    summary["full_replay_audit_sha256"] = hashlib.sha256(args.audit.read_bytes()).hexdigest()
    summary["full_replay_audit_note"] = "Regenerate detail with tools/audit_m6r_return.py and retained final/pilot/known archives."
    summary["trials"] = []
    rows = []
    for trial in data["trials"]:
        replay = trial["replay"]
        e = replay["episodes"][0]
        recovery = e["recovery"]
        final = e.get("final_reference") or {}
        terminal = trial.get("terminal", {})
        summary["trials"].append({"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
                                  "replay_passed": replay["passed"], "max_action_replay_error": replay["max_action_replay_error"],
                                  "independent_endpoint": trial["independent_endpoint"], "terminal": terminal,
                                  "executed_phase_counts": trial["executed_phase_counts"],
                                  "passive_4cm_drift": trial.get("passive_4cm_drift")})
        row = {"point_id": trial["point_id"], "seed": trial["seed"], "system": trial["system"],
               "excluded": e["excluded"], "exclusion_reason": e.get("exclusion_reason"), "actions": e["steps"],
               "task_success": e["task_success_at_end"], "first_task_success_step": e["first_task_success_step"],
               "release_success": e["release_success_at_end"], "support_stability_success": e["support_stability_success_at_end"],
               "retracted": e["retraction_success_at_end"], "final_contact_grasped": final.get("is_grasped"),
               "final_horizontal_error_m": e["final_horizontal_error_m"],
               "disturbance_attempted": e["disturbance_attempted"], "disturbance_applied": e["disturbance_applied"],
               "first_reference_failure_step": (e.get("first_reference_failure") or {}).get("step"),
               "first_detected_failure_step": (e.get("first_detected_failure") or {}).get("step"),
               "first_failure_latency_steps": e["first_failure_latency_steps"],
               "controller_complete": e["controller_complete"], "retry_attempts": recovery["attempts"],
               "retry_state": recovery["state"], "retry_trigger_step": recovery.get("trigger_step"),
               "retry_first_action_step": recovery.get("first_action_step"), "retry_actions": recovery["action_steps"],
               "retry_path_m": recovery["observed_tcp_path_m"], "total_path_m": e["total_observed_tcp_path_m"],
               "retry_success": e["recovery_task_success"], "retry_failure_detail": recovery.get("failure_detail"),
               "lower_transition_step": e["lower_transition_step"], "lower_phase_timeout": e["lower_phase_timeout"],
               "release_reached": e["recovery_release_reached"], "release_first_action_step": e["recovery_release_first_action_step"],
               "release_executed": e["recovery_release_executed"], "release_action_count": trial["executed_phase_counts"].get("recovery_release", 0),
               "retraction_reached": e["recovery_retraction_reached"], "retraction_first_action_step": e["recovery_retraction_first_action_step"],
               "retraction_executed": e["recovery_retraction_executed"], "retraction_action_count": trial["executed_phase_counts"].get("recovery_retract", 0),
               "terminal_step": terminal.get("step"), "terminal_phase_step": terminal.get("phase_step"),
               "terminal_actions_repeat": terminal.get("all_later_actions_repeat_terminal"),
               "terminal_vertical_residual_m": terminal.get("lower_predicates", {}).get("vertical_residual_m"),
               "terminal_tcp_distance_m": terminal.get("lower_predicates", {}).get("tcp_distance_m"),
               "terminal_rotation_error_rad": terminal.get("lower_predicates", {}).get("rotation_error_rad"),
               "replay_passed": replay["passed"], "independent_endpoint_passed": trial["independent_endpoint"]["passed"],
               "max_action_replay_error": replay["max_action_replay_error"]}
        rows.append(row)
    assert len(rows) == 480 and sum(r["excluded"] for r in rows) == 24
    assert sum(r["actions"] for r in rows) == 364800
    for system in ("v2-old", "v2r"):
        selected = [r for r in rows if r["system"] == system and r["retry_attempts"]]
        assert len(selected) == 70
        if system == "v2r":
            assert all(r["retry_success"] and r["release_executed"] and r["retraction_executed"] for r in selected)
        else:
            assert all(r["lower_phase_timeout"] and not r["release_executed"] and not r["retraction_executed"] for r in selected)
    summary["aggregate_descriptive"] = {}
    for system in ("baseline", "v1", "v2-old", "v2r"):
        selected = [r for r in rows if r["system"] == system and not r["excluded"]]
        attempted = [r for r in selected if r["retry_attempts"]]
        summary["aggregate_descriptive"][system] = {"eligible_episodes": len(selected), "task_successes": sum(r["task_success"] for r in selected),
            "attempts": len(attempted), "successful_attempts": sum(r["retry_success"] for r in attempted),
            "lower_timeouts": sum(r["lower_phase_timeout"] for r in attempted),
            "release_executed_attempts": sum(r["release_executed"] for r in attempted),
            "retraction_executed_attempts": sum(r["retraction_executed"] for r in attempted)}
    summary["analysis_unit_caution"] = "19 common eligible seed scenes reused across 6 conditions, not 114 independent scenes per system."
    with (args.output / "AETHER_CL_M6R_Episode_Outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (args.output / "AETHER_CL_M6R_Native_Audit.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    shutil.copyfile(args.curve, args.output / "AETHER_CL_M6R_Native_Curve.csv")
    paired_rows = []
    for point in data["paired_outcomes"]:
        for comparison in ("v2r_vs_v2old", "v2old_vs_v1", "v2r_vs_v1"):
            paired_rows.append({"point_id": point["point_id"], "comparison": comparison,
                                "eligible_pairs": point["eligible_pairs"], "comparison_valid": point["complete_valid_pairing"],
                                **point[comparison]})
    with (args.output / "AETHER_CL_M6R_Paired_Outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paired_rows[0])); writer.writeheader(); writer.writerows(paired_rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), layout="constrained", gridspec_kw={"width_ratios": [1.3, 1]})
    labels = ["Normal", "1 cm", "4 cm", "8 cm", "12 cm", "20 cm"]
    colors = {"baseline": "#376a99", "v1": "#b98320", "v2-old": "#79579b", "v2r": "#b34d39"}
    names = {"baseline": "Baseline", "v1": "V1", "v2-old": "V2-old", "v2r": "V2R"}
    markers = {"baseline": "o", "v1": "s", "v2-old": "^", "v2r": "D"}
    for i, system in enumerate(names):
        cells = [c for c in data["cells"] if c["system"] == system]
        assert [c["task_successes"] for c in cells] == ([19]*6 if system == "v2r" else [19,19,6,0,0,0])
        axes[0].plot(np.arange(6)+(i-1.5)*.10, [100*c["validated_curve_success_rate"] for c in cells],
                     color=colors[system], marker=markers[system], markersize=6, linewidth=1, alpha=.9, label=names[system])
    axes[0].set_xticks(range(6), labels); axes[0].set_ylim(-7, 116)
    axes[0].set_yticks([0,25,50,75,100], ["0%","25%","50%","75%","100%"])
    axes[0].set_ylabel("Released-placement success")
    axes[0].set_xlabel("Synthetic post-release displacement")
    axes[0].set_title("Fresh outcomes across the four systems", loc="left", fontsize=13)
    axes[0].legend(loc="upper right", bbox_to_anchor=(1,.83), frameon=False, ncol=2, fontsize=10)
    for x, n in enumerate((19,19,6,0,0,0)):
        axes[0].text(x-.15, n/19*100+5, f"{n}/19", ha="center", fontsize=10)
    axes[0].text(3.4,105.5,"V2R: 19/19 in every cell",ha="center",fontsize=10,color=colors["v2r"])
    stage_names = ["Released", "Retracted", "Placed"]
    for i, system in enumerate(("v2-old", "v2r")):
        selected = [r for r in rows if r["system"] == system and r["retry_attempts"]]
        values = [sum(r[k] for r in selected) for k in ("release_executed", "retraction_executed", "retry_success")]
        assert values == ([0]*3 if system == "v2-old" else [70]*3)
        positions = np.arange(3)+(i-.5)*.32
        axes[1].bar(positions,values,width=.29,color=colors[system],label=names[system])
        for x, n in zip(positions,values): axes[1].text(x,n+2,f"{n}/70",ha="center",fontsize=10)
    axes[1].set_xticks(range(3),stage_names); axes[1].set_ylim(0,86)
    axes[1].set_ylabel("Recovery attempts reaching the outcome")
    axes[1].set_title("The changed transition permits release",loc="left",fontsize=13)
    axes[1].legend(loc="upper left",frameon=False,ncol=2,fontsize=10)
    axes[1].set_xlabel("Both systems attempt the same 70 cases")
    for ax in axes:
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y",color="#e5e5e5",linewidth=.7);ax.set_axisbelow(True)
    fig.suptitle("M6R native evidence — fresh seeds 120–139", fontsize=16, ha="left", x=.01)
    fig.supxlabel("19 common eligible seed scenes; seed 132 excluded in all 24 cells. One cube, privileged state, synthetic relocation.",fontsize=10)
    fig.savefig(args.output / "AETHER_CL_M6R_Results.svg",metadata={"Date":None})
    fig.savefig(args.preview,dpi=130)
    plt.close(fig)
    print("Published machine audit, 480 episode rows, 18 paired rows, native curve and SVG")


if __name__ == "__main__":
    main()
