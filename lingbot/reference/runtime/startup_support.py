"""One measured startup of the exact failed simulator worker, without a policy."""
import argparse
import ast
import csv
import functools
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import math
import os
import random
import re
import signal
import struct
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
from pathlib import Path
PROJECT = Path('/path/to/lingbot-workspace')
FAILED = PROJECT / 'data-preparation/source200-rollout-v1/run-mNdEqc7E'
OUT = Path(os.environ.get('LINGBOT_STARTUP_OUT', str(Path(__file__).resolve().parent)))
SIM_PY = '/path/to/conda/envs/robotwin-sim/bin/python'
SIM_ENV = Path('/path/to/conda/envs/robotwin-sim')
PINS = {'RoboTwin/envs/_base_task.py': '448f7152b65cb9102217cf5463aa821d72810ca56f63d5a797ec7bd43e23e101', 'RoboTwin/envs/adjust_bottle.py': '4f76b35e718a4c5a364dae564d35d68268755818d9062e3ed4ff393d158d0548', 'RoboTwin/envs/robot/robot.py': '3dcd80acc8cab489a4c5edb507cc460dab1724be0226b8d5c4c1b218dee605cb', 'RoboTwin/envs/robot/planner.py': 'f1012345542483f4cfbac64880a266b7ee0d4a64362d5ec6fd6985ed9c34b564', 'RoboTwin/envs/camera/camera.py': 'e4d17e99c8a68f44a12bef248a2164f52206efeaf24168172b778cc1e32832dd', 'RoboTwin/envs/_GLOBAL_CONFIGS.py': 'f3640d4d132531e1c4a72f1f27dd6312c95aadcb72ab43c638458cf994b5a4d4', 'RoboTwin/envs/utils/actor_utils.py': '252d43c526b23adcf4ba549fec64a49f037fc4a24e9edd1998e5f60d3e13d5d9', 'RoboTwin/envs/utils/action.py': '7bf69e226b98ae7f5b21a523f722271530885cf4778873900f3564003a9b591d', 'RoboTwin/task_config/demo_clean.yml': '8ee5d0d07daecf7599b8d89b44776b700c7c60da24cd6317e176e6798d8cb11e', 'RoboTwin/task_config/_camera_config.yml': 'dc80a40552e0fad25d58cf0141302ceba66d22409b5091bed235ad2f10cbce7f', 'RoboTwin/task_config/_eval_step_limit.yml': '41c62bd26184977bae45aee555edd0cc21de5cddf560c2595921fc23a1e3b551', 'RoboTwin/assets/embodiments/aloha-agilex/config.yml': 'a4f043d2d4b44cca5ec47fb498a3194da3f87ff9530dcbfdcee1539a44423d57', 'RoboTwin/assets/embodiments/aloha-agilex/curobo_left.yml': '692bba019af6c2fd0cba2c437dc6a4210a7070cfca1ced0b3350e90fff7d98ab', 'RoboTwin/assets/embodiments/aloha-agilex/curobo_right.yml': '210ad5c7ed29a7a6825079547d7381f7b4f5881df12fea5c1a2ef61c783ba01d', 'RoboTwin/assets/embodiments/aloha-agilex/collision_aloha_left.yml': '19e21fbba8b6657ffc6d405ac53b277902ce118821b818aa77aad2e0b0d7f83d', 'RoboTwin/assets/embodiments/aloha-agilex/collision_aloha_right.yml': 'd22850769a5c28fec35434e12ffb597837853cb4dd916b74969e6e615faf5cdd', 'data-preparation/source200-rollout-v1/run-mNdEqc7E/sim_worker.py': '29728d5f774737fbc85400fea62d706aa886e8f48251edc8a4bd3fab3b7d7542', 'data-preparation/source200-rollout-v1/run-mNdEqc7E/rollout_telemetry.py': '6a7f9a5a9f65ff3b9112a250930f295115bdb7a84accb7a07b556774e8c7f779', 'RoboTwin/description/utils/generate_episode_instructions.py': 'ef428fa9066c3025d41e2fabcbf894d1d4313bd12bee0a300d19d3d7d1158f24'}
EXPECTED_VERSIONS = {'torch': '2.4.1+cu121', 'sapien': '3.0.0b1', 'mplib': '0.2.1', 'nvidia-curobo': '0.7.8', 'open3d': '0.18.0', 'warp-lang': '1.12.0'}
CHILD_SECONDS = 480
report = dict(status='RUNNING', model_loaded=False, optimizer_created=False, training_updates=0, scene_ready=False, instruction_selection_fix='Full filtered seen-template cycle and whole arm words', scope='One instrumented simulator startup; no policy, actions, oracle or grasp evaluation')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(value, message):
    if not value:
        raise RuntimeError(message)

