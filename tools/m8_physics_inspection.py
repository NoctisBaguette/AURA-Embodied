"""M8 installed-force inspection; known-seed reset, no rollout or disturbance."""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, version
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import traceback


AUTHORITY = "4d477da2a583717b773b3a1c746996a3c2127e40"
ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "aura-sim/prototype_aether_cl"
DEVELOPMENT_SEED = 100
PREFERRED_SEEDS = tuple(range(160, 180))
ACCEPTED_SOURCES = {
    "runtime.py": "471a5d26a384c6997f0d5a6713d5595bc07dcfe64e0bc2a19b13c786d9449c07",
    "policies.py": "c4e16450ad64ad8683db69d7a166720e411e5e97c8c1def3471b1b04ced04f29",
    "verification.py": "472073de5db587de20c2185b324181f169a7bc0e52cd5706aef7506f928f83a7",
    "m6_task.py": "e63aff47dbc8f0c270f02c6a0d6bfa46970f96d9da149b18990d76eba4f6b62c",
    "m6_policy.py": "e4b1d7ff5f74b9008c6f170f62f6da0a565873fb9b61cd3dbf798706ad590d4c",
    "m6_runtime.py": "dd1c26a6299fc1c82fc0e30585f33b905dddecea3e4e6ecf88cf775389473ff7",
    "m6r_policy.py": "dd2628631641e500fe593155453b5c75408faf2f34c76ea761f057455e4e8981",
    "m6r_runtime.py": "679faec4707f7d4baed7091f2069ecd18b5a905ef3197b2fe101da3a218f6ad0",
}
SOURCE_PATHS = (
    "envs/sapien_env.py", "envs/scene.py", "envs/tasks/tabletop/pick_cube.py",
    "utils/structs/actor.py", "utils/structs/pose.py", "utils/structs/types.py",
    "utils/building/actor_builder.py", "utils/building/actors/common.py",
    "utils/scene_builder/table/scene_builder.py", "agents/base_agent.py",
    "agents/controllers/pd_ee_pose.py", "agents/robots/panda/panda.py",
)
PHYSICAL_WORDS = re.compile(r"force|impulse", re.I)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_record(path, root):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(root)), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "source": raw.decode("utf-8")}


def inspect_history(root, progress=None):
    """Read retained reset records, including stopped/failed runs; never reset."""
    if not root.is_dir():
        raise ValueError("Native runs history is missing")
    observed, witnesses, files_checked, reset_records = set(), {}, 0, 0
    digest = hashlib.sha256()
    for path in sorted(root.rglob("events.jsonl")):
        files_checked += 1
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if '"reset"' not in line and '"controller_reset"' not in line:
                    continue
                record = json.loads(line)
                if record.get("event") not in ("reset", "controller_reset"):
                    continue
                seed = record.get("seed")
                if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
                    raise ValueError(f"Missing/invalid recorded reset seed: {path}:{line_number}")
                observed.add(seed)
                witnesses.setdefault(seed, {"path": str(path.relative_to(root)), "line": line_number})
                reset_records += 1
                identity = {"file": str(path.relative_to(root)), "line": line_number,
                            "event": record["event"], "seed": seed}
                digest.update((json.dumps(identity, sort_keys=True) + "\n").encode())
        if progress and files_checked % 100 == 0:
            progress(f"History: {files_checked} event files, {reset_records} reset records")
    if not files_checked or not observed:
        raise ValueError("No retained native reset evidence; cannot establish seed provenance")
    if DEVELOPMENT_SEED not in observed:
        raise ValueError("Development seed100 is not demonstrated already observed; no reset authorized")
    proposed = PREFERRED_SEEDS[0]
    while set(range(proposed, proposed + 20)) & observed:
        proposed += 1
    return {"root": str(root), "event_files_checked": files_checked, "reset_records": reset_records,
            "reset_index_sha256": digest.hexdigest(), "recorded_reset_seeds": sorted(observed),
            "preferred_seeds": list(PREFERRED_SEEDS),
            "preferred_overlap": sorted(set(PREFERRED_SEEDS) & observed),
            "first_unused_contiguous20_from160": list(range(proposed, proposed + 20)),
            "development_seed100_witness": witnesses[DEVELOPMENT_SEED],
            "scope": "retained_native_history_not_unreported_or_deleted_runs",
            "selection_frozen": False, "fresh_entry_must_recheck": True}


