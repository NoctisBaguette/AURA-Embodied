"""Wait only around the retained pre-model same-GPU selector, never model loading."""
from datetime import datetime
import json
import math
from pathlib import Path
import time
from joint50_common import atomic_json, require
RESOURCE_ERRORS = {'No A100 with at least 60 GiB free and at most 10% utilization in all three samples; no GPU work was started.', 'Selected GPU lost free-memory headroom or became busy; stopped before model load.'}

def configure(home, job, admitted):
    status = json.loads((Path(job) / 'status.json').read_text(encoding='utf-8'))
    deadline = datetime.fromisoformat(status['deadline_utc']).timestamp()
    require(math.isfinite(deadline) and deadline <= time.time() + 12 * 3600 + 5, 'Invalid original admission deadline')
    value = dict(schema_version=1, uuid=admitted['uuid'], index=admitted['index'], deadline_epoch=deadline, scope='Original watcher deadline; waiting never resets the 12-hour admission window')
    atomic_json(Path(home) / 'policy-admission-config.json', value)
    return value

def install(core, admitted, home, job, *, clock=time.time, sleep=time.sleep, poll_seconds=60):
    """Retain exact selector thresholds/samples/final check and qualified UUID filter."""
    home = Path(home)
    job = Path(job)
    config = json.loads((home / 'policy-admission-config.json').read_text(encoding='utf-8'))
    require(config['schema_version'] == 1 and (config['uuid'], config['index']) == (admitted['uuid'], admitted['index']), 'Policy admission configuration differs from qualified GPU')
    deadline = config['deadline_epoch']
    require(isinstance(deadline, (int, float)) and math.isfinite(deadline) and (deadline <= clock() + 12 * 3600 + 5), 'Invalid policy admission deadline')
    path = home / 'policy/gpu-admission.json'
    marker = home / 'policy/model-load-started.json'
    original_select = core.select_gpu
    original_trace = core.install_load_trace
    receipt = dict(schema_version=1, uuid=admitted['uuid'], index=admitted['index'], deadline_epoch=deadline, attempts=0, model_load_started=False, status='PENDING')

    def publish(status, **values):
        receipt.update(values, status=status, updated_epoch=clock())
        atomic_json(path, receipt)

    def cancelled():
        return (job / 'CANCEL').exists() or (home / 'STOP_POLICY').exists()

    def select():
        require(not marker.exists(), 'A model-load stage may not re-enter GPU admission')
        while True:
            if cancelled():
                publish('CANCELLED')
                raise RuntimeError('Policy GPU wait cancelled before model load')
            if clock() >= deadline:
                publish('EXPIRED')
                raise RuntimeError('Original GPU admission deadline expired before model load')
            receipt['attempts'] += 1
            publish('CHECKING')
            try:
                original_select()
            except RuntimeError as error:
                if str(error) not in RESOURCE_ERRORS or marker.exists() or 'selected_gpu' in core.report or ('base_weight_load_seconds' in core.report):
                    publish('ERROR', error=str(error))
                    raise
                publish('WAITING', error=str(error), gpu_snapshots=core.report.get('gpu_snapshots', []), gpu_final_recheck=core.report.get('gpu_final_recheck'))
                print('WAITING_POLICY_GPU: qualified UUID', admitted['uuid'], 'is temporarily ineligible; no model load. Next check in', poll_seconds, 'seconds.', flush=True)
                until = min(deadline, clock() + poll_seconds)
                while clock() < until and (not cancelled()):
                    sleep(min(1, max(0, until - clock())))
                continue
            require((core.report['selected_gpu']['uuid'], core.report['selected_gpu']['index']) == (admitted['uuid'], admitted['index']), 'Policy selector changed the qualified GPU')
            if clock() >= deadline:
                publish('EXPIRED')
                raise RuntimeError('Original GPU admission deadline expired during final checks')
            publish('ADMITTED', admitted_epoch=clock(), gpu_snapshots=core.report.get('gpu_snapshots', []), gpu_final_recheck=core.report.get('gpu_final_recheck'))
            return

    def trace():
        require(receipt['status'] == 'ADMITTED' and (not marker.exists()), 'Model load must follow admitted GPU')
        value = dict(model_load_started=True, started_epoch=clock(), uuid=admitted['uuid'], index=admitted['index'])
        atomic_json(marker, value)
        publish('MODEL_LOADING', **value)
        return original_trace()
    core.select_gpu = select
    core.install_load_trace = trace

def wait_baseline(home, policy, config, check_cancel, state, save, *, clock=time.time, sleep=time.sleep):
    home = Path(home)
    ready = home / 'baseline-ready.json'
    receipt_path = home / 'policy/gpu-admission.json'
    last = 0
    while not ready.exists():
        check_cancel()
        if policy.poll() is not None:
            report = home / 'policy/report.json'
            detail = json.loads(report.read_text(encoding='utf-8')).get('error') if report.exists() else None
            raise RuntimeError('Policy process exited: ' + str(detail or 'inspect policy.log and policy/report.json'))
        receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
        if receipt:
            require((receipt['uuid'], receipt['index']) == (config['uuid'], config['index']), 'Policy GPU wait identity differs')
        waiting = receipt.get('status') in (None, 'PENDING', 'CHECKING', 'WAITING')
        state['phase'] = 'WAITING_POLICY_GPU' if waiting else 'BASELINE_POLICY_LOADING'
        state['policy_gpu_admission'] = receipt
        limit = config['deadline_epoch'] + 15 if waiting else receipt.get('admitted_epoch', config['deadline_epoch']) + 900
        require(clock() < limit, 'Baseline GPU admission/loading stage deadline exceeded')
        if clock() - last > 5:
            save()
            last = clock()
        sleep(0.5)
    return json.loads(ready.read_text(encoding='utf-8'))
