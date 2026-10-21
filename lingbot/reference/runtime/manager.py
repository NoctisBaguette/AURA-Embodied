"""Fresh normal qualification -> broad baseline -> joint training -> paired pilot."""
import json
import os
from pathlib import Path
import shutil
import signal
import time
import traceback
from joint50_common import AUDIT, CAMERAS, PILOT, PROJECT, MODEL_PY, SIM_PY, atomic_json, digest, require, reviewed_inputs, results_document
import qualification_manager as owned
import startup_support
from joint50_pack import package
from joint50_commission import run as commission_simulators
from joint50_failure_report import collect as collect_failure, render as render_failure
from joint50_admission import configure as configure_admission, wait_baseline
OUT = Path(os.environ['LINGBOT_PANEL_OUT'])
state = dict(status='RUNNING', phase='CPU_PREFLIGHT', normal_scene_qualified=False, model_loaded=False, policy_started=False, gpu_work_started=False, checkpoint_promotion=False, scene_processes=[], baseline=[], trained=[])
owned.report = state

def save():
    atomic_json(OUT / 'report.json', state)

def check_cancel():
    control = os.environ.get('LINGBOT_CONTROL_JOB')
    require(not control or not (Path(control) / 'CANCEL').exists(), 'Workflow cancelled; retain recovery checkpoint')

def wait_ready(name, policy, seconds):
    deadline = time.monotonic() + seconds
    last = 0
    while not (OUT / name).exists():
        check_cancel()
        require(policy.poll() is None, 'Policy process exited; inspect policy.log and policy/report.json')
        require(time.monotonic() < deadline, 'Stage deadline: ' + name)
        if time.monotonic() - last > 20:
            progress = OUT / 'training/progress.json'
            if progress.exists():
                state['training_progress'] = json.loads(progress.read_text(encoding='utf-8'))
            save()
            last = time.monotonic()
        time.sleep(0.5)
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def pilot(stage, ready, environment):
    import cv2
    results = []
    deadline = time.monotonic() + 3 * 3600
    for index, (task, setting) in enumerate(((task, setting) for task in PILOT for setting in ('clean', 'randomized'))):
        check_cancel()
        directory = OUT / stage / f'{index:02d}-{task}-{setting}'
        directory.mkdir(parents=True)
        child = owned.spawn(OUT / 'joint50_sim.py', directory / 'sim.log', environment, ['--task', task, '--setting', setting, '--job-id', index, '--output', directory, '--ready', OUT / (stage + '-ready.json')], python=SIM_PY, cwd=PROJECT / 'RoboTwin')
        owned.scene_children.add(child.pid)
        save_registry()
        limit = min(time.monotonic() + 20 * 60, deadline)
        while child.poll() is None:
            check_cancel()
            require(time.monotonic() < limit, 'Simulator pilot case timed out: ' + str(directory))
            time.sleep(0.5)
        stopped = owned.stop(child)
        if not stopped or child.returncode != 0:
            state['error'] = 'Simulator pilot case failed: ' + str(directory) + ' exit=' + str(child.returncode)
            save()
            print(render_failure(collect_failure(OUT)), flush=True)
            raise RuntimeError(state['error'])
        result = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
        require(result['status'] == 'COMPLETE' and len(result['episodes']) == 2 and (result['checkpoint'] == ready['checkpoint']), 'Pilot case result identity differs')
        for episode in result['episodes']:
            video = directory / episode['directory'] / episode['video']
            capture = cv2.VideoCapture(str(video))
            frames = 0
            while True:
                okay, frame = capture.read()
                if not okay:
                    break
                require(frame.shape == (384, 512, 3), 'Recorded observer dimensions differ')
                frames += 1
            capture.release()
            require(frames == episode['video_frames'] and frames > 0, 'Video decode/count mismatch')
            episode['all_saved_video_frames_decoded'] = True
            episode['case_directory'] = str(directory.relative_to(OUT))
            results.append(episode)
        state[stage] = results
        save()
        print(stage, task, setting, 'successes', sum((e['task_success'] for e in result['episodes'])), '/2', flush=True)
    require(len(results) == 32, 'Incomplete broad pilot')
    template = json.loads((OUT / 'official-results-template.json').read_text(encoding='utf-8'))
    atomic_json(OUT / stage / 'results.json', results_document(template, results, ready['checkpoint']))
    package(OUT)
    return results

def save_registry():
    atomic_json(OUT / 'owned-children.json', [dict(pid=child.pid, birth=owned.births[child.pid]) for child in owned.children])
_original_spawn = owned.spawn

def tracked_spawn(*args, **kwargs):
    child = _original_spawn(*args, **kwargs)
    save_registry()
    return child
owned.spawn = tracked_spawn