def constructor_reset_seeds(source):
    """Identify the installed BaseEnv constructor's explicit initialization reset.

    The inspected source bytes are independently pinned to the earlier native
    installation. Reject an unresolved constructor seed before creating an env.
    Constructor initialization is distinct from the explicit development reset.
    """
    tree = ast.parse(source)
    base = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BaseEnv")
    init = next(n for n in base.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    seeds = []
    known_vector_seed = ast.parse("[2022 + i for i in range(self.num_envs)]", mode="eval").body
    for call in ast.walk(init):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id == "self"
                and call.func.attr == "reset"):
            continue
        node = next((kw.value for kw in call.keywords if kw.arg == "seed"), None)
        if node is not None and ast.dump(node) == ast.dump(known_vector_seed):
            # build_env fixes num_envs=1; the standard vector initialization
            # therefore resets only2022, never a preferred M8 scene.
            seeds.append(2022)
            continue
        if (not isinstance(node, ast.Constant) or not isinstance(node.value, int)
                or isinstance(node.value, bool) or node.value not in (100, 2022)):
            raise ValueError("Unreviewed BaseEnv initialization reset seed; stop before environment creation")
        seeds.append(node.value)
    return seeds


def interface(cls):
    """Read public descriptors/docstrings without invoking physics methods."""
    members = {}
    for name in sorted(n for n in dir(cls) if not n.startswith("_")):
        member = inspect.getattr_static(cls, name)
        try:
            signature = str(inspect.signature(member))
        except (TypeError, ValueError):
            signature = None
        members[name] = {"kind": type(member).__name__, "signature": signature,
                         "doc": inspect.getdoc(member)}
    return {"class": f"{cls.__module__}.{cls.__qualname__}", "doc": inspect.getdoc(cls),
            "members": members,
            "force_or_impulse_names": [n for n in members if PHYSICAL_WORDS.search(n)]}


def properties(obj, names, encode):
    values, unavailable = {}, {}
    for name in names:
        try:
            value = getattr(obj, name)
            if hasattr(value, "p") and hasattr(value, "q"):
                value = {"p": value.p, "q": value.q}
            values[name] = encode(value)
        except Exception as error:
            unavailable[name] = f"{type(error).__name__}: {error}"
    return {"values": values, "unavailable": unavailable}


def actor_record(actor, encode):
    entities = list(getattr(actor, "_objs", []))
    bodies = list(getattr(actor, "_bodies", []))
    retrieval = []
    if not bodies:
        for entity in entities:
            try:
                components = entity.get_components()
            except AttributeError:
                components = entity.components
            for component in components:
                retrieval.append(type(component).__name__)
                if "PhysxRigid" in type(component).__name__:
                    bodies.append(component)
    records = []
    for body in bodies:
        physical = properties(body, ("mass", "inertia", "cmass_local_pose", "kinematic",
            "disable_gravity", "linear_damping", "angular_damping", "max_linear_velocity",
            "max_angular_velocity", "linear_velocity", "angular_velocity"), encode)
        shapes = []
        for shape in getattr(body, "collision_shapes", []):
            try:
                material = shape.physical_material
            except AttributeError:
                getter = getattr(shape, "get_physical_material", None)
                material = getter() if getter is not None else None
            shapes.append({"class": type(shape).__name__,
                "geometry": properties(shape, ("half_size", "local_pose", "density", "collision_groups"), encode),
                "material": properties(material, ("static_friction", "dynamic_friction", "restitution"), encode)
                    if material is not None else None})
        records.append({"interface": interface(type(body)), "physical_properties": physical,
                        "collision_shapes": shapes})
    return {"actor_class": type(actor).__name__, "name": getattr(actor, "name", None),
            "actor_public_names": sorted(n for n in dir(type(actor)) if not n.startswith("_")),
            "pose_world": encode(actor.pose.raw_pose), "entity_count": len(entities),
            "component_types_seen_in_fallback": retrieval, "bodies": records}


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, check=True, timeout=30).stdout.strip()