def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temporary, path)

def atomic_report():
    atomic_json(OUT / 'report.json', report)

def scene_instruction(task):
    """Use the audited local generator; consider a full finite template cycle."""
    path = PROJECT / 'RoboTwin/description/utils/generate_episode_instructions.py'
    spec = importlib.util.spec_from_file_location('_checked_scene_descriptions', path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    templates = generator.load_task_instructions('adjust_bottle').get('seen')
    require(isinstance(templates, list) and 0 < len(templates) <= 10000, 'Unexpected seen-template count')
    side = 'right' if task.qpose_tag == 1 else 'left'
    other = 'left' if side == 'right' else 'right'
    info = {'{A}': f'001_bottle/base{task.model_id}', '{a}': side}
    generated = generator.generate_episode_descriptions('adjust_bottle', [info], len(templates))
    require(isinstance(generated, list) and generated and isinstance(generated[0].get('seen'), list), 'Invalid generated instruction schema')
    candidates = [text for text in generated[0]['seen'] if isinstance(text, str) and re.search('\\b' + side + '\\s+arm\\b', text, re.I) and (not re.search('\\b' + other + '\\s+arm\\b', text, re.I))]
    require(candidates, 'No explicit arm-consistent seen instruction is available')
    return (candidates[0], side, info)

def traced_instruction(task):
    stage('instruction_for')
    try:
        result = scene_instruction(task)
    except BaseException as error:
        stage('instruction_for', 'ERROR', error=repr(error))
        raise
    stage('instruction_for', 'END', requested_arm=result[1], instruction=result[0])
    return result

def preflight():
    for relative, expected in PINS.items():
        require(digest(PROJECT / relative) == expected, 'Pinned startup source changed: ' + relative)
    protected = {str(PROJECT / path): expected for path, expected in PINS.items()}
    site = SIM_ENV / 'lib/python3.10/site-packages'
    packages = {}
    for item in importlib.metadata.distributions(path=[str(site)]):
        name = (item.metadata.get('Name') or '').lower().replace('_', '-')
        if name in EXPECTED_VERSIONS:
            packages[name] = item.version
    require(packages == EXPECTED_VERSIONS, 'Simulator package metadata changed: ' + repr(packages))
    descriptions = PROJECT / 'RoboTwin/description'
    for relative in ('task_instruction/adjust_bottle.json', 'objects_description/001_bottle/base13.json', 'objects_description/001_bottle/base16.json'):
        path = descriptions / relative
        value = json.loads(path.read_text())
        require(isinstance(value.get('seen'), list) and value['seen'] and all((isinstance(t, str) and t.strip() for t in value['seen'])), 'Missing/invalid seen descriptions: ' + str(path))
        protected[str(path)] = digest(path)
    instructions = []
    rng = random.getstate()
    try:
        random.seed(20261018)
        for tag in (0, 1):
            for model_id in (13, 16):
                text, side, info = scene_instruction(SimpleNamespace(qpose_tag=tag, model_id=model_id))
                instructions.append(dict(arm=side, model_id=model_id, instruction=text))
    finally:
        random.setstate(rng)
    return dict(protected_files=protected, packages=packages, instructions=instructions)

def gpu_snapshot():
    listing = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,name,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True)
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory', '--format=csv,noheader,nounits'], text=True)
    processes = {}
    for row in csv.reader(io.StringIO(apps)):
        if not row or not any((value.strip() for value in row)):
            continue
        require(len(row) == 3, 'Unexpected GPU process inventory; selection stopped.')
        uuid, pid, memory = [value.strip() for value in row]
        processes.setdefault(uuid, []).append({'pid': int(pid), 'used_mib': int(memory) if memory.isdecimal() else None})
    devices = {}
    for line in csv.reader(io.StringIO(listing)):
        index, uuid, name, free, busy = [v.strip() for v in line]
        resident = processes.get(uuid, [])
        resident_mib = sum((row['used_mib'] for row in resident)) if all((row['used_mib'] is not None for row in resident)) else None
        devices[uuid] = {'index': int(index), 'uuid': uuid, 'name': name, 'free_mib': int(free), 'utilization': int(busy), 'occupied': bool(resident), 'resident_mib': resident_mib, 'resident_processes': resident}
    return devices

