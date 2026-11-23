"""Frozen M8: first18 commissioning pause, then exactly342 unstarted slots."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import traceback

import numpy as np

from . import m8_frozen as frozen
from .runtime import json_value

ARCHIVE_ROOT = "m8-placement-seeds160-179"
PILOT_READY = "M8_FIRST18_READY_FOR_INDEPENDENT_REVIEW"
FINAL_READY = "M8_FROZEN_EVIDENCE_VALID"


def write_json(path, value):
    """Atomic parent checkpoint, including the pending slot before its reset."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(json_value(value), stream, indent=2, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def plan():
    pilot = [(p,s,y) for p in frozen.PILOT_POINTS for s in frozen.SEEDS[:2] for y in frozen.SYSTEMS]
    remaining = [(p,s,y) for p in frozen.POINT_IDS for s in frozen.SEEDS for y in frozen.SYSTEMS
                 if (p,s,y) not in pilot]
    return [{"slot":i,"point_id":p,"seed":s,"system":y} for i,(p,s,y) in enumerate(pilot+remaining)]


def paths(output, destination, pilot):
    if destination == pilot or any(p.is_relative_to(output) for p in (destination,pilot)):
        raise ValueError("Require distinct archives outside the retained study directory")
    if destination.exists() or Path(str(destination)+".receipt.json").exists():
        raise FileExistsError("Final archive path already exists; retain evidence")


def archive(output, destination):
    if destination.exists() or Path(str(destination)+".receipt.json").exists():
        raise FileExistsError("Never overwrite an evidence archive")
    write_json(output/"file_index.json", frozen.file_index(output))
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against an archive appearing after preflight.
    with destination.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as bundle:
        bundle.add(output, arcname=ARCHIVE_ROOT, filter=lambda item:
                   None if Path(item.name).name in ("runner.lock", ".lock") else item)
    digest = frozen.sha256(destination)
    with Path(str(destination)+".receipt.json").open("x") as stream:
        json.dump({"archive":str(destination),"bytes":destination.stat().st_size,"sha256":digest},stream,indent=2)
        stream.write("\n")
    print("Archive:",destination,flush=True); print("SHA-256:",digest,flush=True)
    return digest


def verify_archive(output, pilot, digest):
    if not digest or frozen.sha256(pilot) != digest:
        raise ValueError("Immutable pilot archive differs from independently reviewed SHA-256")
    indexed = frozen.verify_index(output)
    receipt = json.loads(Path(str(pilot)+".receipt.json").read_text())
    if receipt != {"archive":str(pilot),"bytes":pilot.stat().st_size,"sha256":digest}:
        raise ValueError("Pilot archive receipt differs")
    with tarfile.open(pilot) as bundle:
        files = [m for m in bundle.getmembers() if m.isfile()]
        expected = {ARCHIVE_ROOT+"/"+n for n in (*indexed,"file_index.json")}
        if len(files) != len(expected) or {m.name for m in files} != expected or any(
                not (m.isfile() or m.isdir()) for m in bundle.getmembers()):
            raise ValueError("Pilot archive file set differs")
        for member in files:
            relative = member.name.removeprefix(ARCHIVE_ROOT+"/")
            if bundle.extractfile(member).read() != (output/relative).read_bytes():
                raise ValueError("Live checkpoint differs from immutable pilot: "+relative)


def snapshot(output):
    sources = output/"sources"; sources.mkdir()
    for name in frozen.SOURCES:
        (sources/name).write_bytes(Path(frozen.__file__).with_name(name).read_bytes())
    for path in (frozen.RECEIPT,frozen.RESPONSE_REVIEW,frozen.DOSE_REVIEW,frozen.REVIEW,
                 frozen.PROTOCOL_PATH,frozen.HISTORY_SOURCE):
        (sources/path.name).write_bytes(path.read_bytes())


def verify_snapshots(output):
    expected = {n:Path(frozen.__file__).with_name(n) for n in frozen.SOURCES}
    expected.update({p.name:p for p in (frozen.RECEIPT,frozen.RESPONSE_REVIEW,frozen.DOSE_REVIEW,
                                      frozen.REVIEW,frozen.PROTOCOL_PATH,frozen.HISTORY_SOURCE)})
    if {p.name for p in (output/"sources").iterdir()} != set(expected):
        raise ValueError("Frozen snapshot file set differs")
    if any((output/"sources"/n).read_bytes() != p.read_bytes() for n,p in expected.items()):
        raise ValueError("Current source/protocol/receipts differ from retained pilot")


