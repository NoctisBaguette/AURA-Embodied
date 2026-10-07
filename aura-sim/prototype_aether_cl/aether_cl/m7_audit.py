"""Read-only development replay, raw physical endpoint reconstruction and strict pairs."""

from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from .policies import pose_rotation, vector
from .runtime import json_value
from .m7_task import SETTINGS, InsertionReference, InsertionVerifier, task_manifest
from .m7_policy import FixedInsertion, InsertionRecovery, INJECTION_STEP, MAX_STEPS
from .m7_runtime import M7DevelopmentConfig, perturb_waypoints


def equal_replay(actual, expected, path="root"):
    """Derived scalar diagnostics only; strict physical pairs are separate."""
    actual, expected = json_value(actual), json_value(expected)
    if type(actual) is not type(expected):
        raise ValueError("Replay type mismatch " + path)
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError("Replay keys differ " + path)
        for key in expected:
            equal_replay(actual[key], expected[key], path + "." + key)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError("Replay length differs " + path)
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal_replay(a, b, path + f"[{i}]")
    elif isinstance(expected, float):
        if not np.isclose(actual, expected, atol=1e-10, rtol=0):
            raise ValueError("Derived replay scalar differs " + path)
    elif actual != expected:
        raise ValueError("Replay differs " + path)


def independent_relation(observation):
    """Reconstruct the insertion relation from raw rigid-body poses and geometry.

    Does not call the controller's geometry function or trust built-in success.
    The clipped cuboid vertex/edge construction checks the entire inserted
    volume, including the channel entry plane, rather than only the peg head.
    """
    e = observation["extra"]
    peg, hole = vector(e["peg_pose"], 7, "peg"), vector(e["box_hole_pose"], 7, "hole")
    size = vector(e["peg_half_size"], 3, "half")
    radius = float(np.asarray(e["box_hole_radius"]).reshape(-1)[0])
    relative_rotation = pose_rotation(hole).T @ pose_rotation(peg)
    center = pose_rotation(hole).T @ (peg[:3] - hole[:3])
    corners = {(x, y, z): center + relative_rotation @ (np.array([x, y, z]) * size)
               for x, y, z in product((-1, 1), repeat=3)}
    contained = [p for p in corners.values() if abs(p[0]) <= size[0]]
    for key, a in corners.items():
        for axis in range(3):
            other = list(key); other[axis] *= -1; other = tuple(other)
            if key >= other:
                continue
            b = corners[other]
            for plane in (-size[0], size[0]):
                if min(a[0], b[0]) < plane < max(a[0], b[0]):
                    contained.append(a + (b - a) * ((plane - a[0]) / (b[0] - a[0])))
    margin = radius - max(max(abs(p[1]), abs(p[2])) for p in contained) if contained else None
    head = center + relative_rotation[:, 0] * size[0]
    depth = float(head[0] + size[0])
    orientations = [Rotation.from_matrix(relative_rotation @ Rotation.from_rotvec([k * np.pi / 2, 0, 0]).as_matrix().T).magnitude() for k in range(4)]
    relation = (.8 * size[0] <= depth <= 1.2 * size[0] and min(orientations) <= .05 and margin is not None and margin >= -.0002)
    return {"depth_m": depth, "channel_margin_m": None if margin is None else float(margin),
            "relation_ready": bool(relation), "position": center, "rotation": relative_rotation}