def eligible(device):
    return 'A100' in device['name'] and device['free_mib'] >= 60 * 1024 and (device['utilization'] <= 10)

def select_gpu():
    snapshots = []
    for index in range(3):
        snapshots.append(gpu_snapshot())
        if index < 2:
            time.sleep(2)
    shared = set(snapshots[0]).intersection(*[set(s) for s in snapshots[1:]])
    options = [snapshots[-1][uuid] for uuid in shared if all((eligible(s[uuid]) for s in snapshots))]
    report['gpu_snapshots'] = [list(s.values()) for s in snapshots]
    report['gpu_selection_policy'] = {'minimum_free_gib': 60, 'allocator_cap_gib': None, 'selection_headroom_gib': None, 'maximum_utilization_percent': 10, 'samples': 3, 'interval_seconds': 2, 'final_recheck': True, 'resident_memory_cutoff_mib': None, 'reservation': False}
    require(options, 'No A100 with at least 60 GiB free and at most 10% utilization in all three samples; no GPU work was started.')
    chosen = max(options, key=lambda row: (not row['occupied'], min((s[row['uuid']]['free_mib'] for s in snapshots)), -max((s[row['uuid']]['utilization'] for s in snapshots)), -row['index']))
    fresh = gpu_snapshot().get(chosen['uuid'])
    report['gpu_final_recheck'] = fresh
    require(fresh is not None and fresh['index'] == chosen['index'] and eligible(fresh), 'Selected GPU lost free-memory headroom or became busy; stopped before model load.')
    chosen = fresh
    os.environ['CUDA_VISIBLE_DEVICES'] = chosen['uuid']
    os.environ['LINGBOT_PHYSICAL_GPU'] = str(chosen['index'])
    report['selected_gpu'] = chosen
    report['quiet_gpu_sharing'] = chosen['occupied']
    print('Selected currently quiet physical GPU:', chosen['index'], flush=True)
    print('Free memory:', round(chosen['free_mib'] / 1024, 2), 'GiB; simulator-only check; no policy allocator or model load.', flush=True)
    print('Existing process memory:', chosen['resident_mib'], 'MiB; existing processes left running. Quiet samples are not a reservation.', flush=True)
_events = None
_active_stages = []

def stage(name, kind='BEGIN', **details):
    if kind == 'BEGIN':
        _active_stages.append(name)
    else:
        matches = [index for index, value in enumerate(_active_stages) if value == name]
        if matches:
            _active_stages.pop(matches[-1])
    event = dict(name=name, kind=kind, pid=os.getpid(), monotonic=time.monotonic(), **details)
    event['active_stages'] = list(_active_stages)
    _events.write(json.dumps(event, allow_nan=False) + '\n')
    _events.flush()
    atomic_json(OUT / 'current-stage.json', event)
    print('STARTUP_STAGE', kind, name, flush=True)

def install_hooks():
    """Wrap existing Python methods; return values, arguments and exceptions pass through."""
    originals = []
    targets = {'envs._base_task': {'Base_Task': ('_init_task_env_', 'setup_scene', 'create_table_and_wall', 'load_robot', 'load_camera', 'together_open_gripper', 'check_stable', 'get_obs', 'close_env')}, 'envs.adjust_bottle': {'adjust_bottle': ('setup_demo', 'load_actors')}, 'envs.robot.robot': {'Robot': ('set_planner', 'init_joints', 'move_to_homestate', 'set_origin_endpose')}, 'envs.robot.planner': {'CuroboPlanner': ('__init__',), 'MplibPlanner': ('__init__',)}, 'envs.camera.camera': {'Camera': ('load_camera',)}}

    def wrapper(original, label):

        @functools.wraps(original)
        def call(*args, **kwargs):
            began = time.monotonic()
            stage(label)
            try:
                result = original(*args, **kwargs)
            except BaseException as error:
                stage(label, 'ERROR', seconds=time.monotonic() - began, error=repr(error))
                raise
            stage(label, 'END', seconds=time.monotonic() - began)
            return result
        return call
    for module_name, classes in targets.items():
        module = sys.modules.get(module_name)
        if module is None:
            continue
        for class_name, names in classes.items():
            cls = getattr(module, class_name, None)
            if cls is None:
                continue
            for name in names:
                if name not in cls.__dict__:
                    continue
                original = cls.__dict__[name]
                if callable(original):
                    originals.append((cls, name, original))
                    setattr(cls, name, wrapper(original, module_name + '.' + class_name + '.' + name))
    stage('method_hooks', 'END', count=len(originals))
    return originals