def verify_retained_pilot(output, pilot, digest, report):
    """The live suite advances; original18 raw cases and sources stay immutable."""
    if frozen.sha256(pilot)!=digest: raise ValueError("Retained pilot archive changed during resume")
    with tarfile.open(pilot) as bundle:
        original=json.load(bundle.extractfile(ARCHIVE_ROOT+"/suite.json"))
        if report["trials"][:18]!=original["trials"] or report["pilot_gate"]!=original["pilot_gate"]:
            raise ValueError("Original18 pilot outcomes changed during resume")
        index=json.load(bundle.extractfile(ARCHIVE_ROOT+"/file_index.json"))
        for relative,record in index.items():
            if relative.startswith("sources/") or any(relative.startswith(t["directory"]+"/") for t in original["trials"]):
                path=output/relative
                if path.stat().st_size!=record["bytes"] or frozen.sha256(path)!=record["sha256"]:
                    raise ValueError("Original pilot raw evidence changed: "+relative)


def physical_diagnostics(case, carrier):
    """Read-only diagnostics; they never enter verification or motor commands.

    Commissioned physical_effects span the whole post-pulse episode and may
    include recovery. This separates the pulse and pre-intervention response.
    """
    effects = carrier["physical_effects"]
    before, after = effects["before_pulse"], effects["after_pulse"]
    first = carrier["episode"]["recovery"].get("first_action_step")
    end = first-1 if first is not None else frozen.MAX_STEPS
    def vector(state, key, size): return np.asarray(state[key],dtype=float).reshape(size)
    samples = []
    for line in (case/"physics.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record["event"] == "physics_action" and frozen.INJECTION_STEP <= record["step"] <= end:
            samples.extend(s["after_physics"] for s in record["substeps"])
    origin = vector(before,"cube_pose_world",7)[:3] if before else None
    return {"window_end_action_before_first_recovery_or_episode_end":end,
        "pulse_displacement_world_m":(vector(after,"cube_pose_world",7)[:3]-origin).tolist() if before and after else None,
        "pulse_delta_linear_velocity_world_m_s":(vector(after,"cube_linear_velocity_m_s",3)-vector(before,"cube_linear_velocity_m_s",3)).tolist() if before and after else None,
        "pre_intervention_peak_horizontal_displacement_m":max((float(np.linalg.norm((vector(s,"cube_pose_world",7)[:3]-origin)[:2])) for s in samples),default=None),
        "pre_intervention_peak_linear_speed_m_s":max((float(np.linalg.norm(vector(s,"cube_linear_velocity_m_s",3))) for s in samples),default=None),
        "pre_intervention_support_loss":any(vector(s,"cube_table_contact_force_world_n",3)[2]<.01 for s in samples),
        "whole_episode_effects_include_recovery":first is not None}


def summarize(trials):
    lookup = {(t["seed"],t["point_id"],t["system"]):t["result"] for t in trials}
    paired = []
    for seed in frozen.SEEDS:
        for point in frozen.candidate_points():
            p = point["point_id"]
            if not all((seed,p,s) in lookup for s in frozen.SYSTEMS): continue
            b,v1,v2 = (lookup[seed,p,s]["episode"] for s in frozen.SYSTEMS)
            eligible = not any(e["excluded"] for e in (b,v1,v2))
            attempt = bool(v2["recovery"]["attempts"])
            paired.append({"seed":seed,"point_id":p,"eligible":eligible,
                "success":{s:lookup[seed,p,s]["episode"]["task_success_at_end"] for s in frozen.SYSTEMS},
                "v2_attempts":v2["recovery"]["attempts"],"v2_recovery_actions":v2["recovery"]["action_steps"],
                "v2_successful_recovery_episode":eligible and v2["recovery_task_success"],
                "v2_rescue":eligible and not b["task_success_at_end"] and v2["task_success_at_end"],
                "v2_unnecessary_attempt":eligible and b["task_success_at_end"] and attempt,
                "v2_final_regression":eligible and b["task_success_at_end"] and not v2["task_success_at_end"],
                "v2_added_tcp_path_m":v2["total_observed_tcp_path_m"]-v1["total_observed_tcp_path_m"],
                "v1_detection":v1["first_detected_failure"],"v2_detection":v2["first_detected_failure"],
                "v2_recovery":v2["recovery"],"v2_lower_transition_step":v2["lower_transition_step"],
                "v2_release_executed":v2["recovery_release_executed"],"v2_retraction_executed":v2["recovery_retraction_executed"]})
    cells=[]
    for point in frozen.candidate_points():
        for system in frozen.SYSTEMS:
            carriers=[t["result"] for t in trials if t["point_id"]==point["point_id"] and t["system"]==system]
            episodes=[c["episode"] for c in carriers]; eligible=[e for e in episodes if not e["excluded"]]
            successes=sum(e["task_success_at_end"] for e in eligible)
            metrics=[c["verification_metrics"] for c in carriers if c.get("verification_metrics") is not None]
            confusion=Counter()
            for m in metrics: confusion.update(m.get("confusion",{}))
            counts={k:sum(m[k] for m in metrics) for k in
                ("steps","uncertain_steps","true_positive","false_positive","false_negative","true_negative","uncertain_on_negative")}
            def rate(a,b): return a/b if b else None
            correct=sum(value for key,value in confusion.items() if key.split("->")[0]==key.split("->")[1] and key.split("->")[0]!="NONE")
            cells.append({"point_id":point["point_id"],"command_force_y_n":point["command_force_y_n"],"system":system,
                "requested":20,"completed":len(episodes),"excluded":len(episodes)-len(eligible),"eligible":len(eligible),
                "task_successes":successes,"success_rate_requested":successes/20 if len(episodes)==20 else None,
                "success_rate_eligible":successes/len(eligible) if len(episodes)==20 and eligible else None,
                "force_applied_episodes":sum(c["physical_force_applied"] for c in carriers),
                "controller_complete":sum(e["controller_complete"] for e in eligible),
                "release_successes":sum(e["release_success_at_end"] for e in eligible),
                "stable_support_successes":sum(e["support_stability_success_at_end"] for e in eligible),
                "retraction_successes":sum(e["retraction_success_at_end"] for e in eligible),
                "recovery_attempts":sum(e["recovery"]["attempts"] for e in eligible),
                "successful_recovery_episodes":sum(e["recovery_task_success"] for e in eligible),
                "verification_counts":counts,
                "failure_detection_precision":rate(counts["true_positive"],counts["true_positive"]+counts["false_positive"]),
                "failure_detection_recall":rate(counts["true_positive"],counts["true_positive"]+counts["false_negative"]),
                "diagnosis_accuracy_when_failure_detected":rate(correct,counts["true_positive"]),
                "diagnosis_confusion":dict(sorted(confusion.items())),
                "failure_detection_latency_steps":[e["first_failure_latency_steps"] for e in eligible],
                "final_horizontal_error_m":[e["final_horizontal_error_m"] for e in eligible],
                "observed_tcp_path_m":[e["total_observed_tcp_path_m"] for e in eligible],
                "recovery_actions":[e["recovery"]["action_steps"] for e in eligible]})
    return {"cells":cells,"paired_outcomes":paired,"totals":{
        "requested_episodes":360,"completed_episodes":len(trials),"complete_matched_scene_conditions":len(paired),
        "eligible_matched_scene_conditions":sum(p["eligible"] for p in paired),
        "v2_rescues":sum(p["v2_rescue"] for p in paired),"v2_unnecessary_attempts":sum(p["v2_unnecessary_attempt"] for p in paired),
        "v2_regressions":sum(p["v2_final_regression"] for p in paired),
        "analysis_unit":"20_common_seed_scenes_not360_independent_scenes"}}


def gate(report, output, pilot):
    n=18 if pilot else 360
    if len(report["trials"]) != n: raise ValueError("Incomplete fixed checkpoint")
    for item,trial in zip(plan()[:n],report["trials"]):
        expected_dir=directory(item)
        if (any(trial[k]!=v for k,v in item.items()) or trial["returncode"]!=0
                or trial["directory"]!=expected_dir or trial["output"]!=str(output/expected_dir)):
            raise ValueError("Started/completed slot does not match frozen order")
        carrier=frozen.checked_trial(output/expected_dir,item,report["identity"])
        if carrier!=trial["result"]: raise ValueError("Parent and child results differ")
        if physical_diagnostics(output/expected_dir,carrier)!=trial["physical_diagnostics"]:
            raise ValueError("Physical diagnostics differ from retained samples")
    comparisons=frozen.comparisons(report["trials"],output)
    counts=dict(Counter(c["kind"] for c in comparisons))
    expected=report["protocol"]["pilot_comparison_counts" if pilot else "comparison_counts"]
    if counts!=expected or not all(c["passed"] for c in comparisons):
        raise ValueError("Fixed matched comparisons failed; retain outcomes and traces")
    return {"passed":True,"performance_gate":False,"complete_trial_replays":n,
            "comparison_counts":counts,"comparisons":comparisons,"summary":summarize(report["trials"])}


def directory(item):
    return f"slot-{item['slot']:03d}-{item['point_id']}-seed{item['seed']}-{item['system']}"


def stop_child(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGINT)
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=15)


