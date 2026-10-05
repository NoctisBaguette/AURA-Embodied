"""Invocation independence, strict runtime pairing, retained errors and 960-slot wiring."""

from contextlib import ExitStack, redirect_stdout
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from aether_cl import m5_attribution as m5
from aether_cl.m5_audit import check_trial, compare_scheduled
from aether_cl.m5_scheduled import ScheduledRecoveryController, FIRST_ACTION
from aether_cl.m5_v3_runtime import V3Config, run as v3_run
from aether_cl.m3_runtime import M3Config, run as m3_run
from aether_cl.policies import FixedPickCube
from aether_cl.recovery import RecoveryController
from aether_cl.verification import VerificationMetrics
from test_policy import BASE
from test_verification import state
from test_m2 import inject
from test_m3_screening import VariedEnvironment

SOFTWARE = {"git_commit":"fixture", "git_dirty":False}


class ScheduledTests(unittest.TestCase):
    def test_schedule_matches_v2_capability_without_consuming_a_verdict(self):
        self.assertIs(ScheduledRecoveryController.observe, RecoveryController.observe)
        for family, first in FIRST_ACTION.items():
            observation = state()
            a = ScheduledRecoveryController(FixedPickCube(observation,BASE),BASE,360,family)
            b = RecoveryController(FixedPickCube(observation,BASE),BASE,360)
            for step in range(1,first+15):
                x, dx = a.action(observation,step)
                y, dy = b.action(observation,step,{"status":"failed","failure":"OBJECT_LOST"} if step>=first else {})
                np.testing.assert_array_equal(x,y)
                self.assertEqual(dx,dy)
                a.observe(observation);b.observe(observation)
                sa,sb=a.snapshot(),b.snapshot()
                sa.pop("reason");sb.pop("reason")
                self.assertEqual(sa,sb)
            self.assertEqual(a.trigger_step,first-1)
            self.assertEqual(a.first_action_step,first)
            self.assertEqual(a.manifest()["inputs"],["step","obj_pose","goal_pos","tcp_pose","qpos"])
            with self.assertRaises(TypeError):
                a.action(observation,first,{"status":"failed"})

    def test_runtime_strict_prefixes_and_aligned_full_traces_at_small_large_magnitudes(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            stack.enter_context(patch("aether_cl.m3_runtime.software_manifest",return_value=SOFTWARE))
            stack.enter_context(patch("aether_cl.m5_v3_runtime.software_manifest",return_value=SOFTWARE))
            root=Path(temp)
            for family,condition in (("shift","object_shift"),("drop","object_drop")):
                for disturbance,magnitude in (("none",.12),(condition,.02),(condition,.20)):
                    paths={}
                    for system in m5.SYSTEMS:
                        opts=dict(system=system,verification=system in ("v1","v2"),seed=0,
                                  disturbance=disturbance,disturbance_magnitude=magnitude,render=False,
                                  output=root/f"{family}-{disturbance}-{magnitude}-{system}")
                        config=V3Config(family=family,**opts) if system=="v3" else M3Config(**opts)
                        runner=v3_run if system=="v3" else m3_run
                        result=runner(config,env_factory=lambda _:VariedEnvironment(),disturbance_fn=inject)
                        paths[system]=Path(result["run_directory"])
                        checked=check_trial(paths[system],config,SOFTWARE)
                        self.assertTrue(checked["passed"],checked["failed_checks"])
                    self.assertTrue(m5.compare_pair(paths["baseline"],paths["v1"])["passed"])
                    self.assertTrue(m5.compare_recovery(paths["v1"],paths["v2"])["passed"])
                    self.assertTrue(compare_scheduled(paths["baseline"],paths["v3"])["passed"])
                    paired=compare_scheduled(paths["v2"],paths["v3"],True)
                    self.assertTrue(paired["passed"],paired)
            # Strict prefix must reject even a small pre-intervention state change.
            path=paths["v3"]/"events.jsonl"
            events=[json.loads(l) for l in path.read_text().splitlines()]
            e=next(e for e in events if e["event"]=="step" and e["step"]==20)
            e["observation"]["extra"]["goal_pos"][0][0]+=.001
            path.write_text("\n".join(json.dumps(e) for e in events)+"\n")
            self.assertFalse(compare_scheduled(paths["baseline"],paths["v3"])["passed"])
            self.assertFalse(check_trial(paths["v3"],config,SOFTWARE)["passed"])

    def test_v3_never_constructs_verifier_and_reference_contact_labels_do_not_control_actions(self):
        class FalseContact(VariedEnvironment):
            def step(self,action):
                obs,reward,term,trunc,info=super().step(action)
                info["is_grasped"]=[False]
                return obs,reward,term,trunc,info
        with tempfile.TemporaryDirectory() as temp, patch("aether_cl.m5_v3_runtime.software_manifest",return_value=SOFTWARE), \
                patch("aether_cl.verification.StateVerifier",side_effect=AssertionError("V3 invoked verifier")):
            root=Path(temp);traces=[]
            for i,environment in enumerate((VariedEnvironment,FalseContact)):
                config=V3Config(family="drop",seed=0,output=root/str(i))
                result=v3_run(config,env_factory=lambda _:environment(),disturbance_fn=inject)
                events=[json.loads(l) for l in (Path(result["run_directory"])/"events.jsonl").read_text().splitlines()]
                traces.append([{k:e[k] for k in ("action","controller_decision","recovery")} for e in events if e["event"]=="step"])
                self.assertIsNone(result["evaluation"]["verification_metrics"])
            self.assertEqual(traces[0],traces[1])
            excluded=v3_run(V3Config(family="shift",seed=8,output=root/"excluded"),env_factory=lambda _:VariedEnvironment(),disturbance_fn=inject)
            checked=check_trial(Path(excluded["run_directory"]),V3Config(family="shift",seed=8,output=root/"excluded"),SOFTWARE)
            self.assertTrue(checked["passed"],checked["failed_checks"])
            self.assertTrue(excluded["episodes"][0]["excluded"])


class SweepTests(unittest.TestCase):
    def fixture(self,trial,software):
        c=trial["config"];excluded=c["seed"]==88
        baseline_success=c["disturbance"]=="none" or c["disturbance_magnitude"]==.02
        attempt=not excluded and (c["system"]=="v3" or c["system"]=="v2" and not baseline_success)
        # Exercise measured V3 regressions and harder V2 failures; no success gate.
        success=not excluded and (baseline_success if c["system"] in ("baseline","v1") else
                   c["disturbance"]!="none" if c["system"]=="v3" else baseline_success or c["disturbance_magnitude"]<.20)
        first=FIRST_ACTION[trial["family"]]-1 if attempt else None
        e={"episode":0,"seed":c["seed"],"excluded":excluded,"task_success_at_end":success,
           "first_detected_failure":None,"first_failure_latency_steps":None,
           "final_cube_goal_distance_m":.01 if success else .3,"recovery_task_success":attempt and success,
           "recovery":{"attempts":int(attempt),"state":"attempt_complete" if attempt and success else "aborted" if attempt else "nominal",
                       "trigger_step":first,"action_steps":100 if attempt else 0,"observed_tcp_path_m":.5 if attempt else 0.,
                       "failure_detail":"fixture_failure" if attempt and not success else None}}
        metrics=VerificationMetrics()
        return {"passed":True,"checks":{"fixture":True},"failed_checks":[],"episodes":[e],
                "evaluation":{"verification_metrics":metrics.result(True) if c["verification"] else None},"max_action_replay_error":0.}

    def child(self,config,environment):
        config.validate();self.calls.append((getattr(config,"family",None),config.disturbance,config.disturbance_magnitude,config.seed,config.system))
        self.environments.append(environment.copy())
        directory=config.output/"fixture";directory.mkdir(parents=True)
        (directory/"raw.json").write_text(json.dumps({"seed":config.seed,"system":config.system}))
        return {"run_directory":str(directory)}

    def mocks(self,stack):
        self.calls=[];self.environments=[]
        stack.enter_context(patch.object(m5,"software_manifest",return_value=SOFTWARE))
        stack.enter_context(patch.object(m5,"launch_child",side_effect=self.child))
        stack.enter_context(patch.object(m5,"checked_trial",side_effect=self.fixture))
        for n in ("compare_pair","compare_recovery","compare_scheduled","compare_control"):
            stack.enter_context(patch.object(m5,n,return_value={"passed":True,"checks":{"fixture":True}}))
        stack.enter_context(redirect_stdout(io.StringIO()))

    def verify_archive(self,path):
        with tarfile.open(path) as bundle:
            index=json.load(bundle.extractfile("m5-attribution/archive_index.json"))
            self.assertEqual(len(bundle.getnames()),len(set(bundle.getnames())))
            self.assertEqual(set(bundle.getnames()),{i["path"] for i in index["files"]}|{"m5-attribution/archive_index.json"})
            for item in index["files"]:
                b=bundle.extractfile(item["path"]).read()
                self.assertEqual(len(b),item["bytes"]);self.assertEqual(hashlib.sha256(b).hexdigest(),item["sha256"])

    def test_960_slot_resume_archive_and_counterfactual_metrics(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            self.mocks(stack);root=Path(temp);output=root/"study";archive=root/"evidence.tar.gz"
            a=m5.run_sweep(output,archive,stop_after=4)
            self.assertEqual(a["state"],"paused");partial=Path(a["saved_archive"])
            self.verify_archive(partial);digest=hashlib.sha256(partial.read_bytes()).hexdigest()
            self.assertTrue(all(c["validated_curve_success_rate"] is None for c in a["cells"]))
            b=m5.run_sweep(output,archive,resume=True)
            self.assertEqual(b["state"],"passed")
            self.assertEqual(len(self.calls),960)
            self.assertEqual(len(b["cells"]),48)
            for group,n in m5.protocol()["comparison_counts"].items():self.assertEqual(len(b[group]),n)
            self.assertTrue(all(e==self.environments[0] for e in self.environments))
            self.assertTrue(all(c["excluded_seeds"]==[88] for c in b["cells"]))
            normal=next(p for p in b["paired_outcomes"] if p["point_id"]=="shift-normal")
            self.assertEqual(normal["v3"]["unnecessary_recovery_rate_on_baseline_success"],1.)
            self.assertEqual(normal["v3"]["regression_rate_on_baseline_success"],1.)
            self.assertEqual(normal["v2"]["mean_attempt_actions_per_eligible_episode"],0.)
            self.assertEqual(normal["mean_paired_extra_actions_v3_minus_v2"],100.)
            self.assertEqual(normal["success_rate_difference_v2_minus_v3"],1.)
            hard=next(p for p in b["paired_outcomes"] if p["point_id"]=="drop-200mm")
            self.assertEqual(hard["success_rate_difference_v2_minus_v3"],-1.)
            self.assertIsNone(hard["v3"]["unnecessary_recovery_rate_on_baseline_success"])
            self.assertEqual(hashlib.sha256(partial.read_bytes()).hexdigest(),digest)
            self.verify_archive(archive)
            with (output/"curve.csv").open() as f:self.assertEqual(len(list(csv.DictReader(f))),48)

    def test_resume_rejects_raw_environment_lock_and_retains_error_slots(self):
        import fcntl
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            self.mocks(stack);root=Path(temp);output=root/"study";archive=root/"evidence.tar.gz"
            with patch.object(m5,"launch_child",side_effect=RuntimeError("fixture error")):
                a=m5.run_sweep(output,archive,stop_after=1)
            b=m5.run_sweep(output,archive,resume=True,stop_after=3)
            self.assertEqual(b["episode_trials"][0],a["episode_trials"][0])
            self.assertEqual(self.calls[0][-1],"v1")
            self.assertTrue(all(p["success_rate_difference_v2_minus_v3"] is None for p in b["paired_outcomes"]))
            with patch.dict("os.environ",{"M5_ENV_CHANGE":"1"}):
                with self.assertRaisesRegex(ValueError,"environment"):m5.run_sweep(output,archive,resume=True)
            with (output/"runner.lock").open("a") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,"owns"):m5.run_sweep(output,archive,resume=True)
            raw=Path(b["episode_trials"][1]["run_directory"])/"raw.json";raw.write_text("tampered")
            with self.assertRaisesRegex(ValueError,"hashes"):m5.run_sweep(output,archive,resume=True)

    def test_explicit_family_subprocess_and_original_m3_dispatch(self):
        from types import SimpleNamespace
        from aether_cl.m5_process import run_v3_process
        with tempfile.TemporaryDirectory() as temp:
            config=V3Config(family="drop",seed=80,output=Path(temp)/"child")
            def wait():
                p=config.output/"fixture";p.mkdir()
                (p/"result.json").write_text(json.dumps({"state":"finished","run_directory":str(p)}))
                return 0
            with patch("aether_cl.m5_process.subprocess.Popen",return_value=SimpleNamespace(wait=wait)) as process:
                run_v3_process(config,{"M5_TEST":"1"})
                args,kwargs=process.call_args
                command=args[0]
                self.assertEqual(command[command.index("--family")+1],"drop")
                self.assertEqual(command[command.index("--system")+1],"v3")
                self.assertEqual(kwargs["env"],{"M5_TEST":"1"})
                self.assertTrue(kwargs["start_new_session"])
            with patch.object(m5,"run_in_process",return_value={"fixture":True}) as original:
                m5.launch_child(M3Config(system="v2"),{"M5_TEST":"1"})
                self.assertEqual(original.call_args.kwargs["module"],"aether_cl.m3")

    def test_schedule_protocol_guard_precedes_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);value=m5.protocol();value["v3_first_action_steps"]={"shift":129,"drop":184}
            p=root/"protocol.json";p.write_text(json.dumps(value))
            with patch.object(m5,"PROTOCOL_PATH",p):
                with self.assertRaisesRegex(ValueError,"preregistration"):
                    m5.run_sweep(root/"study",root/"evidence.tar.gz",run_fn=lambda _:self.fail("launched"))
            self.assertFalse((root/"study").exists())
            self.assertEqual(len(m5.plan(root)),960)
            self.assertEqual(m5.SEEDS,tuple(range(80,100)))


if __name__=="__main__":unittest.main()
