"""Own a single policy process and four serial simulator processes."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from panel_preflight import run as preflight
from rollout_preflight import digest
import owned_processes
import startup_support
from scene_validation import validate_scene

OUT=Path(os.environ['LINGBOT_PANEL_OUT'])
PROJECT=Path('/path/to/lingbot-workspace')
MODEL_PY='/path/to/conda/envs/lingbotvla/bin/python'
SIM_PY='/path/to/conda/envs/robotwin-sim/bin/python'
children=[]
births={}
scene_children=set()
report=dict(status='RUNNING',episodes=[],scope='Four censored clean-scene diagnostics; not a competition score',
    training_updates=0,optimizer_created=False,checkpoint_promotion=False,
    model_loaded=False,policy_loaded=False,normal_scene_qualified=False,scene_processes=[])

def write_report():
    temporary=OUT/'report.json.partial';temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');os.replace(temporary,OUT/'report.json')

def stop(child):
    if child.pid in scene_children and child.poll() is None:
        try:os.kill(child.pid,signal.SIGUSR1)
        except ProcessLookupError:pass
        time.sleep(.5)
    return owned_processes.stop_session(child,births.get(child.pid,0))

def spawn(script,log,env,args=(),python=None,cwd=None):
    with Path(log).open('ab',buffering=0) as stream:
        child=subprocess.Popen([python or MODEL_PY,'-u',str(script),*map(str,args)],stdin=subprocess.DEVNULL,
            stdout=stream,stderr=subprocess.STDOUT,env=env,cwd=cwd or PROJECT/'lingbot-vla-v2',start_new_session=True)
    children.append(child)
    deadline=time.monotonic()+1
    info=owned_processes.proc_info(child.pid)
    while info is None and child.poll() is None and time.monotonic()<deadline:
        time.sleep(.01);info=owned_processes.proc_info(child.pid)
    if info is None and child.poll() is None:
        child.terminate()
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
        raise RuntimeError('Could not verify owned child process identity')
    births[child.pid]=info['start'] if info else 0
    return child

def scene_run(seed,output,env,noise=None,seconds=None):
    output.mkdir(parents=True,exist_ok=True)
    args=['--seed',seed,'--output',output]
    if noise is None:args+=['--probe']
    else:args+=['--noise',noise,'--ready',OUT/'policy-ready.json']
    child=spawn(OUT/'scene_runner.py',output/'scene.log',env,args,python=SIM_PY,cwd=PROJECT/'RoboTwin')
    scene_children.add(child.pid)
    process=dict(seed=seed,noise_seed=noise,directory=str(output.relative_to(OUT)),pid=child.pid,
                 timed_out=False,exit_code=None)
    report['scene_processes'].append(process);write_report()
    try:code=child.wait(timeout=seconds if seconds is not None else 480)
    except subprocess.TimeoutExpired:
        process['timed_out']=True
        process['owned_processes_stopped']=stop(child);process['exit_code']=child.poll();write_report()
        raise RuntimeError('Simulator subprocess deadline: '+str(output))
    process['exit_code']=code
    process['exit_signal']=signal.Signals(-code).name if code<0 else None
    process['owned_processes_stopped']=stop(child)
    write_report()
    if not process['owned_processes_stopped']:
        raise RuntimeError('Simulator process session cleanup failed: '+str(output))
    scene_path=output/'scene-report.json'
    if code:
        failure_path=output/'scene-failure.json'
        try:failure=json.loads(failure_path.read_text()) if failure_path.is_file() else {}
        except (OSError,ValueError):failure={}
        if (code==1 and noise is None and failure.get('schema_version')==1
                and failure.get('scene_seed')==seed and failure.get('pid')==child.pid
                and failure.get('category')=='UNSTABLE_SETUP'
                and failure.get('exception_module')=='envs.utils.create_actor'
                and failure.get('exception_type')=='UnStableError'
                and failure.get('during_setup') is True and failure.get('probe') is True):
            process.update(outcome='REJECTED_UNSTABLE_SETUP',failure=failure)
            write_report()
            return dict(status='REJECTED_UNSTABLE_SETUP',scene_seed=seed,
                        reason=failure['message'],directory=str(output.relative_to(OUT)))
        try:error=json.loads(scene_path.read_text()) if scene_path.exists() else {}
        except (OSError,ValueError) as error_report:error={'error':'Scene report unreadable: '+str(error_report)}
        raise RuntimeError('Simulator failed: '+str(output)+' exit='+str(code)+' '+str(process['exit_signal'])+' '+str(error.get('error','inspect scene.log/startup-stacks.log')))
    validate_scene(output)
    return json.loads(scene_path.read_text())

def main():
    began=time.monotonic();protected={};ready=None;policy=None
    def interrupted(signum,frame):raise RuntimeError('Panel interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    try:
        write_report();checked=preflight(OUT,OUT/'preflight-report.json');protected=checked['protected_files']
        (OUT/'run-nonce.txt').write_text(uuid.uuid4().hex+'\n')
        report['phase']='NORMAL_SCENE_QUALIFICATION';write_report()
        startup_support.report=report
        startup_support.select_gpu()
        report['gpu_work_started']=True;write_report()
        admitted=report['selected_gpu']
        (OUT/'simulator-admission.json').write_text(json.dumps(admitted,indent=2)+'\n')
        env={**os.environ,'LINGBOT_PANEL_OUT':str(OUT),'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
            'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','LINGBOT_ENABLE_FAST_MOE':'0',
            'CUDA_VISIBLE_DEVICES':admitted['uuid'],'LINGBOT_PHYSICAL_GPU':str(admitted['index']),
            'PYTHONPATH':str(OUT)+':'+str(PROJECT/'lingbot-vla-v2')}
        sim_env={**env,'OPEN3D_CPU_RENDERING':'true','PYTHONPATH':str(OUT)+':'+str(PROJECT/'RoboTwin')}
        selected={};probes=[];probe_deadline=time.monotonic()+480
        for seed in range(8):
            remaining=probe_deadline-time.monotonic()
            if remaining<=0:break
            result=scene_run(seed,OUT/'scene-probes'/f'seed-{seed:02d}',sim_env,seconds=remaining)
            probes.append(result)
            report['scene_selection']=dict(method='First stable clean seed for each arm, seeds 0-7; typed unstable setup rejection only; no oracle/action/success filtering',probes=probes,selected=selected)
            write_report()
            if result.get('status')=='REJECTED_UNSTABLE_SETUP':
                print('Rejected unstable setup seed:',seed,'reason:',result['reason'],flush=True)
                continue
            side=result['requested_arm']
            if side not in ('left','right'):raise RuntimeError('Invalid scene arm')
            selected.setdefault(side,result)
            write_report()
            if len(selected)==2:break
        if set(selected)!={'left','right'}:raise RuntimeError('Bounded normal scene search did not provide both arms')
        report.update(normal_scene_qualified=True,phase='POLICY_LOADING',policy_started=True);write_report()
        print('Normal simulator processes qualified both arms; loading retained +200 policy on the same GPU.',flush=True)
        policy=spawn(OUT/'policy_worker.py',OUT/'policy.log',env)
        deadline=time.monotonic()+600
        while not (OUT/'policy-ready.json').is_file():
            if policy.poll() is not None:
                path=OUT/'policy/report.json';inner=json.loads(path.read_text()) if path.exists() else {}
                report.update({key:inner[key] for key in ('error','selected_gpu','base_weight_load_seconds','cases') if key in inner})
                raise RuntimeError(inner.get('error','Policy exited before ready; inspect policy.log'))
            if time.monotonic()>deadline:raise RuntimeError('Policy startup exceeded ten minutes')
            time.sleep(.5)
        ready=json.loads((OUT/'policy-ready.json').read_text())
        if not ready['ready'] or ready['baseline_replays']!=24:raise RuntimeError('Policy replay/identity incomplete')
        if ready['gpu_uuid']!=admitted['uuid'] or ready['physical_gpu']!=admitted['index']:
            raise RuntimeError('Policy GPU differs from normally qualified simulator GPU')
        report.update(policy_identity=ready,baseline_replays=24,selected_gpu=dict(index=ready['physical_gpu'],uuid=ready['gpu_uuid']))
        report.update(model_loaded=True,policy_loaded=True,phase='EPISODES');write_report()
        print('Retained source +200 policy ready; 24 exact source replays. Starting four bounded episodes.',flush=True)
        for side in ('left','right'):
            for noise in (777,888):
                seed=selected[side]['scene_seed'];output=OUT/'episodes'/f'{side}-seed-{seed:02d}-noise-{noise}'
                print('Starting episode:',side,'scene',seed,'noise',noise,'cap 200 actions / six minutes.',flush=True)
                actual=scene_run(seed,output,sim_env,noise=noise)
                if actual['requested_arm']!=side or actual['model_id']!=selected[side]['model_id']:raise RuntimeError('Clean scene identity changed')
                result=json.loads((output/'episode-report.json').read_text())
                if result['status']!='COMPLETE':raise RuntimeError('Episode incomplete: '+str(output))
                if result['policy_checkpoint']!=ready['checkpoint']:raise RuntimeError('Episode checkpoint differs')
                if not (output/'observer.mp4').is_file() or not (output/'physics-telemetry.npz').is_file():raise RuntimeError('Episode evidence missing')
                report['episodes'].append(dict(directory=str(output.relative_to(OUT)),**result));write_report()
                print('Episode result:',side,noise,'task_success=',result['task_success'],'stop=',result['stop_reason'],flush=True)
        report.update(status='COMPLETE',task_successes=sum(e['task_success'] for e in report['episodes']),
            task_success_denominator=4,quality_claim='Descriptive only: two scenes, no oracle validity filter, 200-action/6-minute censoring')
    except BaseException as error:
        report.update(status='ERROR',error=str(error),traceback=traceback.format_exc());traceback.print_exc()
    finally:
        (OUT/'STOP_POLICY').touch()
        if policy is not None:
            try:policy.wait(timeout=4)
            except subprocess.TimeoutExpired:pass
        stopped=[stop(child) for child in reversed(children)]
        report['owned_children_stopped']=all(stopped) and all(child.poll() is not None for child in children)
        if report['status']=='COMPLETE':
            path=OUT/'policy/report.json';integrity=json.loads(path.read_text()) if path.exists() else {}
            report['policy_integrity']={key:integrity.get(key) for key in ('status','live_requests','parameters_unchanged','persistent_buffers_unchanged','model_step_counter_unchanged')}
            expected=sum(episode['chunks'] for episode in report['episodes'])
            if (integrity.get('status')!='COMPLETE' or integrity.get('live_requests')!=expected or
                    not all(integrity.get(key) is True for key in ('parameters_unchanged','persistent_buffers_unchanged','model_step_counter_unchanged'))):
                report.update(status='ERROR',error='Final policy integrity/shutdown report incomplete')
        try:report['original_files_unchanged']=all(digest(path)==expected for path,expected in protected.items()) if protected else False
        except OSError as error:report.update(original_files_unchanged=False,preservation_error=str(error))
        if not report['owned_children_stopped'] or not report['original_files_unchanged']:
            report.update(status='ERROR',error=report.get('error','Protected source or child cleanup check failed'))
        report['duration_seconds']=time.monotonic()-began;write_report()
    return 0 if report['status']=='COMPLETE' else 1

if __name__=='__main__':raise SystemExit(main())