def instrument_scene(source):
    """Only surround top-level operations. Existing function ASTs stay identical."""
    tree = ast.parse(source)
    new = []
    installed = False
    for index, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            label = 'import:' + (node.module or '' if isinstance(node, ast.ImportFrom) else ','.join((n.name for n in node.names)))
            new.extend(ast.parse('_startup_stage(' + repr(label) + ')').body)
            new.append(node)
            new.extend(ast.parse('_startup_stage(' + repr(label) + ',"END")').body)
            if isinstance(node, ast.ImportFrom) and node.module == 'envs.adjust_bottle':
                require(not installed, 'Duplicate task import')
                new.extend(ast.parse('_startup_originals.extend(_startup_install_hooks())').body)
                installed = True
        elif isinstance(node, ast.Assign) and any((isinstance(t, ast.Name) and t.id == '_scene_renderer_bootstrap' for t in node.targets)):
            new.extend(ast.parse('_startup_stage("renderer_bootstrap")').body)
            new.append(node)
            new.extend(ast.parse('_startup_stage("renderer_bootstrap","END")').body)
        elif isinstance(node, ast.FunctionDef) and node.name == 'instruction_for':
            new.append(node)
            new.extend(ast.parse('instruction_for = _startup_instruction').body)
        elif isinstance(node, ast.FunctionDef) and node.name == 'make_task':
            new.append(node)
            new.extend(ast.parse(node.name + ' = _startup_wrap_function(' + node.name + ',' + repr(node.name) + ')').body)
        else:
            new.append(node)
    require(installed, 'Expected task import missing from saved simulator worker')
    tree.body = new
    return ast.fix_missing_locations(tree)

def child():
    global _events
    import faulthandler
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'startup-stacks.log').open('a', buffering=1) as stacks, (OUT / 'startup-stages.jsonl').open('a', buffering=1) as events:
        _events = events
        faulthandler.enable(file=stacks, all_threads=True)
        faulthandler.dump_traceback_later(30, repeat=True, file=stacks)
        faulthandler.register(signal.SIGUSR1, file=stacks, all_threads=True, chain=False)
        originals = []

        def wrap(function, label):

            @functools.wraps(function)
            def call(*args, **kwargs):
                stage(label)
                try:
                    result = function(*args, **kwargs)
                except BaseException as error:
                    stage(label, 'ERROR', error=repr(error))
                    raise
                stage(label, 'END')
                return result
            return call
        source = FAILED / 'sim_worker.py'
        payload = source.read_text()
        tree = instrument_scene(payload)
        (OUT / 'instrumented-scene.py').write_text(ast.unparse(tree) + '\n')
        sys.argv = [str(source), '--seed', '0', '--output', str(OUT / 'scene'), '--probe']
        namespace = dict(__name__='__main__', __file__=str(source), _startup_stage=stage, _startup_install_hooks=install_hooks, _startup_originals=originals, _startup_wrap_function=wrap, _startup_instruction=traced_instruction)
        try:
            stage('execute_saved_scene')
            exec(compile(tree, str(source), 'exec'), namespace)
            stage('saved_scene_returned', 'END')
        except BaseException as error:
            stage('execute_saved_scene', 'ERROR', error=repr(error))
            traceback.print_exc()
            raise
        finally:
            for cls, name, original in reversed(originals):
                setattr(cls, name, original)
            stage('method_hooks_restored', 'END', count=len(originals))
            faulthandler.cancel_dump_traceback_later()
            faulthandler.unregister(signal.SIGUSR1)
            faulthandler.disable()
            faulthandler.enable(file=sys.stderr, all_threads=True)
            faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True, chain=False)
            faulthandler.dump_traceback_later(30, repeat=True, file=sys.stderr)

def read_stage():
    path = OUT / 'current-stage.json'
    return json.loads(path.read_text()) if path.exists() else None

def stop_owned(child):
    if child.poll() is not None:
        return
    try:
        os.kill(child.pid, signal.SIGUSR1)
    except ProcessLookupError:
        return
    time.sleep(0.25)
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=8)

