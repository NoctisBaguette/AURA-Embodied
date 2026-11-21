"""Run the actual upstream evaluator with HTTP transport and passive visuals."""
import pyexpat
import argparse
import ast
import copy
import faulthandler
import io
import importlib
import json
import os
from pathlib import Path
import random
import signal
import sys
import time
import traceback
import urllib.request
import numpy as np
from joint50_common import CAMERAS, PROJECT, atomic_json, digest, require, PILOT

def evaluation_tree(source):
    tree = ast.parse(source)
    function, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'eval_policy']
    counts = dict(loop=0, generic=0, unstable=0, rejected=0, episode=0, language=0)

    class Instrument(ast.NodeTransformer):

        def visit_While(self, node):
            self.generic_visit(node)
            if ast.unparse(node.test) == 'succ_seed < test_num':
                node.body[:0] = ast.parse('_candidate(now_seed, st_seed)').body
                counts['loop'] += 1
            return node

        def visit_ExceptHandler(self, node):
            if isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                node.body = ast.parse('_rejection(now_seed, e, "FATAL_EXPERT_ERROR")\nraise').body
                counts['generic'] += 1
            elif isinstance(node.type, ast.Name) and node.type.id == 'UnStableError':
                node.body[:0] = ast.parse('_rejection(now_seed, e, "UNSTABLE_SETUP")').body
                counts['unstable'] += 1
            return node

        def visit_If(self, node):
            self.generic_visit(node)
            if isinstance(node.test, ast.BoolOp) and any((isinstance(n, ast.Attribute) and n.attr == 'plan_success' for n in ast.walk(node.test))):
                node.orelse[:0] = ast.parse('_unsolved(now_seed)').body
                counts['rejected'] += 1
            return node

        def visit_AugAssign(self, node):
            if isinstance(node.target, ast.Name) and node.target.id == 'now_id':
                counts['episode'] += 1
                return [*ast.parse('_episode(now_seed, succ, now_id)').body, node]
            return node

        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == 'generate_episode_descriptions':
                require(len(node.args) == 3 and ast.unparse(node.args[2]) == 'test_num', 'Instruction generator signature differs')
                node.args[2] = ast.Constant(100)
                counts['language'] += 1
            return node
    function = Instrument().visit(function)
    require(counts == dict(loop=1, generic=1, unstable=1, rejected=1, episode=1, language=1), 'Upstream evaluator interface changed')
    return ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))

class CommissionComplete(Exception):
    pass

def prepared_sources():
    evaluation_source = PROJECT / 'lingbot-vla-v2/experiment/robotwin/eval_policy_client_lingbotvla.py'
    tree = evaluation_tree(evaluation_source.read_text(encoding='utf-8'))
    compile(tree, str(evaluation_source), 'exec')
    source = (Path(__file__).parent / 'sim_worker.py').read_text(encoding='utf-8')
    definitions = ast.parse(source)
    observers = [n for n in definitions.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in ('observer_camera', 'Recording')]
    require(len(observers) == 2, 'Retained observer source changed')
    compile(ast.fix_missing_locations(ast.Module(body=observers, type_ignores=[])), 'retained-observers', 'exec')
    return (evaluation_source, tree, observers)

def check_source(output):
    import locale
    import yaml
    evaluation_source, tree, observers = prepared_sources()
    files = [evaluation_source, PROJECT / 'RoboTwin/task_config/demo_clean.yml', PROJECT / 'RoboTwin/task_config/demo_randomized.yml', PROJECT / 'RoboTwin/assets/embodiments/aloha-agilex/config.yml']
    for name in PILOT:
        path = PROJECT / 'RoboTwin/envs' / (name + '.py')
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        files.append(path)
    for path in files[1:4]:
        yaml.safe_load(path.read_text(encoding='utf-8'))
    result = dict(status='PASS', source_encoding='utf-8', preferred_encoding=locale.getpreferredencoding(False), utf8_mode=sys.flags.utf8_mode, evaluator_sha256=digest(evaluation_source), files={str(path): digest(path) for path in files}, scope='CPU-only exact evaluator/observer/task-source compile and config decode; no renderer/model/actions')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'report.json', result)
    print(json.dumps(result, allow_nan=False), flush=True)
    return result