def inspect_installed(report):
    receipt = json.loads((ROOT / "docs/research/experiments/evidence/AETHER_CL_M7_Installed_Inspection.json").read_text())
    actual = {name: version(name) for name in receipt["packages"]}
    report["packages"] = actual
    if sys.version_info[:2] != (3, 10) or actual != receipt["packages"]:
        raise ValueError("Use the unchanged Python3.10 aether-cl native environment")
    pkg = Path(distribution("mani_skill").locate_file("mani_skill")).resolve()
    hashes = {name: sha256_file(pkg / name) for name in receipt["source_sha256"]}
    report["inherited_installed_sources_sha256"] = hashes
    if hashes != receipt["source_sha256"]:
        raise ValueError("Installed ManiSkill bytes changed since the M7 inspection")
    report["mani_skill_sources"] = [source_record(pkg / name, pkg) for name in SOURCE_PATHS if (pkg / name).is_file()]
    report["missing_optional_source_paths"] = [n for n in SOURCE_PATHS if not (pkg / n).is_file()]
    report["constructor_initialization_reset_seeds"] = constructor_reset_seeds((pkg / "envs/sapien_env.py").read_text())
    sapien_pkg = Path(distribution("sapien").locate_file("sapien")).resolve()
    report["sapien_interface_sources"] = [source_record(p, sapien_pkg) for p in sorted(sapien_pkg.rglob("*.pyi"))
        if PHYSICAL_WORDS.search(p.read_text(encoding="utf-8"))]
    import sapien
    module = sapien.physx
    report["sapien_physx_bindings"] = [interface(getattr(module, name)) for name in sorted(dir(module))
        if name.startswith("Physx") and any(k in name for k in ("Rigid", "System", "Material", "CollisionShape"))
        and inspect.isclass(getattr(module, name))]
    report["sapien_native_binaries"] = [{"path": str(p.relative_to(sapien_pkg)), "bytes": p.stat().st_size,
        "sha256": sha256_file(p)} for p in sorted(sapien_pkg.rglob("*.so"))]
    report["force_api_status"] = "candidate_interfaces_captured_not_yet_commissioned"


def inspect_live(report):
    sys.path.insert(0, str(PROTOTYPE))
    from aether_cl.runtime import build_env, json_value
    from aether_cl.m6r_runtime import M6RConfig
    from aether_cl.m6_runtime import observe_native
    config = M6RConfig(seed=DEVELOPMENT_SEED, system="baseline", verification=False, render=False)
    config.validate()
    env = None
    try:
        print("Constructing unrendered CPU PickCube-v1; explicit development reset100 only", flush=True)
        report["environment_construction_attempted"] = True
        env = build_env(config)
        report["environments_created"] = 1
        base = env.unwrapped
        if bool(getattr(base, "gpu_sim_enabled", False)):
            raise ValueError("M8 inspection requires CPU physics")
        report["explicit_reset_attempted_seeds"] = [DEVELOPMENT_SEED]
        observation, info = env.reset(seed=DEVELOPMENT_SEED)
        report["explicit_reset_seeds"] = [DEVELOPMENT_SEED]
        observation, info = observe_native(env, observation, info)
        report["native_geometry"] = {"cube_half_size_m": float(base.cube_half_size),
            "native_goal_world_m": json_value(base.goal_site.pose.p),
            "goal_projection_performed": False,
            "cube": actor_record(base.cube, json_value),
            "table": actor_record(base.table_scene.table, json_value),
            "cube_table_contact_force_world_n": json_value(info["cube_table_contact_force_world_n"])}
        systems = {}
        for name in sorted(n for n in dir(base.scene) if n == "px" or "physx" in n.lower()):
            try:
                system = getattr(base.scene, name)
                systems[name] = {"class": type(system).__name__,
                    **properties(system, ("timestep", "gravity"), json_value)}
            except Exception as exc:
                systems[name] = {"unavailable": f"{type(exc).__name__}: {exc}"}
        report["physics"] = {"frequencies": properties(base,
            ("sim_freq", "control_freq", "_sim_steps_per_control"), json_value),
            "scene_public_names": sorted(n for n in dir(type(base.scene)) if not n.startswith("_")),
            "physics_system_candidates": systems}
        hooks = {}
        for name in ("step", "_step_action", "_before_control_step", "_before_simulation_step", "_after_simulation_step"):
            try:
                hook = getattr(base, name)
                hooks[name] = {"qualname": hook.__qualname__, "source": inspect.getsource(hook)}
            except Exception as error:
                hooks[name] = {"unavailable": f"{type(error).__name__}: {error}"}
        report["actual_physics_hooks"] = hooks
        masses = [r["physical_properties"]["values"].get("mass") for r in report["native_geometry"]["cube"]["bodies"]]
        report["cube_mass_capture_complete"] = bool(masses) and all(isinstance(m, (int, float)) and m > 0 for m in masses)
        report["live_force_api_names"] = sorted({n for r in report["native_geometry"]["cube"]["bodies"]
                                                  for n in r["interface"]["force_or_impulse_names"]})
    finally:
        if env is not None:
            env.close()


