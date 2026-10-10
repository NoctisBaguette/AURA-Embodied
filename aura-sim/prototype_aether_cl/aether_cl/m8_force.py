"""M8 development force adapter: engine force only, no controller/scorer change."""

import hashlib
from importlib.metadata import distribution, version
import inspect
import json
import math
from pathlib import Path
import sys

import numpy as np

from .runtime import json_value, software_manifest
from .m6_policy import INJECTION_STEP, FixedPlacement
from .m6_task import SETTINGS, geometry
from .verification import single_bool

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "docs/research/experiments/evidence/AETHER_CL_M8_Installed_Physics_Inspection.json"
DEVELOPMENT_SEEDS = (100, 101)
WINDOW_SUBSTEPS = 5
GRAVITY_M_S2 = 9.81
MODEL_DRIFTS_M = (0., .01, .04, .08, .12, .20)
SOURCE_FILES = ("m8_force.py", "m8_force_commission.py")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def receipt():
    return json.loads(RECEIPT.read_text())


def candidate_points():
    """Coulomb-sliding estimates choose development forces, never set state.

    With pulse duration T and post-pulse velocity v, estimated total drift is
    d=v*T/2+v*v/(2*mu*g). This is not a promised physical outcome.
    """
    r = receipt()
    mass = r["cube"]["physical_properties"]["values"]["mass"]
    mu = r["cube"]["collision_shapes"][0]["material"]["values"]["dynamic_friction"]
    duration = WINDOW_SUBSTEPS / r["physics_frequencies"]["sim_freq"]
    result = []
    for distance in MODEL_DRIFTS_M:
        velocity = (-mu * GRAVITY_M_S2 * duration + math.sqrt(
            (mu * GRAVITY_M_S2 * duration)**2 + 8 * mu * GRAVITY_M_S2 * distance)) / 2
        force = 0. if distance == 0 else mass * (mu * GRAVITY_M_S2 + velocity / duration)
        encoded = float(np.float32(force))
        result.append({"point_id": "normal" if not distance else f"model-drift-{round(distance*1000):03d}mm",
            "estimated_drift_m": distance, "command_force_y_n": encoded,
            "command_force_world_n": [0., encoded, 0.], "torque_world_nm": [0., 0., 0.],
            "planned_nominal_duration_s": duration,
            "planned_command_integral_y_ns": encoded * WINDOW_SUBSTEPS * r["actual_timestep_s"],
            "prediction_is_not_actor_state_command": True})
    return result


def preflight(expected_head):
    r = receipt()
    if not set(DEVELOPMENT_SEEDS).issubset(r["recorded_reset_seeds"]):
        raise ValueError("Development seeds must appear in the independently inspected retained history")
    if sys.version_info[:2] != (3, 10) or {k: version(k) for k in r["packages"]} != r["packages"]:
        raise ValueError("Use the unchanged inspected Python3.10 aether-cl environment")
    current = {n: sha256(Path(__file__).parent / n) for n in r["accepted_placement_sources_sha256"]}
    if current != r["accepted_placement_sources_sha256"]:
        raise ValueError("Accepted placement sources changed")
    pkg = Path(distribution("mani_skill").locate_file("mani_skill"))
    sources = {**r["inherited_installed_sources_sha256"], **r["installed_source_sha256"]}
    if any(sha256(pkg / n) != h for n, h in sources.items()):
        raise ValueError("Inspected installed ManiSkill source bytes changed")
    if any(sha256(pkg / "assets" / n) != h for n, h in r["inherited_asset_sha256"].items()):
        raise ValueError("Native Panda assets changed")
    sapien_pkg = Path(distribution("sapien").locate_file("sapien"))
    if any(sha256(sapien_pkg / b["path"]) != b["sha256"] for b in r["sapien_native_binaries"]):
        raise ValueError("Inspected SAPIEN native binaries changed")
    software = software_manifest()
    if software["git_commit"] != expected_head or software["git_dirty"]:
        raise ValueError("Require the requested clean development Git revision")
    return {"software": software, "receipt_sha256": sha256(RECEIPT),
            "development_sources_sha256": {n: sha256(Path(__file__).with_name(n)) for n in SOURCE_FILES},
            "installed_sources_sha256": sources,
            "accepted_placement_sources_sha256": current,
            "sapien_binaries": r["sapien_native_binaries"]}


def release_precondition(observation, info, phase):
    g = geometry(observation)
    contact = np.asarray(info["cube_table_contact_force_world_n"]).reshape(3)
    return bool(phase == "retract" and g["released_geometry"] and g["supported_geometry"]
        and not single_bool(info["is_grasped"], "is_grasped") and contact[2] >= SETTINGS.minimum_support_force_n)


def verify_body(actor, expected):
    bodies = actor._bodies
    if len(bodies) != 1:
        raise ValueError("Require exactly one inspected rigid body")
    body = bodies[0]
    values = expected["physical_properties"]["values"]
    for n in ("mass", "kinematic", "disable_gravity", "linear_damping", "angular_damping"):
        if getattr(body, n) != values[n]:
            raise ValueError("Native rigid-body property changed: " + n)
    if len(body.collision_shapes) != len(expected["collision_shapes"]):
        raise ValueError("Native collision shape count changed")
    for shape, record in zip(body.collision_shapes, expected["collision_shapes"]):
        if json_value(shape.half_size) != record["geometry"]["values"]["half_size"]:
            raise ValueError("Native collision shape dimensions changed")
        for n, v in record["material"]["values"].items():
            if getattr(shape.physical_material, n) != v:
                raise ValueError("Native material changed: " + n)
    return body