def independent_endpoint(observation, info, previous, acquired, max_lift):
    """Raw-force acquisition, independent geometry and legacy velocity shadow."""
    data = independent_relation(observation)
    e = observation["extra"]
    peg = vector(e["peg_pose"], 7, "peg")
    finger_flags = []
    for side in ("left", "right"):
        force = vector(info[side + "_finger_peg_force_world_n"], 3, "force")
        opening = vector(info[side + "_finger_open_direction_world"], 3, "direction")
        norm = float(np.linalg.norm(force)); direction_norm = float(np.linalg.norm(opening))
        finger_flags.append(norm >= .5 and direction_norm > 0 and np.dot(force, opening) / (max(norm, 1e-12) * direction_norm) >= np.cos(np.deg2rad(85)))
    contact = bool(all(finger_flags))
    if contact != info["contact_grasped"]:
        raise ValueError("Raw finger forces disagree with recorded contact acquisition")
    delta = np.linalg.norm(peg[:3] - previous[:3])
    turn = Rotation.from_matrix(pose_rotation(peg) @ pose_rotation(previous).T).magnitude()
    stable = (np.linalg.norm(vector(e["peg_linear_velocity"], 3, "linear")) <= .01 and
              np.linalg.norm(vector(e["peg_angular_velocity"], 3, "angular")) <= .15 and delta <= .0005 and turn <= .01)
    return {"depth_m": data["depth_m"], "channel_margin_m": data["channel_margin_m"],
            "relation_ready": data["relation_ready"], "stable_frame": bool(stable), "contact_grasped": contact,
            "ready": bool(acquired and max_lift >= .03 and data["relation_ready"] and stable)}


class IndependentPoseStability:
    """Reconstruct pose-window verdicts without calling task/controller stability."""

    def __init__(self, observation):
        data = independent_relation(observation)
        self.previous = (data["position"], Rotation.from_matrix(data["rotation"]))
        self.control_previous = self.previous
        self.frames = []

    def observe(self, observation, samples):
        if samples is None or len(samples) != 5:
            raise ValueError("Independent complete physics samples required")
        points, rotations, relations, speeds, turns = [], [], [], [], []
        for sample in samples:
            raw = {**observation, "extra": {**observation["extra"],
                "peg_pose": sample["peg_pose"], "box_hole_pose": sample["hole_pose"]}}
            data = independent_relation(raw)
            p, r = data["position"], Rotation.from_matrix(data["rotation"])
            speeds.append(float(np.linalg.norm(p - self.previous[0]) / .01))
            turns.append(float((r * self.previous[1].inv()).magnitude() / .01))
            points.append(p); rotations.append(r); relations.append(data["relation_ready"])
            self.previous = (p, r)
        distance = float(np.linalg.norm(self.previous[0] - self.control_previous[0]))
        angle = float((self.previous[1] * self.control_previous[1].inv()).magnitude())
        self.control_previous = self.previous
        stable = max(speeds) <= .01 and max(turns) <= .15 and distance <= .0005 and angle <= .01
        self.frames = (self.frames + [(points, rotations, bool(stable), all(relations))])[-10:]
        xyz = np.asarray([p for frame in self.frames for p in frame[0]])
        qs = np.asarray([r.as_quat() for frame in self.frames for r in frame[1]])
        diameter = float(np.sqrt(np.sum(np.square(xyz[:, None] - xyz[None, :]), axis=2)).max())
        # Each rotation has two quaternion representatives; use the shorter chord.
        chords = np.minimum(np.sqrt(np.sum(np.square(qs[:, None] - qs[None, :]), axis=2)),
                            np.sqrt(np.sum(np.square(qs[:, None] + qs[None, :]), axis=2)))
        angular_diameter = float(4 * np.arcsin(np.clip(chords.max() / 2, 0, 1)))
        ready = (len(self.frames) == 10 and all(frame[2] and frame[3] for frame in self.frames)
                 and diameter <= .0005 and angular_diameter <= .01)
        return {"stable_frame": bool(stable), "relation_all_substeps": all(relations),
            "maximum_substep_pose_speed_m_s": max(speeds),
            "maximum_substep_pose_angular_speed_rad_s": max(turns),
            "relative_frame_translation_m": distance, "relative_frame_rotation_rad": angle,
            "window_control_observations": len(self.frames), "window_physics_samples": len(xyz),
            "window_translation_diameter_m": diameter, "window_rotation_diameter_rad": angular_diameter,
            "window_ready": bool(ready)}