def validate_scene():
    path = OUT / 'scene/scene-report.json'
    require(path.is_file(), 'Original worker did not save a scene report')
    value = json.loads(path.read_text())
    require(value.get('status') == 'READY', 'Original scene report is not READY')
    require(len(value.get('drive', [])) == 14 and all((math.isfinite(x) for x in value['drive'])), 'Invalid drive-state evidence')
    require(len(value.get('measured_arm', [])) == 12 and all((math.isfinite(x) for x in value['measured_arm'])), 'Invalid measured-joint evidence')
    for name in ('head_camera', 'left_camera', 'right_camera'):
        image = (OUT / 'scene' / f'{name}-start.png').read_bytes()
        require(image[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', image[16:24]) == (320, 240), 'Invalid camera PNG: ' + name)
    return value

def parent():
    began = time.monotonic()
    child_process = None
    protected = {}
    timed_out = False

    def interrupted(signum, frame):
        raise RuntimeError('Startup check interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        atomic_report()
        checked = preflight()
        protected = checked['protected_files']
        report['package_versions'] = checked['packages']
        report['instruction_preflight'] = checked['instructions']
        select_gpu()
        atomic_report()
        env = {**os.environ, 'LINGBOT_STARTUP_OUT': str(OUT), 'CUDA_VISIBLE_DEVICES': report['selected_gpu']['uuid'], 'LINGBOT_PHYSICAL_GPU': str(report['selected_gpu']['index']), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'OPEN3D_CPU_RENDERING': 'true', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'LINGBOT_ENABLE_FAST_MOE': '0', 'PYTHONPATH': str(OUT) + ':' + str(FAILED) + ':' + str(PROJECT / 'RoboTwin')}
        print('Starting one original scene probe with 30-second stacks; no policy is loaded.', flush=True)
        with (OUT / 'scene.log').open('ab', buffering=0) as stream:
            child_process = subprocess.Popen([SIM_PY, '-u', str(Path(__file__).resolve()), 'child'], stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, env=env, cwd=PROJECT / 'RoboTwin', start_new_session=True)
        report.update(scene_child_pid=child_process.pid, gpu_work_started=True)
        atomic_report()
        started = time.monotonic()
        next_progress = started
        while child_process.poll() is None:
            if time.monotonic() - started >= CHILD_SECONDS:
                timed_out = True
                break
            if time.monotonic() >= next_progress:
                report.update(last_stage=read_stage(), scene_wall_seconds=time.monotonic() - started)
                atomic_report()
                print('Scene startup progress:', report['last_stage'], flush=True)
                next_progress = time.monotonic() + 15
            time.sleep(0.25)
        if timed_out:
            report['last_stage_before_stop'] = read_stage()
            stop_owned(child_process)
            report['scene_ready_file_present'] = (OUT / 'scene/scene-report.json').exists()
            raise RuntimeError('Eight-minute startup deadline; last stage and Python stacks are saved. No policy was loaded.')
        report['scene_exit_code'] = child_process.returncode
        require(child_process.returncode == 0, 'Scene subprocess failed; inspect scene.log, stages and stacks')
        report.update(scene=validate_scene(), scene_ready=True, status='COMPLETE')
        print('SIMULATOR STARTUP / OBSERVATION CAPTURE / PROCESS EXIT: PASS. No grasp evaluation.', flush=True)
    except BaseException as error:
        report.update(status='ERROR', error=str(error), traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        if child_process is not None:
            stop_owned(child_process)
        report['owned_child_stopped'] = child_process is None or child_process.poll() is not None
        report['last_stage'] = read_stage()
        report['startup_timed_out'] = timed_out
        try:
            report['original_files_unchanged'] = bool(protected) and all((digest(path) == value for path, value in protected.items()))
        except OSError as error:
            report.update(original_files_unchanged=False, preservation_error=str(error))
        if not report['owned_child_stopped'] or not report['original_files_unchanged']:
            report.update(status='ERROR', error=report.get('error', 'Cleanup/source preservation failed'))
        report['duration_seconds'] = time.monotonic() - began
        atomic_report()
    return 0 if report['status'] == 'COMPLETE' else 1
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('preflight', 'parent', 'child'))
    args = parser.parse_args()
    if args.action == 'preflight':
        print('CPU startup source/package/description preflight: PASS', preflight()['packages'], flush=True)
    elif args.action == 'child':
        child()
    else:
        raise SystemExit(parent())
