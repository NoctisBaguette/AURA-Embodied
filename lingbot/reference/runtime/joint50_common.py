"""Shared strict schemas, reviewed inputs and actual source camera extraction."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import time
import zipfile
import numpy as np
PROJECT = Path('/path/to/lingbot-workspace')
ROOT = PROJECT / 'data-preparation/joint50-competition-v3'
AUDIT = PROJECT / 'data-preparation/joint50-input-audit-v1/audit-GGa4CP2L'
AUDIT_SHA = '28160ec1754c70734f2c70a4a305db3af8265154953bf8ae10103f43adf8763e'
MODEL_PY = '/path/to/conda/envs/lingbotvla/bin/python'
SIM_PY = '/path/to/conda/envs/robotwin-sim/bin/python'
CAMERAS = ('observation.images.cam_high', 'observation.images.cam_left_wrist', 'observation.images.cam_right_wrist')
PILOT = ('click_bell', 'lift_pot', 'handover_block', 'place_can_basket', 'open_laptop', 'stack_blocks_two', 'rotate_qrcode', 'pick_dual_bottles')

def require(value, message):
    if not value:
        raise RuntimeError(message)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 ** 2), b''):
            h.update(block)
    return h.hexdigest()

def plain(value):
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, dict):
        require(all((isinstance(key, str) for key in value)), 'JSON object keys must be strings')
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite JSON value')
    require(value is None or isinstance(value, (str, int, float, bool)), 'Unsupported JSON type: ' + str(type(value)))
    return value

def atomic_json(path, value):
    path = Path(path)
    stage = path.with_name(path.name + '.partial')
    with stage.open('w', encoding='utf-8') as handle:
        json.dump(plain(value), handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(stage, path)

def reviewed_inputs(check_files=True):
    archive = AUDIT / 'joint50-input-audit.zip'
    require(digest(archive) == AUDIT_SHA, 'Reviewed input audit archive changed')
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None and bundle.read('worker.exit').strip() == b'0', 'Input audit archive invalid')
        for name in ('report.json', 'proposed-schedule.npz', 'joint50_data_audit.py'):
            require(hashlib.sha256(bundle.read(name)).hexdigest() == digest(AUDIT / name), 'Input audit payload changed: ' + name)
    report = json.loads((AUDIT / 'report.json').read_text(encoding='utf-8'))
    require(report['status'] == 'COMPLETE' and len(report['episodes']) == 2500 and (len(report['task_summaries']) == 50) and (report['first_text_arm_conflicts'] == 2), 'Unexpected reviewed audit scope')
    require(report['protected_source_and_metadata_hashes_unchanged'] and report['numeric_file_stats_unchanged'], 'Input audit integrity failed')
    conflicts = {(entry['task'], entry['episode']) for entry in report['episodes'] if entry['first_explicit_arm_conflict']}
    require(conflicts == {('adjust_bottle', 0), ('place_bread_basket', 5)}, 'Reviewed conflict set changed')
    require(digest(AUDIT / 'proposed-schedule.npz') == report['schedule']['sha256'], 'Schedule digest differs')
    with np.load(AUDIT / 'proposed-schedule.npz', allow_pickle=False) as values:
        schedule = {name: values[name].copy() for name in values.files}
    require(schedule['global_indices'].shape == (100000,) and schedule['global_indices'].dtype == np.int64, 'Invalid schedule shape/type')
    require(np.all(np.bincount(schedule['task_indices'], minlength=50) == 2000) and np.all(np.bincount(schedule['task_indices'][schedule['forced_episode_start']], minlength=50) == 400), 'Schedule balance differs')
    if check_files:
        for name, expected in report['protected_files'].items():
            require(digest(name) == expected, 'Protected source/metadata changed: ' + name)
        for item in report['numeric_file_identity_checks']:
            stat = Path(item['path']).stat()
            require((stat.st_size, stat.st_mtime_ns) == (item['bytes'], item['mtime_ns']), 'Numeric data changed since audit')
    return (report, schedule)

def results_document(template, records, checkpoint):
    result = json.loads(json.dumps(template))
    for setting in ('clean', 'randomized'):
        require(len(result['results'][setting]) == 50, 'Official template task count differs')
        for task in result['results'][setting]:
            result['results'][setting][task] = dict(attempts=0, successes=0)
    seen = set()
    for record in records:
        require(record['status'] == 'COMPLETE' and record['checkpoint'] == checkpoint, 'Mixed checkpoint or incomplete outcome')
        require(isinstance(record['task_success'], (bool, np.bool_)), 'Task success must be a boolean')
        key = (record['task'], record['setting'], int(record['scene_seed']))
        require(key not in seen, 'Duplicate task/setting/scene result')
        seen.add(key)
        cell = result['results'][record['setting']][record['task']]
        cell['attempts'] += 1
        cell['successes'] += int(bool(record['task_success']))
    return result

def source_frames(output, report):
    """Decode existing demonstration images, not visualizations from joint values."""
    import pyarrow.parquet as pq
    from PIL import Image
    corpus = json.loads((PROJECT / 'data-preparation/clean50-conversion/corpus-report.json').read_text(encoding='utf-8'))
    tasks = {task['task']: task for task in corpus['tasks']}
    selected = [entry for entry in report['episodes'] if entry['first_explicit_arm_conflict'] or (entry['task'] in PILOT and entry['episode'] == 0)]
    offsets = np.r_[0, np.cumsum([task['training_pairs'] for task in corpus['tasks']])]
    output.mkdir(parents=True, exist_ok=True)
    receipts = []
    for task in sorted({entry['task'] for entry in selected}):
        own = [entry for entry in selected if entry['task'] == task]
        wanted = {}
        for entry in own:
            for frame in sorted({0, entry['rows'] // 2, entry['rows'] - 1}):
                local = entry['global_start'] - int(offsets[entry['task_index']]) + frame
                wanted[local] = (entry, frame)
        dataset = Path(tasks[task]['dataset'])
        for path in sorted((dataset / 'data').glob('chunk-*/file-*.parquet')):
            for batch in pq.ParquetFile(path).iter_batches(batch_size=128, columns=['index', *CAMERAS]):
                values = batch.to_pydict()
                for index, local in enumerate(values['index']):
                    if local not in wanted:
                        continue
                    entry, frame = wanted.pop(local)
                    for camera in CAMERAS:
                        value = values[camera][index]
                        require(isinstance(value, dict) and value.get('bytes'), 'Expected embedded demonstration image bytes')
                        with Image.open(io.BytesIO(value['bytes'])) as image:
                            rgb = image.convert('RGB')
                            require(rgb.size == (320, 240), 'Source camera size differs')
                            name = f"{task}-e{entry['episode']:02d}-f{frame:04d}-{camera.rsplit('.', 1)[-1]}.png"
                            rgb.save(output / name)
                        receipts.append(dict(task=task, episode=entry['episode'], frame=frame, camera=camera, file=name, sha256=digest(output / name), source_text=entry['first_text'], training_text=entry['selected_text'] if entry['first_explicit_arm_conflict'] else entry['first_text']))
                if not wanted:
                    break
            if not wanted:
                break
        require(not wanted, 'Missing exact source image rows: ' + task)
    atomic_json(output / 'frames.json', dict(scope='Actual decoded clean demonstrations, three cameras; no simulator/policy run', frames=receipts))
    return len(receipts)