def read_episode(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    result = json.loads((directory / "result.json").read_text())
    with (directory / "events.jsonl").open(encoding="utf-8") as stream:
        events = [json.loads(line) for line in stream]
    resets = [e for e in events if e["event"] == "reset"]
    if len(resets) != 1 or resets[0]["seed"] != manifest["config"]["seed"]:
        raise ValueError("One exact seeded reset required")
    steps = [e for e in events if e["event"] == "step"]
    return manifest, result, resets[0], steps, events


def check_substeps(manifest, steps, events):
    config = manifest.get("physics_substep_trace", {"enabled": False})
    traces = [e for e in events if e["event"] == "physics_substeps"]
    if not config["enabled"]:
        raise ValueError("Complete physics sampling required for current pose-stability contract")
    if (config.get("selection") != "every_action_all_external_physics_steps"
            or config["sim_freq_hz"] != 100 or config["sim_steps_per_control"] != 5):
        raise ValueError("Physics sampling contract differs")
    lookup = {e["step"]: e for e in traces}
    required = {e["step"] for e in steps}
    if len(lookup) != len(traces) or set(lookup) != required:
        raise ValueError("Physics substep selection incomplete or duplicated")
    count = 0
    for event in steps:
        if event["step"] not in required:
            continue
        samples = lookup[event["step"]]["samples"]
        if len(samples) != config["sim_steps_per_control"]:
            raise ValueError("Physics substep count differs")
        for n, sample in enumerate(samples, 1):
            if sample["substep"] != n:
                raise ValueError("Physics substeps nonconsecutive")
            for key, size in (("peg_pose", 7), ("hole_pose", 7), ("linear_velocity", 3), ("angular_velocity", 3)):
                vector(sample[key], size, key)
        extra = event["observation"]["extra"]
        for key, raw_key, size in (("peg_pose", "peg_pose", 7),
                                   ("hole_pose", "box_hole_pose", 7),
                                   ("linear_velocity", "peg_linear_velocity", 3),
                                   ("angular_velocity", "peg_angular_velocity", 3)):
            if not np.array_equal(vector(samples[-1][key], size, key), vector(extra[raw_key], size, raw_key)):
                raise ValueError("Final physics substep differs from raw observation")
        count += len(samples)
    return count


def replay(directory):
    manifest, result, reset, steps, events = read_episode(directory)
    if result["state"] != "finished" or result["steps"] != MAX_STEPS or len(steps) != MAX_STEPS:
        raise ValueError("Development episode not complete; retain failed evidence")
    substep_count = check_substeps(manifest, steps, events)
    config = M7DevelopmentConfig(**{**manifest["config"], "output": Path(manifest["config"]["output"])})
    config.validate()
    nominal = FixedInsertion(reset["observation"], manifest["robot_base_pose"])
    reference = InsertionReference(reset["observation"])
    verifier = InsertionVerifier(reset["observation"]) if config.system != "baseline" else None
    recovery = InsertionRecovery(nominal) if config.system == "v2" else None
    independent_motion = IndependentPoseStability(reset["observation"])
    samples_by_step = {e["step"]: e["samples"] for e in events if e["event"] == "physics_substeps"}
    equal_replay(manifest["nominal"], nominal.manifest())
    equal_replay(manifest["task_contract"], task_manifest())
    equal_replay(manifest["recovery"], recovery.manifest() if recovery else None)
    observation, info = reset["observation"], reset["info"]
    verdict, truth = {"status": "waiting" if verifier else "disabled", "failure": None}, {}
    injected = [e["disturbance"] for e in events if e["event"] == "disturbance_considered"]
    if len(injected) != 1:
        raise ValueError("One retained perturbation decision required")
    maximum_action_error = path = 0.
    previous_tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp")[:3]
    acquired, max_lift, stable_count, legacy_count = False, 0., 0, 0
    initial_z = vector(observation["extra"]["peg_pose"], 7, "peg")[2]
    nominal_complete = False
    first_contact = first_depth = None
    pre_insert = None
    for step, event in enumerate(steps, 1):
        if event["step"] != step:
            raise ValueError("Nonconsecutive native steps")
        if step == INJECTION_STEP:
            injection = perturb_waypoints(nominal, observation, truth, info, config.offset_clearance_ratio,
                                          bool(recovery and recovery.state != "nominal"))
            equal_replay(injected[0], injection)
        if step == 491:
            pre_insert = {"step": step - 1, "reference": truth, "recovery_state": recovery.snapshot() if recovery else None,
                          "peg_box_contact_force_world_n": info["peg_box_contact_force_world_n"]}
        action, decision = recovery.action(observation, step, verdict) if recovery else nominal.action(observation, step - 1)
        expected = action[0] if manifest["action_space_shape"] == [7] else action
        if np.asarray(event["action"]).shape != expected.shape:
            raise ValueError("Action shape changed")
        error = float(np.max(np.abs(np.asarray(event["action"]) - expected)))
        maximum_action_error = max(maximum_action_error, error)
        if error > 3e-7:
            raise ValueError("Insertion controller action replay differs")
        equal_replay(event["controller_decision"], decision)
        previous_pose = vector(observation["extra"]["peg_pose"], 7, "previous")
        observation, info = event["observation"], event["info"]
        samples = samples_by_step[step]
        truth = reference.observe(observation, info, step, decision, final=step == MAX_STEPS, physics_samples=samples)
        equal_replay(event["reference"], truth)
        if verifier:
            verdict = verifier.observe(observation, step, decision, final=step == MAX_STEPS, physics_samples=samples)
        equal_replay(event["verification"], verdict)
        if recovery:
            recovery.observe(observation, physics_samples=samples)
        snapshot = recovery.snapshot() if recovery else {"state": "disabled", "attempts": 0}
        equal_replay(event["recovery"], snapshot)
        current_lift = float(vector(observation["extra"]["peg_pose"], 7, "peg")[2] - initial_z)
        acquired |= info["contact_grasped"] and current_lift >= SETTINGS.minimum_lift_m
        max_lift = max(max_lift, current_lift)
        endpoint = independent_endpoint(observation, info, previous_pose, acquired, max_lift)
        for name in ("depth_m", "channel_margin_m", "relation_ready"):
            equal_replay(truth[name], endpoint[name])
        equal_replay(truth["legacy_velocity_stable_frame"], endpoint["stable_frame"])
        legacy_count = legacy_count + 1 if endpoint["ready"] else 0
        equal_replay(truth["legacy_velocity_stable_steps"], legacy_count)
        equal_replay(truth["legacy_velocity_task_success"], legacy_count >= 10)
        raw_motion = independent_motion.observe(observation, samples)
        equal_replay(truth["pose_stability"], raw_motion)
        equal_replay(truth["stable_frame"], raw_motion["stable_frame"])
        pose_ready = acquired and endpoint["relation_ready"] and raw_motion["stable_frame"] and raw_motion["relation_all_substeps"]
        stable_count = stable_count + 1 if pose_ready else 0
        equal_replay(truth["stable_steps"], stable_count)
        if truth["task_success"] != bool(stable_count >= 10 and raw_motion["window_ready"]):
            raise ValueError("Independent physical endpoint/stability disagreement")
        tcp = vector(observation["extra"]["tcp_pose"], 7, "tcp")[:3]
        path += float(np.linalg.norm(tcp - previous_tcp)); previous_tcp = tcp
        nominal_complete |= not decision["phase"].startswith("recovery_") and decision["schedule_complete"]
        if first_contact is None and np.linalg.norm(vector(info["peg_box_contact_force_world_n"], 3, "force")) > .05:
            first_contact = step
        if first_depth is None and truth["depth_m"] > 0:
            first_depth = step
    snapshot = recovery.snapshot() if recovery else {"state": "disabled", "attempts": 0, "action_steps": 0, "observed_tcp_path_m": 0., "completed_stages": []}
    expected_result = {"task_success_at_end": truth["task_success"], "final_reference": truth,
        "built_in_success_at_end": bool(np.asarray(info["success"]).reshape(-1)[0]),
        "final_verification": verdict, "first_reference_failure": reference.first_failure,
        "first_detected_failure": verifier.first_failure if verifier else None,
        "first_task_success_step": reference.first_success_step, "recovery": snapshot,
        "total_observed_tcp_path_m": path, "controller_complete": nominal_complete if not snapshot["attempts"] else snapshot["state"] == "attempt_complete",
        "injection": injection, "pre_insert_state": pre_insert,
        "first_peg_box_contact_step": first_contact, "first_positive_depth_step": first_depth}
    for key, value in expected_result.items():
        equal_replay(result[key], value, "result." + key)
    return {"passed": True, "steps": len(steps), "maximum_action_replay_error": maximum_action_error,
            "physics_substep_samples": substep_count,
            "raw_endpoint_reconstructions": len(steps), "action_replay_bound": 3e-7,
            "derived_scalar_replay_bound": 1e-10, "physical_pair_tolerance": "exact"}


def compare(left, right, stop=None):
    lm, lr, lreset, ls, le = read_episode(left)
    rm, rr, rreset, rs, re = read_episode(right)
    for key in ("observation", "info", "seed"):
        if lreset[key] != rreset[key]:
            raise ValueError("Matched reset differs: " + key)
    for key in ("software", "installed_sources_sha256", "installed_assets_sha256", "startup_environment_sha256", "robot_base_pose", "episode_geometry", "task_contract", "nominal"):
        if lm[key] != rm[key]:
            raise ValueError("Matched startup differs: " + key)
    if lm["config"]["seed"] != rm["config"]["seed"]:
        raise ValueError("Matched seeds differ")
    if lm.get("physics_substep_trace") != rm.get("physics_substep_trace"):
        raise ValueError("Matched physics substep settings differ")
    bound = MAX_STEPS if stop is None else stop
    if len(ls) < bound or len(rs) < bound:
        raise ValueError("Matched prefix incomplete")
    for a, b in zip(ls[:bound], rs[:bound]):
        for key in ("step", "observation", "info", "reward", "action", "terminated", "truncated", "reference", "controller_decision"):
            if a[key] != b[key]:
                raise ValueError(f"Strict physical/action/reference pair differs at step{a['step']}: {key}")
    ltrace = [{k: e[k] for k in ("step", "samples")} for e in le if e["event"] == "physics_substeps" and e["step"] <= bound]
    rtrace = [{k: e[k] for k in ("step", "samples")} for e in re if e["event"] == "physics_substeps" and e["step"] <= bound]
    if ltrace != rtrace:
        raise ValueError("Strict matched physics substeps differ")
    return {"passed": True, "exact_steps": bound}


def suite_pairs(trials, root, include_controls=False):
    root = Path(root)
    lookup = {(t["ratio"], t["seed"], t["system"]): t for t in trials if t.get("run_directory")}
    pairs = []
    for ratio, seed in sorted({(t["ratio"], t["seed"]) for t in trials}):
        for left, right in (("baseline", "v1"), ("v1", "v2")):
            a, b = lookup.get((ratio, seed, left)), lookup.get((ratio, seed, right))
            if not a or not b:
                continue
            first_action = b["result"]["recovery"].get("first_action_step") if right == "v2" else None
            pairs.append({"ratio": ratio, "seed": seed, "systems": [left, right],
                          **compare(root / a["run_directory"], root / b["run_directory"], first_action - 1 if first_action else None)})
        if include_controls and ratio != 0:
            a, b = lookup.get((0., seed, "baseline")), lookup.get((ratio, seed, "baseline"))
            if a and b:
                pairs.append({"ratio": ratio, "seed": seed, "systems": ["normal_baseline", "disturbed_baseline"],
                    **compare(root / a["run_directory"], root / b["run_directory"], INJECTION_STEP - 1)})
    return pairs