class ForceTrace:
    """Attach additive force immediately before five real physics steps.

    Only mode='force' is used. No impulse/velocity-change setter or pose write
    exists here. Reads and hook wrappers are checked against a no-hook control.
    """

    def __init__(self, env, point, log):
        self.base, self.point, self.log = env.unwrapped, point, log
        r = receipt()
        if (self.base.gpu_sim_enabled or self.base.num_envs != 1 or self.base.sim_freq != 100
                or self.base.control_freq != 20 or self.base._sim_steps_per_control != 5
                or self.base.scene.px.timestep != r["actual_timestep_s"]):
            raise ValueError("Inspected one-environment CPU100Hz/20Hz physics required")
        if not np.allclose(self.base.sim_config.scene_config.gravity, [0, 0, -GRAVITY_M_S2], rtol=0, atol=1e-6):
            raise ValueError("Native gravity differs from the inspected installed source model")
        self.body = verify_body(self.base.cube, r["cube"])
        verify_body(self.base.table_scene.table, r["table"])
        if inspect.getdoc(self.body.add_force_torque) != r["force_binding_docs"]["add_force_torque"]:
            raise ValueError("Installed force binding differs from inspection")
        self.original_before = self.base._before_simulation_step
        self.original_after = self.base._after_simulation_step
        for name, method in (("_before_simulation_step", self.original_before), ("_after_simulation_step", self.original_after)):
            if inspect.getsource(method) != r["physics_hooks"][name]["source"]:
                raise ValueError("Task physics hook differs from inspection")
        self.had_before = "_before_simulation_step" in self.base.__dict__
        self.had_after = "_after_simulation_step" in self.base.__dict__
        self.base._before_simulation_step = self.before
        self.base._after_simulation_step = self.after
        self.step, self.records, self.pending = 0, [], None
        self.precondition = False
        self.total_calls = 0

    def state(self):
        b = self.base
        return json_value({"cube_pose_world": b.cube.pose.raw_pose,
            "cube_linear_velocity_m_s": b.cube.linear_velocity,
            "cube_angular_velocity_rad_s": b.cube.angular_velocity,
            "cube_table_contact_force_world_n": b.scene.get_pairwise_contact_forces(b.cube, b.table_scene.table),
            "cube_finger1_contact_force_world_n": b.scene.get_pairwise_contact_forces(b.cube, b.agent.finger1_link),
            "cube_finger2_contact_force_world_n": b.scene.get_pairwise_contact_forces(b.cube, b.agent.finger2_link)})

    def begin(self, step, observation, info, phase):
        if self.pending is not None:
            raise ValueError("Incomplete previous physics sample")
        self.step, self.records = step, []
        self.precondition = release_precondition(observation, info, phase) if step == INJECTION_STEP else False
        self.intent = {"step": step, "nominal_phase": phase,
            "requested_force_world_n": self.point["command_force_world_n"],
            "injection_boundary": step == INJECTION_STEP,
            "release_support_precondition": self.precondition,
            "planned_substeps": WINDOW_SUBSTEPS if step == INJECTION_STEP else 0,
            "timing": "after_action_computation_before_each_external_physics_step",
            "mode": "force", "force_api": "PhysxRigidBodyComponent.add_force_torque"}

    def before(self):
        result = self.original_before()
        substep = len(self.records) + 1
        if self.step < 1 or self.pending is not None or substep > 5:
            raise ValueError("Unexpected external physics-step sequence")
        prior = self.state()
        apply = bool(self.step == INJECTION_STEP and self.precondition and self.point["command_force_y_n"] != 0)
        force = np.asarray(self.point["command_force_world_n"] if apply else [0., 0., 0.], dtype=np.float32)
        self.pending = {"substep": substep, "before": prior, "force_world_n": force.tolist(),
            "torque_world_nm": [0., 0., 0.], "force_call_executed": apply,
            "dt_s": float(self.base.scene.px.timestep)}
        if apply:
            self.body.add_force_torque(force=force, torque=np.zeros(3, dtype=np.float32), mode="force")
            self.total_calls += 1
            self.pending["immediately_after_force_call"] = self.state()
            for n in ("cube_pose_world", "cube_linear_velocity_m_s", "cube_angular_velocity_rad_s"):
                if prior[n] != self.pending["immediately_after_force_call"][n]:
                    self.log({"event": "force_call_unexpected_state_change", **self.pending})
                    raise ValueError("Force call changed pose/velocity before physics advance; retain and review")
        else:
            self.pending["immediately_after_force_call"] = prior
        return result

    def after(self):
        result = self.original_after()
        if self.pending is None:
            raise ValueError("Physics post-hook has no preceding pre-hook")
        self.pending["after_physics"] = self.state()
        self.records.append(self.pending)
        self.pending = None
        return result

    def end(self):
        if self.pending is not None or len(self.records) != 5:
            raise ValueError("Require exactly five complete external physics samples per action")
        record = {"event": "physics_action", "step": self.step, "intent": self.intent, "substeps": self.records}
        self.log(record)
        return record

    def close(self):
        for name, had, original in (("_before_simulation_step", self.had_before, self.original_before),
                                     ("_after_simulation_step", self.had_after, self.original_after)):
            if had:
                setattr(self.base, name, original)
            else:
                delattr(self.base, name)


class ForceEnvironment:
    """Proxy the unchanged Baseline runner; controller actions pass through."""

    def __init__(self, env):
        self.env, self.trace, self.step_number = env, None, 0
        self.observation = self.info = self.policy = None

    def __getattr__(self, name):
        return getattr(self.env, name)

    def step(self, action):
        self.step_number += 1
        phase = self.policy.phase(self.step_number - 1)[0]
        self.trace.begin(self.step_number, self.observation, self.info, phase)
        result = self.env.step(action)
        self.trace.end()
        return result

    def close(self):
        if self.trace is not None:
            self.trace.close()
        self.env.close()