def main(args):
    evaluation_source, tree, observer_nodes = prepared_sources()
    import yaml
    from PIL import Image
    sys.path.insert(0, str(PROJECT / 'RoboTwin'))
    sys.path.insert(0, str(PROJECT / 'RoboTwin/description/utils'))
    import sapien.core as sapien
    from sapien.render import set_global_config
    set_global_config(max_num_materials=50000, max_num_textures=50000)
    bootstrap = sapien.SapienRenderer()
    from envs.utils.create_actor import UnStableError
    from generate_episode_instructions import generate_episode_descriptions
    from rollout_telemetry import observe_controller, joint_snapshot, ARM
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    ready = json.loads(Path(args.ready).read_text(encoding='utf-8'))
    stage = ready['stage']
    require(args.commission and stage == 'commission' and (ready['checkpoint'] == 'NO_MODEL_TRANSPORT_COMMISSION') or (not args.commission and stage in ('baseline', 'trained')), 'Commission/learned-policy mode identity mismatch')
    config = yaml.safe_load((PROJECT / 'RoboTwin/task_config' / ('demo_clean.yml' if args.setting == 'clean' else 'demo_randomized.yml')).read_text(encoding='utf-8'))
    robot_dir = PROJECT / 'RoboTwin/assets/embodiments/aloha-agilex'
    robot = yaml.safe_load((robot_dir / 'config.yml').read_text(encoding='utf-8'))
    config.update(task_name=args.task, task_config='demo_clean' if args.setting == 'clean' else 'demo_randomized', policy_name='joint50_fixed_checkpoint', ckpt_setting=stage, embodiment_name='aloha-agilex', left_robot_file=str(robot_dir), right_robot_file=str(robot_dir), left_embodiment_config=copy.deepcopy(robot), right_embodiment_config=copy.deepcopy(robot), dual_arm_embodied=True, render_freq=0, collect_data=False, save_data=False, eval_mode=True, need_plan=True, save_path=str(output), eval_video_save_dir=None, eval_video_log=False)
    require(config['domain_randomization']['random_background'] == (args.setting == 'randomized'), 'Scene setting mismatch')
    task = getattr(importlib.import_module('envs.' + args.task), args.task)()
    visuals = dict(np=np, sapien=sapien)
    exec(compile(ast.fix_missing_locations(ast.Module(body=observer_nodes, type_ignores=[])), str(Path(__file__).parent / 'sim_worker.py'), 'exec'), visuals)
    record = dict(status='RUNNING', stage=stage, task=args.task, setting=args.setting, checkpoint=ready['checkpoint'], episodes=[], rejections=[], candidate_seeds=[], scope='Paired broad pilot; modified transport/passive recording, not full official evaluation')
    current_seed = None
    current = {'action': 0}
    original_setup = task.setup_demo
    original_take = task.take_action

    def setup(*positional, **kwargs):
        nonlocal current_seed
        current_seed = int(kwargs['seed'])
        random.seed(current_seed)
        return original_setup(*positional, **kwargs)
    task.setup_demo = setup

    def take(*positional, **kwargs):
        current['action'] = int(task.take_action_cnt)
        return original_take(*positional, **kwargs)
    task.take_action = take

    class Bridge:

        def __init__(self):
            self.context = None
            self.episode_index = 0
            self.chunk = 0

        def frames(self, observation, tag):
            for camera in CAMERAS:
                rgb = np.asarray(observation[camera])
                require(rgb.shape == (240, 320, 3) and rgb.dtype == np.uint8, 'Camera producer differs')
                Image.fromarray(rgb).save(self.folder / (tag + '-' + camera.rsplit('.', 1)[-1] + '.jpg'), quality=90)

        def sample(self, tick):
            if tick % 25:
                return
            drive, measured, fingers = joint_snapshot(task.robot)
            self.rows.append(dict(physics_step=tick, action_index=int(task.take_action_cnt), drive=drive, measured_arm=measured, measured_fingers=fingers))
            if self.video.frames < 6000:
                self.real_scene.update_render()
                self.observer.take_picture()
                rgb = np.clip(self.observer.get_picture('Color')[..., :3] * 255, 0, 255).astype(np.uint8)
                self.video.write(rgb)

        def infer(self, observation):
            if observation.get('reset'):
                require(self.context is None, 'Previous episode recorder not closed')
                self.episode = f'{stage}-job-{args.job_id:02d}-seed-{current_seed}-ep-{self.episode_index:03d}'
                self.folder = output / self.episode
                self.folder.mkdir()
                self.chunk = 0
                self.rows = []
                self.events = []
                self.requests = []
                self.started = time.monotonic()
                self.real_scene = task.scene
                self.observer = visuals['observer_camera'](task)
                self.video = visuals['Recording'](self.folder)
                self.context = observe_controller(task, self.sample, self.events, current)
                self.wrapped = self.context.__enter__()
                self.sample(0)
                self.episode_index += 1
                return dict(action=[], server_timing=0.0)
            self.chunk += 1
            packet = {key: np.asarray(observation[key], dtype=np.float32 if key == 'observation.state' else np.uint8) for key in (*CAMERAS, 'observation.state')}
            packet.update(task=np.asarray(observation['task']), episode_id=np.asarray(self.episode), chunk_index=np.asarray(self.chunk), noise_seed=np.asarray(777 + self.chunk - 1))
            require(packet['observation.state'].shape == (14,) and np.isfinite(packet['observation.state']).all(), 'State producer differs')
            self.frames(observation, f'chunk-{self.chunk:03d}')
            buffer = io.BytesIO()
            np.savez_compressed(buffer, **packet)
            request = urllib.request.Request(f"http://127.0.0.1:{ready['port']}/infer", data=buffer.getvalue(), headers={'Content-Type': 'application/octet-stream', 'X-LingBot-Run': ready['nonce']})
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.load(response)
            require(result['stage'] == stage and result['checkpoint'] == ready['checkpoint'] and (result['episode_id'] == self.episode) and (result['chunk_index'] == self.chunk), 'Policy identity/response mismatch')
            commands = np.asarray(result['actions'], dtype=np.float32)
            require(commands.shape == (50, 14) and np.isfinite(commands).all(), 'Invalid controller command transport')
            self.requests.append({key: result[key] for key in ('chunk_index', 'noise_seed', 'inference_seconds', 'conditioned_text', 'conditioned_tokens')})
            np.savez_compressed(self.folder / f'commands-{self.chunk:03d}.npz', commands=commands, state=packet['observation.state'])
            if args.commission:
                require(self.chunk == 1 and int(task.take_action_cnt) == 0, 'Commission must stop before policy actions')
                raise CommissionComplete()
            return dict(action=commands, server_timing=result['inference_seconds'])

        def finish(self, seed, success, episode_index):
            require(self.context is not None, 'Missing live episode context')
            try:
                observation = task.get_obs()
                self.frames({key: observation['observation'][camera]['rgb'] for camera, key in [('head_camera', CAMERAS[0]), ('left_camera', CAMERAS[1]), ('right_camera', CAMERAS[2])]}, 'final')
                self.sample(self.wrapped.steps)
            finally:
                self.context.__exit__(None, None, None)
                self.context = None
                self.video.close()
            if self.rows:
                np.savez_compressed(self.folder / 'tracking.npz', **{key: np.asarray([r[key] for r in self.rows]) for key in self.rows[0]})
                error = np.rad2deg(np.asarray([r['measured_arm'] - r['drive'][ARM] for r in self.rows]))
                rmse = float(np.sqrt(np.mean(error ** 2)))
            else:
                rmse = None
            result = dict(status='COMPLETE', task=args.task, setting=args.setting, stage=stage, scene_seed=seed, episode_id=self.episode, checkpoint=ready['checkpoint'], task_success=bool(success), task_predicate=bool(task.eval_success), instruction=task.get_instruction(), step_limit=int(task.step_lim), actions_started=int(task.take_action_cnt), chunks=self.chunk, wall_seconds=time.monotonic() - self.started, video_frames=self.video.frames, video_truncated=self.wrapped.steps // 25 > 6000, video='observer.mp4', directory=str(self.folder.relative_to(output)), tracking_rmse_degrees=rmse, topp_calls=len(self.events), topp_exceptions=sum((e['status'] == 'EXCEPTION' for e in self.events)), topp_empty=sum((e['status'] == 'EMPTY' for e in self.events)), requests=self.requests)
            require(bool(success) == bool(task.eval_success), 'Evaluator and task success flags differ')
            atomic_json(self.folder / 'episode.json', result)
            atomic_json(self.folder / 'planner-events.json', self.events)
            record['episodes'].append(result)
            atomic_json(output / 'report.json', record)
    bridge = Bridge()

    def candidate(seed, start):
        require(seed - start < 64, 'Bounded expert seed search exhausted; case incomplete')
        record['candidate_seeds'].append(seed)
        atomic_json(output / 'report.json', record)

    def rejection(seed, error, category):
        if category == 'UNSTABLE_SETUP':
            frames = traceback.extract_tb(error.__traceback__)
            require(type(error) is UnStableError and any((f.name == '_init_task_env_' and f.filename.endswith('/envs/_base_task.py') for f in frames)), 'Instability outside normal setup is fatal')
        record['rejections'].append(dict(seed=seed, category=category, error=str(error), traceback=traceback.format_exc()))
        atomic_json(output / 'report.json', record)

    def unsolved(seed):
        record['rejections'].append(dict(seed=seed, category='EXPERT_UNSOLVED'))
        atomic_json(output / 'report.json', record)
    (output / 'instrumented-evaluator.py').write_text(ast.unparse(tree) + '\n', encoding='utf-8')
    namespace = dict(np=np, os=os, subprocess=__import__('subprocess'), generate_episode_descriptions=generate_episode_descriptions, UnStableError=UnStableError, _candidate=candidate, _rejection=rejection, _unsolved=unsolved, _episode=lambda seed, success, index: bridge.finish(seed, success, index))
    exec(compile(tree, str(evaluation_source), 'exec'), namespace)
    try:
        namespace['eval_policy'](args.task, task, config, bridge, 100000, test_num=2, instruction_type='seen' if args.setting == 'clean' else 'unseen', usr_args=dict(robo_name='robotwin'))
        require(not args.commission, 'Commission did not stop at the first validated transport response')
        require(len(record['episodes']) == 2, 'Incomplete pilot case')
        record.update(status='COMPLETE', successes=sum((e['task_success'] for e in record['episodes'])))
    except CommissionComplete:
        require(args.commission and bridge.chunk == 1 and (int(task.take_action_cnt) == 0), 'Invalid commission stop')
        record.update(status='COMPLETE', native_commissioned=True, policy_actions_executed=0, chunks=bridge.chunk, scene_seed=current_seed, directory=str(bridge.folder.relative_to(output)), video='observer.mp4', video_frames=bridge.video.frames, scope='Native expert/setup/camera/recorder/transport commissioning; no learned policy or policy actions; no task score')
    finally:
        if bridge.context is not None:
            bridge.context.__exit__(None, None, None)
            bridge.context = None
            bridge.video.close()
        try:
            task.close_env()
        except Exception:
            pass
        atomic_json(output / 'report.json', record)
    return record
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task')
    parser.add_argument('--setting', choices=('clean', 'randomized'))
    parser.add_argument('--job-id', type=int)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ready')
    parser.add_argument('--check-source', action='store_true')
    parser.add_argument('--commission', action='store_true')
    args = parser.parse_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    if args.check_source:
        check_source(args.output)
        raise SystemExit(0)
    require(args.task and args.setting and (args.job_id is not None) and args.ready, 'Missing simulator case arguments')
    with (Path(args.output) / 'native-stacks.log').open('a', buffering=1, encoding='utf-8') as stack:
        faulthandler.enable(file=stack, all_threads=True)
        faulthandler.dump_traceback_later(30, repeat=True, file=stack)
        faulthandler.register(signal.SIGUSR1, file=stack, all_threads=True, chain=False)
        try:
            main(args)
        except BaseException as error:
            atomic_json(Path(args.output) / 'failure.json', dict(status='ERROR', error=str(error), traceback=traceback.format_exc()))
            raise
        finally:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.unregister(signal.SIGUSR1)