def launch(command, stream):
    process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    try: return process.wait(timeout=600)
    except BaseException:
        stop_child(process)
        raise


def validate_checkpoint(output, destination, pilot, settings, identity, digest):
    verify_archive(output,pilot,digest)
    report=json.loads((output/"suite.json").read_text())
    if (report["state"]!="paused_first18" or report["protocol"]!=settings or report["identity"]!=identity
            or report["environment"]!=frozen.environment() or report["plan"]!=plan()
            or report["output_path"]!=str(output) or report["archive_path"]!=str(destination)
            or report["pilot_archive"]!=str(pilot) or report["saved_archive"]!=str(pilot)):
        raise ValueError("Resume only the unchanged reviewed first18 checkpoint and environment")
    verify_snapshots(output)
    reconstructed=gate(report,output,True)
    if reconstructed!=report["pilot_gate"] or reconstructed["summary"]!=report["summary"]:
        raise ValueError("Pilot gate/summary differs from independent reconstruction")
    return report


def run_suite(output,destination,pilot,expected_head,commission_report,commission_archive,
              resume=False,pilot_sha256=None,check_pilot=False,stop_after=None):
    output,destination,pilot=(p.resolve() for p in (output,destination,pilot))
    if stop_after not in (None,18) or (resume and stop_after is not None) or (resume and check_pilot):
        raise ValueError("Initial execution stops at18; resume completes342; no outcome-dependent stops")
    if resume or check_pilot:
        # Guard failures must not mutate the indexed first18 checkpoint.
        settings,identity=frozen.preflight(expected_head)
        report=validate_checkpoint(output,destination,pilot,settings,identity,
            pilot_sha256 or (None if resume else json.loads(Path(str(pilot)+".receipt.json").read_text())["sha256"]))
        if check_pilot:
            print(json.dumps(report["pilot_gate"],indent=2),flush=True);print(PILOT_READY,flush=True)
            return report
        paths(output,destination,pilot)
    else:
        paths(output,destination,pilot)
        if output.exists() or pilot.exists() or Path(str(pilot)+".receipt.json").exists():
            raise FileExistsError("Require new study/pilot paths; do not rerun retained fresh seeds")
        output.mkdir(parents=True,exist_ok=False)
        report={"scope":frozen.SCOPE,"confirmatory":True,"state":"starting",
            "time_utc":datetime.now(timezone.utc).isoformat(),"plan":plan(),"trials":[],
            "output_path":str(output),"archive_path":str(destination),"pilot_archive":str(pilot),
            "saved_archive":str(pilot),"fresh_study_started":False,"force_family_frozen_for_fresh_study":True,
            "performance_success_gate":False,"model_training":False}
    with (output/"runner.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        target=destination if resume else pilot
        try:
            settings,identity=frozen.preflight(expected_head)
            if resume:
                # Recheck under lock before authorizing omission of own reset history.
                report=validate_checkpoint(output,destination,pilot,settings,identity,pilot_sha256)
                report["immutable_pilot_sha256"]=pilot_sha256
            else:
                report.update(protocol=settings,identity=identity,environment=frozen.environment())
                snapshot(output)
            print("Replaying independently reviewed36 commissioning episodes before any fresh reset",flush=True)
            commissioning=frozen.validate_commission(commission_report,commission_archive)
            if resume and commissioning!=report["commissioning_validation"]:
                raise ValueError("Reviewed commissioning prerequisite changed")
            report["commissioning_validation"]=commissioning
            print("Scanning retained reset history for frozen160–179",flush=True)
            report["resume_seed_history" if resume else "seed_history"]=frozen.seed_history(output,resume=resume)
            report.update(state="running",runner_pid=os.getpid(),saved_archive=str(target))
            write_json(output/"suite.json",report)
            limit=360 if resume else 18
            for item in plan()[len(report["trials"]):limit]:
                # Software and non-volatile environment must remain unchanged.
                if frozen.preflight(expected_head)!=(settings,identity) or frozen.environment()!=report["environment"]:
                    raise ValueError("Runtime identity/environment changed between slots")
                case=output/directory(item);case.mkdir(exist_ok=False)
                record={**item,"directory":directory(item),"output":str(case),"returncode":None,
                        "result":{"state":"started_pending_child_result"}}
                report["trials"].append(record);report["fresh_study_started"]=True
                write_json(output/"suite.json",report)
                print(f"START {item['slot']+1}/360 {item['point_id']} seed{item['seed']} {item['system']}",flush=True)
                command=[sys.executable,"-u","-m","aether_cl.m8_frozen","--expected-head",expected_head,
                    "--output",str(case),"--seed",str(item["seed"]),"--system",item["system"],
                    "--point",item["point_id"],"--suite",str(output/"suite.json")]
                try:
                    with (case/"stdout.log").open("x") as stream: record["returncode"]=launch(command,stream)
                except subprocess.TimeoutExpired:
                    record["result"]={"state":"child_timeout_retained","replacement":False,"timeout_s":600}
                    raise
                child_path=case/"m8_result.json"
                record["result"]=json.loads(child_path.read_text()) if child_path.exists() else {"state":"missing_child_result_retained"}
                write_json(output/"suite.json",report)
                if record["returncode"]: raise ValueError("Fresh child failed; retain started slot; no replacement or resume")
                carrier=frozen.checked_trial(case,item,identity)
                if carrier!=record["result"]: raise ValueError("Fresh parent/child result differs")
                record["physical_diagnostics"]=physical_diagnostics(case,carrier)
                write_json(output/"suite.json",report)
                print(f"END {item['slot']+1}/360 {carrier['state']}",flush=True)
            if frozen.preflight(expected_head)!=(settings,identity) or frozen.environment()!=report["environment"]:
                raise ValueError("Final runtime identity/environment changed")
            verify_snapshots(output)
            if resume: verify_retained_pilot(output,pilot,pilot_sha256,report)
            checked=gate(report,output,not resume)
            report["final_gate" if resume else "pilot_gate"]=checked
            report["summary"]=checked["summary"]
            report["state"]="valid_frozen_evidence" if resume else "paused_first18"
            report["next_boundary"]="independent_final_audit_then02" if resume else "independent_pilot_review_before342"
            with (output/"cells.csv").open("w",newline="") as stream:
                rows=report["summary"]["cells"];writer=csv.DictWriter(stream,fieldnames=rows[0])
                writer.writeheader();writer.writerows(rows)
        except BaseException as error:
            report.update(state="error_retained",error=f"{type(error).__name__}: {error}",traceback=traceback.format_exc())
            print(report["error"],flush=True)
        finally:
            report["saved_archive"]=str(target)
            write_json(output/"suite.json",report)
            archive(output,target)
        if report["state"] not in ("paused_first18","valid_frozen_evidence"):
            print("M8_ERROR_RETAIN_EVIDENCE",flush=True);raise SystemExit(1)
        print(FINAL_READY if resume else PILOT_READY,flush=True)
    return report


def main():
    def interrupted(signum, frame):
        raise InterruptedError("Sweep received termination signal; retain started evidence")
    signal.signal(signal.SIGTERM, interrupted)
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("output","archive","pilot-archive","commission-report","commission-archive"):
        cli.add_argument("--"+name,type=Path,required=True)
    cli.add_argument("--expected-head",required=True)
    cli.add_argument("--resume",action="store_true");cli.add_argument("--check-pilot",action="store_true")
    cli.add_argument("--pilot-sha256");cli.add_argument("--stop-after",type=int)
    args=cli.parse_args()
    if args.resume and not args.pilot_sha256:cli.error("--resume requires independently reviewed --pilot-sha256")
    run_suite(args.output,args.archive,args.pilot_archive,args.expected_head,args.commission_report,
              args.commission_archive,args.resume,args.pilot_sha256,args.check_pilot,args.stop_after)


if __name__=="__main__":main()