def main():
    policy = None
    protected = {}
    began = time.monotonic()

    def interrupt(signum, frame):
        raise RuntimeError('Workflow interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        save()
        audit, _ = reviewed_inputs()
        from panel_preflight import run as preflight
        checked = preflight(OUT, OUT / 'preflight-report.json')
        protected = checked['protected_files']
        preview = Path(os.environ['LINGBOT_CONTROL_JOB']) / 'source-preview/source-frames'
        require((preview / 'frames.json').exists(), 'Prepared source camera frames missing')
        shutil.copytree(preview, OUT / 'source-frames')
        (OUT / 'run-nonce.txt').write_text(__import__('uuid').uuid4().hex + '\n', encoding='utf-8')
        startup_support.report = state
        state['phase'] = 'GPU_ADMISSION'
        save()
        startup_support.select_gpu()
        state['gpu_work_started'] = True
        admitted = state['selected_gpu']
        atomic_json(OUT / 'simulator-admission.json', admitted)
        state['phase'] = 'NORMAL_SCENE_QUALIFICATION'
        save()
        environment = {**os.environ, 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'LINGBOT_ENABLE_FAST_MOE': '0', 'CUDA_VISIBLE_DEVICES': admitted['uuid'], 'LINGBOT_PHYSICAL_GPU': str(admitted['index']), 'PYTHONPATH': str(OUT) + ':' + str(PROJECT / 'lingbot-vla-v2')}
        simulator = {**environment, 'OPEN3D_CPU_RENDERING': 'true', 'PYTHONPATH': str(OUT) + ':' + str(PROJECT / 'RoboTwin')}
        selected = {}
        deadline = time.monotonic() + 480
        for seed in range(8):
            require(time.monotonic() < deadline, 'Normal qualification search expired')
            result = owned.scene_run(seed, OUT / 'scene-probes' / f'seed-{seed:02d}', simulator, seconds=deadline - time.monotonic())
            save_registry()
            if result.get('status') == 'REJECTED_UNSTABLE_SETUP':
                continue
            selected.setdefault(result['requested_arm'], result)
            if set(selected) == {'left', 'right'}:
                break
        require(set(selected) == {'left', 'right'}, 'Normal qualification did not cover both arms')
        state.update(normal_scene_qualified=True, phase='NATIVE_SIMULATOR_COMMISSION')
        save()
        commission_simulators(OUT, simulator, owned, state, save, check_cancel, package)
        state.update(phase='BASELINE_POLICY_LOADING', policy_started=True)
        save()
        admission = configure_admission(OUT, os.environ['LINGBOT_CONTROL_JOB'], admitted)
        policy = owned.spawn(OUT / 'joint50_policy.py', OUT / 'policy.log', environment)
        save_registry()
        ready = wait_baseline(OUT, policy, admission, check_cancel, state, save)
        require(ready['gpu_uuid'] == admitted['uuid'] and ready['checkpoint'] == audit['original_checkpoint'] and ready['original_padding_replay'], 'Baseline policy identity differs')
        state.update(model_loaded=True, phase='BASELINE', baseline_identity=ready)
        save()
        baseline = pilot('baseline', ready, simulator)
        state['phase'] = 'JOINT_TRAINING'
        save()
        (OUT / 'BEGIN_TRAIN').touch()
        trained = wait_ready('trained-ready.json', policy, 24 * 3600)
        state.update(phase='TRAINED_PILOT', trained_identity=trained)
        save()
        after = pilot('trained', trained, simulator)
        training = json.loads((OUT / 'training/report.json').read_text(encoding='utf-8'))
        before_success = sum((e['task_success'] for e in baseline))
        after_success = sum((e['task_success'] for e in after))
        state.update(status='COMPLETE', phase='FINISHED', training=training, baseline_successes=before_success, trained_successes=after_success, training_updates=training['completed_updates'], interpretation='Paired 32-episode pilot only; retain original fallback and candidate. No automatic final submission promotion.')
        atomic_json(OUT / 'candidate-review.json', dict(baseline_successes=before_success, candidate_successes=after_success, baseline_checkpoint=ready['checkpoint'], candidate_checkpoint=trained['checkpoint'], provisional_direction='candidate improved on this pilot' if after_success > before_success else 'candidate did not improve this pilot', fresh_process_export_reload_pending=True, official_score=False))
    except BaseException as error:
        state.update(status='ERROR', error=str(error), traceback=traceback.format_exc())
        save()
        traceback.print_exc()
        try:
            print(render_failure(collect_failure(OUT)), flush=True)
        except Exception as diagnostic_error:
            print('Failure reader error:', str(diagnostic_error), flush=True)
    finally:
        (OUT / 'STOP_TRAIN').touch()
        (OUT / 'STOP_POLICY').touch()
        if policy is not None:
            deadline = time.monotonic() + 90
            while policy.poll() is None and time.monotonic() < deadline:
                time.sleep(0.5)
        stopped = [owned.stop(child) for child in reversed(owned.children)]
        state['owned_children_stopped'] = all(stopped) and all((child.poll() is not None for child in owned.children))
        try:
            state['original_files_unchanged'] = bool(protected) and all((digest(path) == expected for path, expected in protected.items()))
        except OSError:
            state['original_files_unchanged'] = False
        try:
            reviewed_inputs()
            state['reviewed_input_files_unchanged'] = True
        except Exception as error:
            state['reviewed_input_files_unchanged'] = False
            state.setdefault('error', str(error))
        if not state['reviewed_input_files_unchanged']:
            state['original_files_unchanged'] = False
        if not state['owned_children_stopped'] or not state['original_files_unchanged']:
            state.update(status='ERROR', error=state.get('error', 'Cleanup/source preservation failed'))
        state['duration_seconds'] = time.monotonic() - began
        save()
    return 0 if state['status'] == 'COMPLETE' else 1
if __name__ == '__main__':
    raise SystemExit(main())