def write_bundle(output, archive, report):
    if archive.exists() or any((output / n).exists() for n in ("inspection.json", "executed_inspection.py", "file_index.json")):
        raise FileExistsError("Retain previous inspection bundle; do not overwrite its report or archive")
    (output / "inspection.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "executed_inspection.py").write_bytes(Path(__file__).read_bytes())
    index = {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(output.iterdir()) if p.is_file()}
    (output / "file_index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("xb") as raw:
        with tarfile.open(fileobj=raw, mode="w:gz") as tar:
            tar.add(output, arcname="m8-physics-inspection")
    print("Report:", output / "inspection.json", flush=True)
    print("Archive:", archive, flush=True)
    print("SHA-256:", sha256_file(archive), flush=True)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--archive", type=Path, required=True)
    cli.add_argument("--expected-head", required=True)
    args = cli.parse_args(argv)
    output, archive = args.output.resolve(), args.archive.resolve()
    if output.is_relative_to(ROOT) or archive.is_relative_to(ROOT):
        raise ValueError("Inspection artifacts must be outside the guarded checkout")
    if output.exists() or archive.exists():
        raise FileExistsError("Retain previous inspection evidence; choose new output/archive paths")
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "scope": "M8_development_installed_force_inspection",
        "02_authority_commit": AUTHORITY, "time_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256_file(Path(__file__)), "confirmatory": False,
        "status": "starting", "python": sys.version.split()[0],
        "conda_environment": os.environ.get("CONDA_DEFAULT_ENV"),
        "native_library_environment": {k: os.environ.get(k) for k in ("LD_LIBRARY_PATH", "LD_PRELOAD", "CUDA_VISIBLE_DEVICES")},
        "environment_construction_attempted": False, "environments_created": 0,
        "explicit_reset_attempted_seeds": [], "explicit_reset_seeds": [], "controller_actions_executed": 0,
        "disturbance_commands_executed": 0, "force_family_frozen": False, "fresh_study_started": False}
    error = None
    try:
        report["native_repo_commit"] = git("rev-parse", "HEAD")
        report["native_repo_dirty"] = bool(git("status", "--porcelain"))
        if report["native_repo_commit"] != args.expected_head or report["native_repo_dirty"]:
            raise ValueError("Native checkout differs from the requested clean inspection revision")
        git("merge-base", "--is-ancestor", AUTHORITY, "HEAD")
        current = {n: sha256_file(PROTOTYPE / "aether_cl" / n) for n in ACCEPTED_SOURCES}
        report["accepted_placement_sources_sha256"] = current
        if current != ACCEPTED_SOURCES:
            raise ValueError("Accepted placement/controller/verifier/recovery bytes changed")
        print("Scanning retained native reset history; no fresh seeds will be reset", flush=True)
        report["native_reset_history"] = inspect_history(PROTOTYPE / "runs", lambda s: print(s, flush=True))
        print("Inspecting installed source and SAPIEN binding descriptors", flush=True)
        inspect_installed(report)
        inspect_live(report)
        if git("rev-parse", "HEAD") != args.expected_head or git("status", "--porcelain"):
            raise ValueError("Checkout changed during inspection")
        report["status"] = "inspection_complete_await_independent_engineering_review"
        print("M8_PHYSICS_INSPECTION_READY", flush=True)
        print("Live force/impulse candidates:", report["live_force_api_names"], flush=True)
        print("Cube mass captured:", report["cube_mass_capture_complete"], flush=True)
        print("Fresh160_179 overlap:", report["native_reset_history"]["preferred_overlap"], flush=True)
    except BaseException as exc:
        error = exc
        report.update(status="error_retained_no_fresh_execution", error=f"{type(exc).__name__}: {exc}",
                      traceback=traceback.format_exc())
        print(report["error"], file=sys.stderr, flush=True)
    finally:
        write_bundle(output, archive, report)
    if error is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
