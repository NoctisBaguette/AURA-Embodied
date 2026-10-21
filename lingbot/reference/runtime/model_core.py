import ast
import copy
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path

ROOT = Path('/path/to/lingbot-workspace')
RUN = ROOT / 'data-preparation/clean50-overnight-training-v2/run-20261007-174216-YxxMEO'
OLD = ROOT / 'bridge-smoke/trained-policy-10000/run-GrKJVjis'
OUT = Path(os.environ['LINGBOT_MOTION_OUT'])
ARM = list(range(6)) + list(range(7, 13))
CAMERAS = [('head_camera', 'observation.images.cam_high'),
           ('left_camera', 'observation.images.cam_left_wrist'),
           ('right_camera', 'observation.images.cam_right_wrist')]
report={'status':'RUNNING','cases':[],'preprocessing_comparisons':[], 'scope':'One phase-balanced +200 continuation; no simulation.'}
GENERALIZATION = ROOT / 'data-preparation/padding-generalization/run-9aOE63Yu'
PARITY_FILES = {
    'report.json': 'ef0fd58eb17f0f70373362399d03d433ac9e73b7b47d2598813feb381bed2fc8',
    'episode-00-frame-000-input.npz': '5dcee45093b3fe8bb880566e10ec3ce33e104bf393ae8594c931c1bd3276bcbc',
    'production_10000-episode-00-frame-000-analytic_padding-seed-777-10-steps.npz':
        '03f5ff77d0f33ba39fc22a8eca1d281f6797ce4ab2433362ba6b71b3c9c95b9c',
}
from contextlib import contextmanager
TRAIN_EPISODES=()
EVAL_EPISODES=()
_BOTTLE_AUDIT=None
FIRST_ACTION_WEIGHT=5.0




def require(value, message):
    if not value:
        raise RuntimeError(message)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def atomic_report():
    temporary = OUT / 'report.json.partial'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    os.replace(temporary, OUT / 'report.json')

def gpu_snapshot():
    listing = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,name,memory.free,utilization.gpu',
                                       '--format=csv,noheader,nounits'], text=True)
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory',
                                   '--format=csv,noheader,nounits'], text=True)
    processes = {}
    for row in csv.reader(io.StringIO(apps)):
        if not row or not any(value.strip() for value in row):
            continue
        require(len(row) == 3, 'Unexpected GPU process inventory; selection stopped.')
        uuid, pid, memory = [value.strip() for value in row]
        processes.setdefault(uuid, []).append({'pid': int(pid),
            'used_mib': int(memory) if memory.isdecimal() else None})
    devices = {}
    for line in csv.reader(io.StringIO(listing)):
        index, uuid, name, free, busy = [v.strip() for v in line]
        resident = processes.get(uuid, [])
        resident_mib = (sum(row['used_mib'] for row in resident)
                        if all(row['used_mib'] is not None for row in resident) else None)
        devices[uuid] = {'index': int(index), 'uuid': uuid, 'name': name,
                         'free_mib': int(free), 'utilization': int(busy),
                         'occupied': bool(resident), 'resident_mib': resident_mib,
                         'resident_processes': resident}
    return devices

def eligible(device):
    # The reused builder caps this process's allocator at 52 GiB. Leave an
    # additional 8 GiB free at selection; resident memory is already excluded
    # from nvidia-smi's free-memory measurement.
    return ('A100' in device['name'] and device['free_mib'] >= 60 * 1024
            and device['utilization'] <= 10)

def select_gpu():
    snapshots = []
    for index in range(3):
        snapshots.append(gpu_snapshot())
        if index < 2:
            time.sleep(2)
    shared = set(snapshots[0]).intersection(*[set(s) for s in snapshots[1:]])
    options = [snapshots[-1][uuid] for uuid in shared
               if all(eligible(s[uuid]) for s in snapshots)]
    report['gpu_snapshots'] = [list(s.values()) for s in snapshots]
    report['gpu_selection_policy'] = {
        'minimum_free_gib': 60, 'allocator_cap_gib': 52,
        'selection_headroom_gib': 8, 'maximum_utilization_percent': 10,
        'samples': 3, 'interval_seconds': 2, 'final_recheck': True,
        'resident_memory_cutoff_mib': None,
        'reservation': False,
    }
    require(options, 'No A100 with at least 60 GiB free and at most 10% utilization in all three samples; no GPU work was started.')
    chosen = max(options, key=lambda row: (
        not row['occupied'], min(s[row['uuid']]['free_mib'] for s in snapshots),
        -max(s[row['uuid']]['utilization'] for s in snapshots), -row['index']))
    fresh = gpu_snapshot().get(chosen['uuid'])
    report['gpu_final_recheck'] = fresh
    require(fresh is not None and fresh['index'] == chosen['index'] and eligible(fresh),
            'Selected GPU lost free-memory headroom or became busy; stopped before model load.')
    chosen = fresh
    os.environ['CUDA_VISIBLE_DEVICES'] = chosen['uuid']
    os.environ['LINGBOT_PHYSICAL_GPU'] = str(chosen['index'])
    report['selected_gpu'] = chosen
    report['quiet_gpu_sharing'] = chosen['occupied']
    print('Selected currently quiet physical GPU:', chosen['index'], flush=True)
    print('Free memory:', round(chosen['free_mib'] / 1024, 2),
          'GiB; allocator cap 52 GiB; selection headroom at least 8 GiB.', flush=True)
    print('Existing process memory:', chosen['resident_mib'],
          'MiB; existing processes left running. Quiet samples are not a reservation.', flush=True)

def verified_prefix(source):
    # Reuse only the already-tested loading and prediction functions. No HTTP server is started.
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'predict']
    require(len(functions) == 1, 'Saved inference predict function missing or duplicated')
    end = functions[0].end_lineno
    nodes = [node for node in tree.body if node.end_lineno <= end]
    require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'HTTPServer' for top in nodes for node in ast.walk(top)),
            'Unexpected HTTP server startup in reusable inference prefix')
    prefix = ast.Module(body=nodes, type_ignores=[])
    return ast.fix_missing_locations(prefix)

def statistics(values, reference, state):
    import numpy as np
    require(values.shape == reference.shape == (50, 14), 'Unexpected action comparison shape')
    require(np.isfinite(values).all() and np.isfinite(reference).all(), 'Nonfinite commands')
    arm_error = values[:, ARM].astype('float64') - reference[:, ARM]
    deltas = np.diff(values[:, ARM].astype('float64'), axis=0)
    reversals = ((deltas[:-1] * deltas[1:] < 0) &
                 (abs(deltas[:-1]) > .001) & (abs(deltas[1:]) > .001)).sum(axis=0)
    return {
        'arm_target_rmse_degrees': float(np.rad2deg(np.sqrt(np.mean(arm_error ** 2)))),
        'left_arm_target_rmse_degrees': float(np.rad2deg(np.sqrt(np.mean(arm_error[:, :6] ** 2)))),
        'right_arm_target_rmse_degrees': float(np.rad2deg(np.sqrt(np.mean(arm_error[:, 6:] ** 2)))),
        'gripper_target_mean_absolute_error': float(np.mean(abs(values[:, [6, 13]] - reference[:, [6, 13]]))),
        'largest_adjacent_joint_target_change_degrees': float(np.rad2deg(abs(deltas).max())),
        'median_per_step_largest_joint_change_degrees': float(np.rad2deg(np.median(abs(deltas).max(axis=1)))),
        'joint_target_second_difference_rms_degrees': float(np.rad2deg(np.sqrt(np.mean(np.diff(deltas, axis=0) ** 2)))),
        'direction_reversals_over_0_001_radians': reversals.tolist(),
        'initial_largest_arm_target_change_degrees': float(np.rad2deg(abs(values[0, ARM] - state[ARM]).max())),
        'left_gripper_min_max': [float(values[:, 6].min()), float(values[:, 6].max())],
        'right_gripper_min_max': [float(values[:, 13].min()), float(values[:, 13].max())],
    }

def comparison(left, right):
    import torch
    require(left.shape == right.shape, 'Training/live tensor shape differs')
    delta = (left.to(torch.float64) - right.to(torch.float64)).abs()
    return {'shape': list(left.shape), 'exact_equal': torch.equal(left, right),
            'maximum_absolute_difference': float(delta.max()), 'mean_absolute_difference': float(delta.mean())}

def instrument_loader_tree(source):
    """Preserve loader operations, adding timing only to four existing calls."""
    tree = ast.parse(source)
    dispatch, = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_dispatch_parameter']
    iterator_class, = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'StateDictIterator']
    iterator, = [n for n in iterator_class.body if isinstance(n, ast.FunctionDef) and n.name == '__iter__']
    counts = {'safetensors_get_tensor_lazy': 0, 'cpu_to_gpu_including_mmap_faults': 0, 'gpu_copy': 0}

    class Calls(ast.NodeTransformer):
        def visit_Call(self, node):
            node = self.generic_visit(node)
            if not isinstance(node.func, ast.Attribute):
                return node
            stage = None
            if node.func.attr == 'get_tensor' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'f':
                stage, label = 'safetensors_get_tensor_lazy', 'key'
            elif node.func.attr == 'to' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'tensor':
                stage, label = 'cpu_to_gpu_including_mmap_faults', '_lingbot_trace_key'
            elif node.func.attr == 'copy_':
                stage, label = 'gpu_copy', '_lingbot_trace_key'
            if stage is None:
                return node
            counts[stage] += 1
            arguments = ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
            wrapped = ast.Call(func=ast.Name(id='_lingbot_trace_call', ctx=ast.Load()),
                               args=[ast.Constant(stage), ast.Name(id=label, ctx=ast.Load()),
                                     ast.Lambda(args=arguments, body=node)], keywords=[])
            return ast.copy_location(wrapped, node)

    dispatch = Calls().visit(dispatch)
    # Save the full checkpoint key before the existing function shortens it to a leaf name.
    dispatch.body.insert(1, ast.parse('_lingbot_trace_key = name').body[0])
    iterator = Calls().visit(iterator)
    require(counts == {'safetensors_get_tensor_lazy': 1, 'cpu_to_gpu_including_mmap_faults': 1, 'gpu_copy': 2},
            'Loader operation structure changed; timing instrumentation stopped.')
    return ast.fix_missing_locations(ast.Module(body=[dispatch, iterator], type_ignores=[]))

def install_load_trace():
    import faulthandler
    import resource
    import signal
    import threading
    import torch
    from lingbotvla.models import module_utils as module

    source = Path(module.__file__)
    require(digest(source) == '95eb1b970829ead088792bf6c6f0e32b349399fc36e6988b6a91e25f2ac2c595',
            'Installed loader differs from the uploaded diagnostic; stopped before model allocation.')
    shutil.copyfile(source, OUT / 'installed-module_utils.py')
    payload = source.read_text()
    tree = instrument_loader_tree(payload)
    report['loader_source_sha256'] = digest(source)
    report['phase'] = 'transfer baseline'
    atomic_report()
    faulthandler.enable()
    faulthandler.dump_traceback_later(30, repeat=True)
    faulthandler.register(signal.SIGTERM, all_threads=True, chain=True)
    trace_file = (OUT / 'loader-trace.jsonl').open('a', buffering=1)
    totals = {}
    report['load_trace_summary'] = totals
    last_log = [0.0]

    def io_snapshot():
        usage = resource.getrusage(resource.RUSAGE_SELF)
        counters = dict(line.split(': ', 1) for line in Path('/proc/self/io').read_text().splitlines())
        return {'major_faults': usage.ru_majflt, 'read_bytes': int(counters['read_bytes']),
                'cpu_seconds': usage.ru_utime + usage.ru_stime}

    def traced(stage, key, operation):
        began = time.monotonic()
        before = io_snapshot()
        trace_file.write(json.dumps({'event': 'begin', 'stage': stage, 'key': key,
                                    'monotonic': began}) + '\n')
        if began - last_log[0] >= 10:
            report['phase'] = stage + ': ' + key
            atomic_report()
            print('LOAD:', report['phase'], flush=True)
            last_log[0] = began
        result = operation()
        if stage in ('cpu_to_gpu_including_mmap_faults', 'gpu_copy'):
            torch.cuda.synchronize()
        elapsed = time.monotonic() - began
        after = io_snapshot()
        event = {'event': 'end', 'stage': stage, 'key': key, 'seconds': elapsed,
                 'major_faults': after['major_faults'] - before['major_faults'],
                 'read_bytes': after['read_bytes'] - before['read_bytes'],
                 'cpu_seconds': after['cpu_seconds'] - before['cpu_seconds']}
        trace_file.write(json.dumps(event) + '\n')
        total = totals.setdefault(stage, {'calls': 0, 'seconds': 0.0, 'major_faults': 0, 'read_bytes': 0})
        total['calls'] += 1
        for field in ('seconds', 'major_faults', 'read_bytes'):
            total[field] += event[field]
        if elapsed >= 2:
            print(f'LOAD SLOW: {stage}: {key}: {elapsed:.2f}s; '
                  f'major faults={event["major_faults"]}; reads={event["read_bytes"]/1024**2:.1f} MiB', flush=True)
        return result

    # This uses ordinary allocated CPU data, so it has no checkpoint mmap faults.
    print('Checking three 64 MiB CPU-to-GPU transfers ...', flush=True)
    torch.cuda.set_device(0)
    cpu = torch.zeros(16 * 1024**2, dtype=torch.float32)
    report['transfer_baseline'] = []
    for index in range(3):
        torch.cuda.synchronize()
        began = time.monotonic()
        gpu = cpu.to('cuda')
        torch.cuda.synchronize()
        elapsed = time.monotonic() - began
        require(torch.count_nonzero(gpu).item() == 0, 'Transfer baseline data mismatch.')
        report['transfer_baseline'].append({'bytes': 64*1024**2, 'seconds': elapsed})
        print(f'Transfer {index+1}/3: {elapsed:.3f}s', flush=True)
        del gpu
    del cpu
    torch.cuda.empty_cache()
    atomic_report()

    originals = (module._dispatch_parameter, module.StateDictIterator.__iter__, module.load_model_weights)
    namespace = dict(module.__dict__)
    namespace['_lingbot_trace_call'] = traced
    exec(compile(tree, str(source) + ':timed', 'exec'), namespace)
    module._dispatch_parameter = namespace['_dispatch_parameter']
    module.StateDictIterator.__iter__ = namespace['__iter__']

    def stop_loading():
        # TERM is chained to the default action after a stack dump. The outer shell packages partial evidence.
        print('MODEL LOAD CUTOFF: five minutes; stopping this diagnostic worker.', flush=True)
        os.kill(os.getpid(), signal.SIGTERM)

    def loading(*args, **kwargs):
        report['phase'] = 'installed base-weight loader'
        atomic_report()
        print('Base-weight loading: five-minute cutoff; per-tensor timings enabled.', flush=True)
        deadline = threading.Timer(300, stop_loading)
        deadline.daemon = True
        deadline.start()
        began = time.monotonic()
        try:
            result = originals[2](*args, **kwargs)
            torch.cuda.synchronize()
            report['base_weight_load_seconds'] = time.monotonic() - began
            report['phase'] = 'base weights loaded; restoring original loader functions'
            atomic_report()
            print(f'BASE WEIGHTS LOADED: {report["base_weight_load_seconds"]:.2f}s', flush=True)
            return result
        finally:
            deadline.cancel()
            module._dispatch_parameter, module.StateDictIterator.__iter__, module.load_model_weights = originals

    module.load_model_weights = loading

    def cleanup():
        module._dispatch_parameter, module.StateDictIterator.__iter__, module.load_model_weights = originals
        trace_file.close()
        faulthandler.cancel_dump_traceback_later()
        require(digest(source) == report['loader_source_sha256'], 'Installed loader file changed during check.')

    return cleanup

def projection_parameters(model):
    import torch
    shapes = {
        'state_proj': (768, 55), 'action_in_proj': (768, 55),
        'action_out_proj': (55, 768), 'action_time_mlp_in': (768, 1536),
        'action_time_mlp_out': (768, 768),
    }
    chosen = {}
    all_parameters = dict(model.named_parameters())
    for module_name, shape in shapes.items():
        module = getattr(model.model, module_name)
        require(isinstance(module, torch.nn.Linear) and tuple(module.weight.shape) == shape,
                'Action projection layout differs: ' + module_name)
        for name, parameter in module.named_parameters():
            matches = [key for key, value in all_parameters.items() if value is parameter]
            require(len(matches) == 1, 'Projection parameter name is ambiguous: ' + module_name)
            require(parameter.dtype == torch.float32, 'Projection dtype differs.')
            chosen[matches[0]] = parameter
    expected_count = sum(out_size * (in_size + 1) for out_size, in_size in shapes.values())
    require(len(chosen) == 10 and sum(p.numel() for p in chosen.values()) == expected_count,
            'Unexpected action projection parameter count.')
    return chosen

def restore_capacity_start(model, adapter, projections, buffers, step):
    import torch
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from inference_cache_recovery import clear_visual_cache
    result = set_peft_model_state_dict(model, adapter)
    require(not result.unexpected_keys, 'Unexpected tiny-probe adapter keys.')
    actual = get_peft_model_state_dict(model)
    require(actual.keys() == adapter.keys() and
            all(torch.equal(actual[key].detach().cpu(), value) for key, value in adapter.items()),
            'Tiny-probe adapter did not restore exactly.')
    parameters = dict(model.named_parameters())
    live_buffers = dict(model.named_buffers())
    with torch.no_grad():
        for values, live in ((projections, parameters), (buffers, live_buffers)):
            for name, value in values.items():
                require(name in live and live[name].shape == value.shape and live[name].dtype == value.dtype,
                        'Restored tensor layout differs: ' + name)
                live[name].copy_(value.to(live[name].device))
                require(torch.equal(live[name].detach().cpu(), value), 'Restored tensor differs: ' + name)
    model.model.steps = step
    model.requires_grad_(False)
    model.eval()
    clear_visual_cache(model)

def choose_instruction(episode, instructions, states):
    import numpy as np
    require(isinstance(instructions, list) and instructions
            and all(isinstance(text, str) and text.strip() for text in instructions),
            'Invalid seen instruction list.')
    moving = [side for side, indices in [('left', list(range(6))), ('right', list(range(7, 13)))]
              if np.ptp(states[:, indices], axis=0).max() > 1e-5]
    if episode == 0:
        require(len(instructions) > 3 and moving == ['left']
                and instructions[3] == 'Use the left arm to pick up the smooth green plastic bottle from the table.',
                'Previously audited episode/instruction changed.')
        index, reason = 3, 'Previously audited arm-consistent small-probe instruction.'
    elif len(moving) == 1:
        side = moving[0]; opposite = 'right' if side == 'left' else 'left'
        candidates = [i for i, text in enumerate(instructions)
                      if side + ' arm' in text.lower() and opposite + ' arm' not in text.lower()]
        neutral = [i for i, text in enumerate(instructions)
                   if 'left arm' not in text.lower() and 'right arm' not in text.lower()]
        require(candidates or neutral, 'No source instruction consistent with recorded moving arm.')
        index = (candidates or neutral)[0]
        reason = 'First source instruction consistent with the recorded moving arm, or neutral wording.'
    else:
        index, reason = 0, 'First source instruction; both/neither arm moves in the recorded episode.'
    return index, instructions[index], moving, reason

def snapshot_branch(model):
    from peft import get_peft_model_state_dict
    persistent = set(model.state_dict())
    return dict(adapter={key: value.detach().cpu().clone() for key, value in get_peft_model_state_dict(model).items()},
        projections={key: value.detach().cpu().clone() for key, value in projection_parameters(model).items()},
        buffers={key: value.detach().cpu().clone() for key, value in model.named_buffers() if key in persistent},
        step=model.model.steps)

def branch_equals(model, saved):
    import torch
    actual = snapshot_branch(model)
    return actual['step'] == saved['step'] and all(actual[field].keys() == saved[field].keys()
        and all(torch.equal(actual[field][key], value) for key, value in saved[field].items())
        for field in ('adapter', 'projections', 'buffers'))

def select_capacity_parameters(model):
    parameters = dict(model.named_parameters())
    trainable = {name: value for name, value in parameters.items()
                 if '.lora_A.' in name or '.lora_B.' in name}
    require(len(trainable) == 288 and sum(p.numel() for p in trainable.values()) == 3833856,
            'Existing action-attention adapter layout differs.')
    projections = projection_parameters(model)
    if report['branch'] == 'lora_plus_projections':
        require(not (set(trainable) & set(projections)), 'Projection/adapter overlap.')
        trainable.update(projections)
    else:
        require(report['branch'] == 'lora_only', 'Unknown capacity branch.')
    for name, parameter in parameters.items():
        parameter.grad = None
        parameter.requires_grad_(name in trainable)
    report['trainable_parameters'] = sum(p.numel() for p in trainable.values())
    report['trainable_tensor_count'] = len(trainable)
    report['projection_parameter_names'] = sorted(projections)
    frozen = [(name, p, p._version) for name, p in parameters.items() if name not in trainable]
    require(frozen and all(not p.requires_grad for _, p, _ in frozen), 'Unselected parameters were not frozen.')
    return trainable, frozen

def probe_train_step(model, batch, trainable, optimizer):
    import torch
    started = time.monotonic()
    optimizer.zero_grad(set_to_none=True)
    result = model(**batch)
    require(len(result) == 11 and torch.isfinite(result[0]).item() and torch.isfinite(result[1]).item(),
            'Nonfinite action/MoE training loss; optimizer step stopped.')
    loss, action = result[:2]
    loss.backward()
    require(all(p.grad is not None for p in trainable.values()), 'Missing adapter gradient; optimizer step stopped.')
    grad_norm = torch.nn.utils.clip_grad_norm_(list(trainable.values()), 1., error_if_nonfinite=True)
    optimizer.step()
    torch.cuda.synchronize()
    return {'total_loss': float(loss.detach()), 'action_loss': float(action.detach()),
            'gradient_norm': float(grad_norm.detach()), 'seconds': time.monotonic()-started}

def validate_padding_reference():
    for name, expected in PARITY_FILES.items():
        require(digest(GENERALIZATION/name) == expected, 'Previous corrected inference evidence changed: '+name)
    saved = json.loads((GENERALIZATION/'report.json').read_text())
    require(saved['status'] == 'COMPLETE' and saved['worker_exit_code'] == 0,
            'Previous corrected inference run did not finish')

def verify_padding_helper(model, config, namespace):
    import numpy as np
    import torch
    from lingbot_zero_padding import sample_actions, VERSION
    from inference_cache_recovery import clear_visual_cache
    with np.load(GENERALIZATION/'episode-00-frame-000-input.npz', allow_pickle=False) as source:
        observation = {name: torch.from_numpy(source['training_'+name].copy()).unsqueeze(0).to(namespace['device'])
                       for name in ('images','img_masks','lang_tokens','lang_masks','state','image_grid_thw')}
        active = torch.from_numpy(source['active'].copy()).to(namespace['device'])
    observation['images'] = observation['images'].float(); observation['state'] = observation['state'].float()
    observation['image_grid_thw'] = observation['image_grid_thw'].long()
    with np.load(GENERALIZATION/'production_10000-episode-00-frame-000-analytic_padding-seed-777-10-steps.npz', allow_pickle=False) as source:
        noise = torch.from_numpy(source['noise'].copy()).to(namespace['device'])
        expected = source['states'][-1].copy()
    original_count = model.model.config.num_steps
    original_precision = torch.get_float32_matmul_precision()
    try:
        torch.set_float32_matmul_precision('highest')
        model.model.config.num_steps = 10
        with namespace['inference_cache_scope'](model, config):
            actual = sample_actions(model.model, observation, action_joint_mask=active, noise=noise)
        require(np.array_equal(actual.cpu().numpy(), expected),
                'Reusable zero-padding helper differs from previous corrected inference')
    finally:
        model.model.config.num_steps = original_count
        torch.set_float32_matmul_precision(original_precision)
        clear_visual_cache(model)
    report['zero_padding_helper'] = {'version': VERSION, 'sha256': digest(OUT/'lingbot_zero_padding.py'),
                                   'previous_corrected_output_bitwise_equal': True}
    print('Explicit zero-padding inference helper reproduces previous corrected targets exactly: PASS', flush=True)

def episode_item(dataset, row, entries, transform):
    import numpy as np
    import torch
    episode, frame, global_row = row; entry = entries[episode]
    value = dataset.getdata(global_row)
    if isinstance(value, list):
        require(len(value) == 1, 'Unexpected packed episode item'); value = value[0]
    # Preserve the full installed loader/collator contract, including optional
    # current/future image fields. Filter model inputs only after collation.
    item = {name:(entry.detach().cpu().clone() if torch.is_tensor(entry) else copy.deepcopy(entry))
            for name,entry in value.items()}
    item.update({name:value.clone() for name,value in entry['language'].items()})
    active = item['action_joint_mask']
    require(active.dtype == torch.bool and torch.equal(torch.nonzero(active).flatten(),
            torch.tensor(list(range(12))+[28,29])), 'Unexpected Aloha action mapping')
    require(item['actions'].shape == (50,55) and item['state'].shape == (55,), 'Invalid episode item shape')
    remaining = len(entry['states'])-frame-1
    pad = torch.arange(50) >= remaining
    require(torch.equal(item['action_is_pad'].bool(),pad), 'Temporal padding differs from raw episode end')
    require(torch.count_nonzero(item['actions'][:,~active]).item() == 0, 'Unused normalized targets are not zero')
    raw = transform.unapply({**copy.deepcopy(item), 'actions':item['actions'].clone()})
    expected = entry['states'][frame+1:min(frame+51,len(entry['states']))]
    require(np.allclose(raw['observation.state'].numpy(),entry['states'][frame],atol=2e-5,rtol=0)
            and np.allclose(raw['action'].numpy()[:len(expected)],expected,atol=2e-5,rtol=0),
            'Training state or valid next-frame actions differ from pinned source')
    require(torch.isfinite(item['state']).all().item() and torch.isfinite(item['actions']).all().item(),
            'Nonfinite training state/actions')
    return item

def episode_batch(items, device):
    import torch
    from lingbotvla.data import VLADataCollatorWithPacking
    collated = VLADataCollatorWithPacking()(items)
    names = ('images','img_masks','lang_tokens','lang_masks','state','image_grid_thw','actions','joint_mask','action_is_pad')
    batch = {name:collated[name].to(device) for name in names}
    for name in ('images','state','actions'): batch[name] = batch[name].float()
    batch['image_grid_thw'] = batch['image_grid_thw'].long()
    batch['action_is_pad'] = batch['action_is_pad'].bool()
    expected = torch.stack([item['action_joint_mask'] for item in items]).to(device)[:,None,:].expand(-1,50,-1)
    require(batch['actions'].shape == (len(items),50,55) and batch['joint_mask'].shape == expected.shape,
            'Collated action/mask shapes differ')
    require(torch.equal(batch['joint_mask'].bool(),expected), 'Stock active-joint mask differs')
    # Installed policy.forward combines this joint mask with action_is_pad.
    require((expected & ~batch['action_is_pad'][...,None]).any().item(), 'No valid action loss targets')
    return batch

def audit_bottle_archive(archive):
    """Inspect all raw joint sequences and source wording before allocating CUDA."""
    import h5py
    import numpy as np
    import re
    global TRAIN_EPISODES, EVAL_EPISODES, _BOTTLE_AUDIT
    entries = {}
    with zipfile.ZipFile(archive) as bundle:
        prefix = 'aloha-agilex_clean_50/'
        actual_ids = {int(match.group(1)) for name in bundle.namelist()
                      if (match := re.fullmatch(re.escape(prefix) + r'data/episode(\d+)\.hdf5', name))}
        require(actual_ids == set(range(50)), 'Pinned bottle archive must contain episodes 0-49')
        for episode in range(50):
            with h5py.File(io.BytesIO(bundle.read(prefix + f'data/episode{episode}.hdf5')), 'r') as h:
                states = np.asarray(h['joint_action/vector'][()], dtype=np.float32)
                require(states.ndim == 2 and states.shape[1] == 14 and len(states) > 52
                        and np.isfinite(states).all(), 'Invalid raw bottle joint sequence')
                require(np.allclose(states[:, [6, 13]], np.clip(states[:, [6, 13]], 0, 1), atol=1e-5, rtol=0),
                        'Raw gripper coordinate is outside the expected 0-1 range')
            descriptions = json.loads(bundle.read(prefix + f'instructions/episode{episode}.json'))['seen']
            index, instruction, moving, reason = choose_instruction(episode, descriptions, states)
            require(len(moving) == 1, 'Bottle correction requires exactly one recorded moving arm per episode')
            side = moving[0]; other = 'right' if side == 'left' else 'left'
            require(side + ' arm' in instruction.lower() and other + ' arm' not in instruction.lower(),
                    'No explicit source instruction consistent with recorded moving arm')
            contrary = [i for i, text in enumerate(descriptions) if other + ' arm' in text.lower()]
            entries[episode] = dict(episode=episode, states=states, instruction=instruction,
                instruction_index=index, moving_arms=moving, instruction_selection=reason,
                recorded_frames=len(states), converted_pairs=len(states)-1,
                first_source_instruction=descriptions[0], contrary_instruction_indices=contrary,
                first_source_instruction_contradicts_arm=(0 in contrary))
    by_arm = {side: [e for e in range(50) if entries[e]['moving_arms'] == [side]] for side in ('left', 'right')}
    require(all(len(ids) >= 7 for ids in by_arm.values()),
            'Need at least seven raw episodes for each arm; no model was loaded')
    training = {side: ids[:5] for side, ids in by_arm.items()}
    evaluation = {side: [e for e in ids if e not in training[side]][-2:] for side, ids in by_arm.items()}
    TRAIN_EPISODES = tuple(sorted(e for ids in training.values() for e in ids))
    EVAL_EPISODES = tuple(sorted(e for ids in evaluation.values() for e in ids))
    require(not set(TRAIN_EPISODES) & set(EVAL_EPISODES), 'Arm-balanced split overlaps')
    for e, value in entries.items():
        value['split'] = 'train' if e in TRAIN_EPISODES else 'evaluation' if e in EVAL_EPISODES else 'audit_only'
    details = {str(e): {k: v for k, v in value.items() if k != 'states'} for e, value in entries.items()}
    report['data_audit'] = dict(episodes=50, episodes_by_arm=by_arm, training_by_arm=training,
        evaluation_by_arm=evaluation, raw_annotation_conflicts=[e for e, v in entries.items() if v['first_source_instruction_contradicts_arm']],
        corrected_wording_scope='New isolated stage only; converted files and original checkpoint are preserved.',
        entries=details, completed_before_gpu_selection=True)
    (OUT / 'bottle-data-audit.json').write_text(json.dumps(report['data_audit'], indent=2) + '\n')
    _BOTTLE_AUDIT = entries
    print('Raw bottle audit: 50 episodes; left/right counts:', {side: len(ids) for side, ids in by_arm.items()}, flush=True)
    print('Training split: five episodes per arm:', training, flush=True)
    print('Evaluation split: two separate episodes per arm:', evaluation, flush=True)
    print('First source instructions contradicting recorded arm:', report['data_audit']['raw_annotation_conflicts'], flush=True)
    print('Balanced coverage and selected source wording: PASS before GPU allocation', flush=True)
    atomic_report()
    return entries

@contextmanager
def first_action_loss_scope(core, batch, first_weight=FIRST_ACTION_WEIGHT):
    """Reweight installed elementwise loss; preserve pooled-loss scale and masks."""
    import torch
    require(first_weight >= 1 and first_weight < 100, 'Invalid first-action loss weight')
    require(not getattr(core, '_first_action_weight_active', False), 'Nested first-action loss wrapper is unsupported')
    active = batch['joint_mask'].bool() & ~batch['action_is_pad'].bool()[..., None]
    require(active.shape == batch['actions'].shape and active.ndim == 3, 'Invalid weighted action loss mask')
    weights = torch.ones_like(batch['actions']); weights[:, 0, :] = first_weight
    valid_count = active.sum(); weighted_count = (active * weights).sum()
    require(valid_count.item() > 0, 'All-padded action loss cannot be trained')
    weights = weights * (valid_count.to(weights.dtype) / weighted_count)
    had_instance = 'forward' in core.__dict__; previous = core.__dict__.get('forward'); original = core.forward
    calls = [0]

    def forward(*args, **kwargs):
        result = original(*args, **kwargs)
        require(isinstance(result, tuple) and len(result) == 11 and result[0].shape == active.shape,
                'Installed unreduced action loss contract differs')
        require(torch.isfinite(result[0]).all().item(), 'Nonfinite unreduced action loss')
        calls[0] += 1
        return (result[0] * weights.to(device=result[0].device, dtype=result[0].dtype), *result[1:])

    core._first_action_weight_active = True; core.forward = forward
    try:
        yield
        require(calls[0] == 1, 'Actual direct-forward loss wrapper was not invoked exactly once')
    finally:
        if had_instance: core.forward = previous
        else: delattr(core, 'forward')
        delattr(core, '_first_action_weight_active')

def summarize_motion_stage(label):
    import numpy as np
    summaries = []
    metric_names = ('arm_target_rmse_degrees', 'left_arm_target_rmse_degrees', 'right_arm_target_rmse_degrees',
                    'initial_largest_arm_target_change_degrees', 'largest_adjacent_joint_target_change_degrees',
                    'joint_target_second_difference_rms_degrees', 'gripper_target_mean_absolute_error')
    for split in ('train', 'evaluation'):
        for side in ('left', 'right'):
            selected = [c for c in report['cases'] if c['label'] == label and c['split'] == split and c['moving_arms'] == [side]]
            require(selected, 'Missing arm-specific generated-target evaluation')
            summaries.append(dict(label=label, split=split, moving_arm=side, cases=len(selected),
                mean_per_case_metrics={k: float(np.mean([c['motion_metrics'][k] for c in selected])) for k in metric_names},
                max_initial_jump_degrees=max(c['motion_metrics']['initial_largest_arm_target_change_degrees'] for c in selected),
                max_adjacent_jump_degrees=max(c['motion_metrics']['largest_adjacent_joint_target_change_degrees'] for c in selected)))
    return summaries

def check_motion_gate(label):
    before = {r['moving_arm']: r for r in summarize_motion_stage('before') if r['split'] == 'evaluation'}
    after = {r['moving_arm']: r for r in summarize_motion_stage(label) if r['split'] == 'evaluation'}
    failures = []
    for side in ('left', 'right'):
        m = after[side]['mean_per_case_metrics']; baseline = before[side]['mean_per_case_metrics']
        other = 'right' if side == 'left' else 'left'
        checks = dict(arm_target_accuracy=(m['arm_target_rmse_degrees'] <= 15 and
            m['arm_target_rmse_degrees'] <= .9 * baseline['arm_target_rmse_degrees']),
            moving_arm_accuracy=m[side+'_arm_target_rmse_degrees'] <= 20,
            stationary_arm_accuracy=m[other+'_arm_target_rmse_degrees'] <= 5,
            first_target_continuity=(m['initial_largest_arm_target_change_degrees'] <= 5 and after[side]['max_initial_jump_degrees'] <= 10),
            adjacent_target_continuity=(m['largest_adjacent_joint_target_change_degrees'] <= 8 and after[side]['max_adjacent_jump_degrees'] <= 12),
            gripper_accuracy=m['gripper_target_mean_absolute_error'] <= .06)
        failures.extend(side + ':' + name for name, passed in checks.items() if not passed)
    return dict(status='PASS' if not failures else 'NOT_READY', label=label, failures=failures,
        scope='Provisional offline target-quality gate only; simulation, collisions and grasping remain untested.',
        thresholds=dict(mean_arm_rmse_degrees=15, minimum_rmse_improvement_fraction=.1,
            moving_arm_rmse_degrees=20, stationary_arm_rmse_degrees=5, mean_first_jump_degrees=5,
            max_first_jump_degrees=10, mean_adjacent_jump_degrees=8, max_adjacent_jump_degrees=12, gripper_mae=.06),
        score=max(after[side]['mean_per_case_metrics']['arm_target_rmse_degrees'] +
                  after[side]['mean_per_case_metrics']['initial_largest_arm_target_change_degrees'] for side in ('left', 'right')))

def evaluate_episode_rows(model, config, dataset, rows, entries, namespace, transform, label, completed):
    import numpy as np
    import torch
    from lingbot_zero_padding import sample_actions
    from inference_cache_recovery import clear_visual_cache
    model.eval(); cases = []
    for episode, frame, global_row in rows:
        item = episode_item(dataset,(episode,frame,global_row),entries,transform)
        require(not item['action_is_pad'].any().item(), 'Evaluation window is not fully valid')
        observation = {name:item[name].unsqueeze(0).to(namespace['device']) for name in
                       ('images','img_masks','lang_tokens','lang_masks','state','image_grid_thw')}
        observation['images'] = observation['images'].float(); observation['state'] = observation['state'].float()
        observation['image_grid_thw'] = observation['image_grid_thw'].long()
        reference = entries[episode]['states'][frame+1:frame+51]
        state = entries[episode]['states'][frame]
        for seed in EVALUATION_SEEDS:
            noise = torch.randn((1,50,55),device=namespace['device'],dtype=torch.float32,
                                generator=torch.Generator(device=namespace['device']).manual_seed(seed))
            with namespace['inference_cache_scope'](model,config):
                prediction = sample_actions(model.model,observation,
                    action_joint_mask=item['action_joint_mask'],noise=noise)
            commands = transform.unapply({**copy.deepcopy(item),'actions':prediction[0].cpu().clone()})['action'].numpy().copy()
            name = f'{label}-episode-{episode:02d}-frame-{frame:03d}-seed-{seed}.npz'
            np.savez_compressed(OUT/name, normalized=prediction.cpu().numpy(),commands=commands,
                raw_target=reference,raw_state=state,noise=noise.cpu().numpy(),active=item['action_joint_mask'].numpy(),
                normalized_target=item['actions'].numpy(),instruction=np.asarray(entries[episode]['instruction']))
            case = dict(label=label,completed_updates=completed,episode=episode,frame=frame,noise_seed=seed,
                denoising_steps=10,split=entries[episode]['split'],moving_arms=entries[episode]['moving_arms'],array_file=name,
                motion_metrics=statistics(commands,reference,state))
            cases.append(case);report['cases'].append(case)
            clear_visual_cache(model)
        print(f'{label}: episode {episode:02d} frame {frame:03d} ({entries[episode]["split"]}): '
              f'arm RMSE={case["motion_metrics"]["arm_target_rmse_degrees"]:.2f} deg; '
              f'max adjacent jump={case["motion_metrics"]["largest_adjacent_joint_target_change_degrees"]:.2f} deg',flush=True)
        atomic_report()
    require(len(cases) == len(rows)*len(EVALUATION_SEEDS), 'Incomplete split trajectory evaluation')
    return cases

def save_episode_checkpoint(model, optimizer, completed, consumed, source, schedule):
    import torch
    from peft import get_peft_model_state_dict
    from safetensors.torch import save_file
    from inference_common import to_cpu
    folder = OUT/'episode-checkpoints'/f'update-{completed:06d}'
    folder.parent.mkdir(exist_ok=True)
    stage = folder.with_name(folder.name+'.partial');stage.mkdir()
    adapter = {key:value.detach().cpu().contiguous().clone() for key,value in get_peft_model_state_dict(model).items()}
    projections = {key:value.detach().cpu().contiguous().clone() for key,value in projection_parameters(model).items()}
    require(all(torch.isfinite(value).all().item() for value in (*adapter.values(),*projections.values())),
            'Nonfinite trained tensors will not be saved')
    save_file(adapter,str(stage/'adapter_model.safetensors'))
    save_file(projections,str(stage/'projection_weights.safetensors'))
    model.peft_config['default'].save_pretrained(str(stage))
    persistent = set(model.state_dict())
    buffers = {key:value.detach().cpu().clone() for key,value in model.named_buffers() if key in persistent}
    torch.save({'completed_updates':completed,'samples_consumed':consumed,
        'optimizer':to_cpu(optimizer.state_dict()),'torch_cpu_rng':torch.get_rng_state(),
        'torch_cuda_rng':torch.cuda.get_rng_state(),'model_steps':model.model.steps,'persistent_buffers':buffers,
        'source_checkpoint':str(source),'schedule':schedule,'train_episodes':TRAIN_EPISODES,
        'evaluation_episodes':EVAL_EPISODES,'sampling_seed':SAMPLING_SEED},stage/'resume-state.pt')
    shutil.copyfile(source/'norm-stats-clean50.json',stage/'norm-stats-clean50.json')
    shutil.copyfile(OUT/'lingbot_zero_padding.py',stage/'lingbot_zero_padding.py')
    names = ('adapter_model.safetensors','projection_weights.safetensors','adapter_config.json','resume-state.pt',
             'norm-stats-clean50.json','lingbot_zero_padding.py')
    metadata = {'completed_updates':completed,'samples_consumed':consumed,'source_checkpoint':str(source),
                'files':{name:digest(stage/name) for name in names}}
    (stage/'checkpoint.json').write_text(json.dumps(metadata,indent=2)+'\n')
    os.replace(stage,folder)
    pointer = OUT/'latest-checkpoint.json.partial'
    pointer.write_text(json.dumps({'directory':str(folder),**metadata},indent=2)+'\n')
    os.replace(pointer,OUT/'latest-checkpoint.json')
    report.setdefault('saved_checkpoints',[]).append(str(folder))
    print('New isolated checkpoint:',folder,flush=True)
    return folder

def start_motion_gate(label):
    """Keep worst-case start/arm failures visible, beyond pooled phase averages."""
    import numpy as np
    base_gate = check_motion_gate(label)
    selected = [c for c in report['cases'] if c['label'] == label and c['split'] == 'evaluation']
    starts = [c for c in selected if c['frame'] == 0]
    require(len(starts) == len(EVAL_EPISODES) * len(EVALUATION_SEEDS), 'Incomplete start/seed evaluation')
    failures = list(base_gate['failures']); records = []
    for case in starts:
        side, = case['moving_arms']; other = 'right' if side == 'left' else 'left'
        with np.load(OUT / case['array_file'], allow_pickle=False) as arrays:
            command, state = arrays['commands'], arrays['raw_state']
        departures = {arm: float(np.sqrt(np.mean(np.square(
            command[:, indices] - state[indices]))) * 180 / np.pi)
            for arm, indices in [('left', list(range(6))), ('right', list(range(7, 13)))]}
        metrics = case['motion_metrics']
        checks = dict(requested_arm_dominant=departures[side] > departures[other],
            unwanted_arm=metrics[other + '_arm_target_rmse_degrees'] <= 5,
            moving_arm_fit=metrics[side + '_arm_target_rmse_degrees'] <= 20,
            first_jump=metrics['initial_largest_arm_target_change_degrees'] <= 10,
            adjacent_jump=metrics['largest_adjacent_joint_target_change_degrees'] <= 12)
        tag = f'ep{case["episode"]}-seed{case["noise_seed"]}'
        failures.extend(tag + ':' + name for name, passed in checks.items() if not passed)
        records.append(dict(episode=case['episode'], seed=case['noise_seed'], requested_arm=side,
                            departure_degrees=departures, checks=checks))
    base_gate.update(status='PASS' if not failures else 'NOT_READY', failures=failures,
        initial_seed_cases=records, requested_arm_dominant=sum(r['checks']['requested_arm_dominant'] for r in records),
        initial_cases=len(records),
        score=max(c['motion_metrics']['arm_target_rmse_degrees'] +
                  c['motion_metrics']['initial_largest_arm_target_change_degrees'] for c in starts))
    return base_gate

"""One phase-balanced continuation; source and confirmation never enter training."""
SOURCE_RUN = ROOT / 'data-preparation/bottle-start-state-correction-v1/run-WbDfVeGv'
SOURCE_STAGE = SOURCE_RUN / 'episode-checkpoints/update-000200'
SOURCE_FILES = {'report.json': '427fc81f357172ead5625e63f1c2a5a58ac0e272e98a92ca279257e7da1d900d', 'episode-checkpoints/update-000200/checkpoint.json': '2b46832fd17c6a5c27af256cf91bd2330dcb4d3a9809a91d2c317a1f7d548b6f', 'after-000200-episode-00-frame-000-seed-777.npz': 'e0b76e3b7f77ee93e0937fd82940b631d9e31bfee23e60db2d6eb69546fac52a', 'after-000200-episode-00-frame-000-seed-888.npz': '4f32f5fc947c13ee21a25df7c183690d1206ab451e1463eca26d3b29bed93a63', 'after-000200-episode-00-frame-000-seed-7.npz': '54e9145534b9e27d60222037cf430e2a6be3bd2c509ef299d0b8a026af059e93', 'after-000200-episode-00-frame-000-seed-20261016.npz': 'e57998d0320821a7c4ff1965976b942074340b3eb97b41f10e3efa50a6e976cd', 'after-000200-episode-00-frame-044-seed-777.npz': 'b42d0c5c67fa5490bde3ac31b6192bf6d74390c1b569b5714d97b6838f704610', 'after-000200-episode-00-frame-044-seed-888.npz': '00cd5a6fefdf80b187f1e666fe96cf7ab795fcdcd57fc8e0e99d803baabd4e4a', 'after-000200-episode-00-frame-044-seed-7.npz': '9dca4255862a85117f9d43d17163a18ec8a4f38ddc2f826ef54c8b1b4f4a4548', 'after-000200-episode-00-frame-044-seed-20261016.npz': 'd1164df2ab7045eac7cc7a3ac5425caf3aebfae83c8caf5c0130ac6d826bd20a', 'after-000200-episode-00-frame-089-seed-777.npz': '139dc34a926f3f7dceb723f03e995cc5b3df70ee8b4a0ca470502eff8dd5e445', 'after-000200-episode-00-frame-089-seed-888.npz': '4deabcf5db0b1f7265633278510bd10fac2b4921d66271e2ca9114e7134d066e', 'after-000200-episode-00-frame-089-seed-7.npz': '3af54a9dd9e8491f3d05179630d234cda67522a7f7fbeec282081bf62b4eeb7b', 'after-000200-episode-00-frame-089-seed-20261016.npz': 'e23ea1b9bdd14279b51cc25c68e588a08bd97f1d202f8e634159fe8cafbbb3a7', 'after-000200-episode-01-frame-000-seed-777.npz': '7ea9e3c04e349225645684c944d3d393cd7f82bae709b83139f7e02af96db369', 'after-000200-episode-01-frame-000-seed-888.npz': '67084d7cf41d8fcced7a383b7f4e16266fe735abf898b0da8b0941bc82fd61e8', 'after-000200-episode-01-frame-000-seed-7.npz': 'a9ce53082b701b8bf64006f882b0ebdf6ec95c66f5fd3875d3521f15ca733407', 'after-000200-episode-01-frame-000-seed-20261016.npz': '7f775932fda8371e9b3b898ceecfe947f22a910c16aa8246cb13b665c13fcc3c', 'after-000200-episode-01-frame-046-seed-777.npz': 'ae8cd96ecb58aeb472f258e6c9be05d58072a02d23849287f0de914317a2e863', 'after-000200-episode-01-frame-046-seed-888.npz': '9ffdb872b2674939678ea2d29e4957f91173d9aee64c6d78c162dd41126f7d3a', 'after-000200-episode-01-frame-046-seed-7.npz': 'b43a8a6e284ed575c463154c67f9aabe28a6547aabe5210be0a4f02990f89b72', 'after-000200-episode-01-frame-046-seed-20261016.npz': 'c2ccf8ac4ab8ce62431c7ad3cd7304f7ed47242dfc1823d15cf07f82279b2a66', 'after-000200-episode-01-frame-093-seed-777.npz': 'bca41d79df816b417ba182baea3669d954645349cdfa7014cb29760511092a7d', 'after-000200-episode-01-frame-093-seed-888.npz': '6cb64c8dfb27ebe46e1f06fb611dac7b587c13057e4c13ce5391e90f4f56bd26', 'after-000200-episode-01-frame-093-seed-7.npz': '00814154728e9c8e2287c4830c53ce1ce336cb93add61f0bb511a4a12deaea1b', 'after-000200-episode-01-frame-093-seed-20261016.npz': '438c5d44689bdcf4627417970dd8d0d80093e2db72a2e43b8ef365f4e81001f3', 'after-000200-episode-02-frame-000-seed-777.npz': '414e3defe0ad1a919f927b4b8d6ac29e5c0152c1c51a9270802166809885bf04', 'after-000200-episode-02-frame-000-seed-888.npz': 'bdc3459fb2f4603e42a46d0dbb3b22fe1859d0970b05d0f9f004e85861069620', 'after-000200-episode-02-frame-000-seed-7.npz': 'e261f36262a7501b502dcb8b69de3681fe2172b10ca41f8120125f75f7c881ce', 'after-000200-episode-02-frame-000-seed-20261016.npz': '196c43a7252fa62ad88d813e6a9283ec5583b96cd7080576af1bea460e71d57d', 'after-000200-episode-02-frame-049-seed-777.npz': '7653f6b415308e9f7c7c024477e9ee0123c35b8b16f7dbf814b42d6f74d7621f', 'after-000200-episode-02-frame-049-seed-888.npz': 'f6e8456dceeac2c262181351947628917c3efcbcef3cfffb56091624ee56bd5c', 'after-000200-episode-02-frame-049-seed-7.npz': 'b0e1f32a2798fa5e24d4cf7ba7e6473276666aa61d19ae05181299ca5ce43785', 'after-000200-episode-02-frame-049-seed-20261016.npz': '841a359c92902fd8441cf7a32fc218a2c2b581fd8648a3c242373a73aafee228', 'after-000200-episode-02-frame-099-seed-777.npz': 'b17ad0b0b60d217ff64bd53385d76a71ebf20b270ba0f7033732372c809d2f9d', 'after-000200-episode-02-frame-099-seed-888.npz': '08b21d9e27b538c091200cd23f891470bd608a5dcdd983cf70c667ad1243278c', 'after-000200-episode-02-frame-099-seed-7.npz': '51bba302b00bf95987436790790d6ddfdad334b972d8431b7c4c87ee221b1b53', 'after-000200-episode-02-frame-099-seed-20261016.npz': 'ac0fc1927415aa420c3044478cbe50615d2f7a42b771b9c2b0886d2fba3bab9d', 'after-000200-episode-03-frame-000-seed-777.npz': 'e0bcae0122112cbd6867d2d44b3848fbd0920e7c3c8e271d3182853bb423568b', 'after-000200-episode-03-frame-000-seed-888.npz': '20fc48dbb1bf71a1c261c0e1e4aa483774758b8e241d3f0728dbc9282d9b2413', 'after-000200-episode-03-frame-000-seed-7.npz': 'c7412259f865c2f8dacc9a91f14c033f64105a708583cb3f66014a382bcfa475', 'after-000200-episode-03-frame-000-seed-20261016.npz': 'c776e7b3bd99491301d764a073fba3519759ca16659f6b6ecd1343d354b536cb', 'after-000200-episode-03-frame-049-seed-777.npz': '95c72169b31a327d14b7c335f54f81856d61a3fa1e19e587a105b6ec6ba3cbe9', 'after-000200-episode-03-frame-049-seed-888.npz': 'b3214215d3df02a95b1d9c8878b245788ae99006786f168424f6c803ef2b0183', 'after-000200-episode-03-frame-049-seed-7.npz': '877cf7a399aca67a95de86e4b5505fea4656236162785af299e03184ff329d42', 'after-000200-episode-03-frame-049-seed-20261016.npz': '6a34d88f7ffac2496ca4aab073b599f8b49eeaf45b0458e916c89b4b80936295', 'after-000200-episode-03-frame-098-seed-777.npz': 'dd23ad581314f4b7bcdf436c4f32672c975be352e06c05263141f7d4ada7f5ea', 'after-000200-episode-03-frame-098-seed-888.npz': '915fc1945ca8a760965be079f679e382e96d9c86dc3397fc7f5cdb79f14b2ed0', 'after-000200-episode-03-frame-098-seed-7.npz': '322e894f31a915730642a5bcf64567a538d5966f3d5c75f0bd5eb5d5701b1045', 'after-000200-episode-03-frame-098-seed-20261016.npz': 'b42f693a4025aa97677c38d00983b15776afbb5799f42e30ce79ad2d67ec9ddb', 'after-000200-episode-04-frame-000-seed-777.npz': '646cce47960573f7bdf0967d718eec3cc1f23bf8272705f51179ed4b48b59fbb', 'after-000200-episode-04-frame-000-seed-888.npz': 'a1e321211a841e5f0d64833b6c85f010806fb2a8ba627a69ca6727e793aa2251', 'after-000200-episode-04-frame-000-seed-7.npz': 'c542d7d8c488663dd34e0b5c883c117d65c6c54c408b7411478ce5230fa20f26', 'after-000200-episode-04-frame-000-seed-20261016.npz': '05858878ed0545639c3b63d58591909e47037cc851b439264d815f0a4d4bfe53', 'after-000200-episode-04-frame-050-seed-777.npz': '48adebd3378e040cb340b01b2ff75abb78a6642f1d1a709429a0bfa2243c5469', 'after-000200-episode-04-frame-050-seed-888.npz': '309612b8b04e7e3cf9f1f9419fb9d32d914293bbfb1d1ef2f6041c9911733a6f', 'after-000200-episode-04-frame-050-seed-7.npz': '0d66c3be1601ee732e0761a54092de15deda329360f7935e7707df4434f1a557', 'after-000200-episode-04-frame-050-seed-20261016.npz': '5d979e50f4d0ef607c86843f12c8321c890d2350e873b1feda14aa5a20cd44a1', 'after-000200-episode-04-frame-101-seed-777.npz': '6213b06257ff2ecec97c7b1d689e3dafc9771478b746f4d90e9874a1e30b08a2', 'after-000200-episode-04-frame-101-seed-888.npz': '5b9d79b97c4e2827c72fbcac11d4ac5fa62120e09747ce0d93ddfd8b10b51880', 'after-000200-episode-04-frame-101-seed-7.npz': '732cd905848e1748b163208f1ee1575a8a9498b056261a45099ebae0a57e2b44', 'after-000200-episode-04-frame-101-seed-20261016.npz': 'bfad4146b71d3cf4942a06a10cb9eec9f72accd134a54d7169a84a00449d902f', 'after-000200-episode-06-frame-000-seed-777.npz': '39baf7951db5f6dac24cec58208550e4141af55a7702e840ef5603b5392ecb2f', 'after-000200-episode-06-frame-000-seed-888.npz': '89b51496fc67ae58cf134a4001e616762e8dcabb2e059393823c36065a34ffea', 'after-000200-episode-06-frame-000-seed-7.npz': '52e7cf55076778d2340f294cd163de9717470ab7095616f1a016c2034ef48b23', 'after-000200-episode-06-frame-000-seed-20261016.npz': '5287e2a7083f3632717eaabbd341ea6753bbe2f81dace4de24d8a8367e2073a8', 'after-000200-episode-06-frame-043-seed-777.npz': '14edfaa50a25866e8ed094fb076bdd16b18af1a1418da885b4c0394807be55d8', 'after-000200-episode-06-frame-043-seed-888.npz': '9d40a062e7791a00ba5088ee7507b154224ed81520a8412395fb3bb0a0f5976e', 'after-000200-episode-06-frame-043-seed-7.npz': '57acf74395541a689c927de7d9b5df0ea7b8ad0534351db3cde4cd3207c6c9ef', 'after-000200-episode-06-frame-043-seed-20261016.npz': '427761d3b4e8cf51c00c83f085309e4edd4ee94a447a7f518f2f10b44f56c47d', 'after-000200-episode-06-frame-087-seed-777.npz': '327187381b0cc64ac51594e6cf64777289e701523864d1ec91895002420d3a74', 'after-000200-episode-06-frame-087-seed-888.npz': 'ce53979b01646c34dc9754bbced3aebad77792853612c4cc04a02838d75f0f64', 'after-000200-episode-06-frame-087-seed-7.npz': 'e961ecd3b62d8364e19cae163ab75055462fc3f8df414376724c71303104e64a', 'after-000200-episode-06-frame-087-seed-20261016.npz': 'dd005c7e79686faa071bce13f4dcfdbce90b7a595501c466ba79c60b74038f36', 'after-000200-episode-07-frame-000-seed-777.npz': '40c1f91150c327f2ce1403826275041e06db4060d5e73700cdf303d428b1b9e1', 'after-000200-episode-07-frame-000-seed-888.npz': '887a1259703bb51984f786a0a573ad2130325cfd4e36a49a7a857233d91f8df8', 'after-000200-episode-07-frame-000-seed-7.npz': '2bd16c49aa28e5f6b0ba0b8a6eba9038ca2d196aec5e824ec33d5ce6ee2d6203', 'after-000200-episode-07-frame-000-seed-20261016.npz': '4adf9bcc22da0b1b5f221a6e10b83e9967cfa29ee8d55d3acfeff8da00df7fbd', 'after-000200-episode-07-frame-043-seed-777.npz': '6dda3c039436ae37e1073da91b9dbc5f2d627819ff9c9045e56aa4df59798850', 'after-000200-episode-07-frame-043-seed-888.npz': '0c3f2e56772e9088bb7b0871054b9067964302eadb9b8f5ebf31897969dd099b', 'after-000200-episode-07-frame-043-seed-7.npz': '91b3711e0018a14e5c588148c22b13730bfed50f77d260009033d85a2169be62', 'after-000200-episode-07-frame-043-seed-20261016.npz': 'a6b0d58d2d6aae369dd283fa77a6e5ce7579b92b8b5bf33fb52b021c76c41291', 'after-000200-episode-07-frame-086-seed-777.npz': '6c655e38354287a710c3f3bbbe37b45dec0a8e05ad77702d01ef571cfaf1521d', 'after-000200-episode-07-frame-086-seed-888.npz': '2ce8c081cd1f62d6b7f264d8a4f8aa49f0cfea34a0ede4106bd1687255d80fe8', 'after-000200-episode-07-frame-086-seed-7.npz': '560f1a3aabeeeacf8c42e8305c575a913639d0ed487daa33288f2f5ca02eb812', 'after-000200-episode-07-frame-086-seed-20261016.npz': '52cb8aa5255ce336f4582dea64f494e5889a4fc08e4a0a2ff2511cc2a233c5f6', 'after-000200-episode-12-frame-000-seed-777.npz': '151db7659771c7fa957c3a4fbd15b3623217b4ea30465749e53b705775d8b248', 'after-000200-episode-12-frame-000-seed-888.npz': '3d9a5265e5ba6884a65058d840218806619180e09485ba6282e48143ed6d9e06', 'after-000200-episode-12-frame-000-seed-7.npz': 'b8ca4ab08b9101a2981106f57e4091b41e6dd414fd2fb9161ecfd837051d948c', 'after-000200-episode-12-frame-000-seed-20261016.npz': '0bf1c014436e1102f05efee52ff2faf168d63fa8196e70a24472da2a8bda8e3b', 'after-000200-episode-12-frame-044-seed-777.npz': 'f082fdee0e02ae8ec03a0989fc7273aa96201d6268b9a7d849098252015dfd0e', 'after-000200-episode-12-frame-044-seed-888.npz': '8c284c59ecca61708a3ac594b6ad28216435c41b3b40ac86abd33431f65ad39f', 'after-000200-episode-12-frame-044-seed-7.npz': '0bf415373e6d3aa574d05fbaa148b5127f268f1557da3110a165a1865670e976', 'after-000200-episode-12-frame-044-seed-20261016.npz': '60a12eb848b15b24f453184d50d4124f187d6a454f91286581967fe6cccdd068', 'after-000200-episode-12-frame-089-seed-777.npz': '64af1bff003935e61ae43d3bfdc5c6e8010794965e4631cab2645b80a880e055', 'after-000200-episode-12-frame-089-seed-888.npz': '57fc442794f5b4f5260edc7fec204bb5c58faf429f2beca95679631f5a5c37af', 'after-000200-episode-12-frame-089-seed-7.npz': 'dcbb93948554de2a5d289643e91c3e326647bf7dc4885928f162e490fa39080c', 'after-000200-episode-12-frame-089-seed-20261016.npz': '23f837a3d53915c0d18998067139a49f0cf75e53113440d1c1a2afd38b5a6d3f', 'after-000200-episode-15-frame-000-seed-777.npz': 'e98d4ffb63e26aaaa72b513b081b2db2842eeaa07add864f8d0ed9aff1071853', 'after-000200-episode-15-frame-000-seed-888.npz': '3d07660e5fd8b0bfb110559708c75cbfe443adb5c63718b1a432e1c04f444f32', 'after-000200-episode-15-frame-000-seed-7.npz': '8f967ce1c82627df859250d1b178185883c7500183bd9bd56a4a86a2d906735d', 'after-000200-episode-15-frame-000-seed-20261016.npz': 'b24a8adec4d9238210e8cbda28ecd7631d72ee2a9e2c1ea6b98dd3a1fa472e04', 'after-000200-episode-15-frame-044-seed-777.npz': '9ac9aaa43db25ffd6ca1f3063bca3aacd6fc8e632688440375f20a3c2d525f76', 'after-000200-episode-15-frame-044-seed-888.npz': 'f25d12bb34780e0523f75ed38effb079cbe87068c957f2b4bb88e351e318d6a9', 'after-000200-episode-15-frame-044-seed-7.npz': 'ef89cb5c23066e9154530792a5ca330d91e0bc4a7bd5bd7772d1961983b38fa7', 'after-000200-episode-15-frame-044-seed-20261016.npz': 'b2b12960856784d627f2e5a31dc612cffeed9ab0ae8f6359f5bf9fc0985772ba', 'after-000200-episode-15-frame-088-seed-777.npz': '49baab5c03776f7b1a20f24300cf27f9886a5e3ae603b0fcd298c9328e7cca4e', 'after-000200-episode-15-frame-088-seed-888.npz': 'cb98b0d74ba19631e37ff38323c2673a1c5f970a2172279caeaba6d0f76f4712', 'after-000200-episode-15-frame-088-seed-7.npz': '9bcb36a004ac56a09620d245dcb7aa2b92ec2263529c31149ce667c2dfef259b', 'after-000200-episode-15-frame-088-seed-20261016.npz': '01922925b6be4111e837098cfe0ae6c9980cd5e0d46dbb9ba5647a5994bb7730', 'after-000200-episode-18-frame-000-seed-777.npz': 'bc2ec0a73a7bb84d561378bddaee698b093623fea61c29c105138f0093e68ae5', 'after-000200-episode-18-frame-000-seed-888.npz': '6afd81f427ccf91504ffc623ef12d0acdef954af110fb39fca67191c0abea77e', 'after-000200-episode-18-frame-000-seed-7.npz': '365927176c22abaf03b2ff1c2b3b470bbe554b745b545d22b3a571a75b5fdfce', 'after-000200-episode-18-frame-000-seed-20261016.npz': 'ba41708ae0f65401634861c868859f81c83dae0ebc67d43d3a8d987b20c13fc7', 'after-000200-episode-18-frame-046-seed-777.npz': '06ef786113ebde05cdf76fc35d0d548b752ba841bd78643e8f51a6f2970592a1', 'after-000200-episode-18-frame-046-seed-888.npz': '6fbd47bd95b23feed35fc318f8b2d6fffb83db0974784ff182710fd70236e15e', 'after-000200-episode-18-frame-046-seed-7.npz': 'e9e14460aad9116525ce529d2de2fc6065ee516a1cdca6b3fa4a9c62a5d9b260', 'after-000200-episode-18-frame-046-seed-20261016.npz': '09a23b577dc3b7efd3cf4b057eb5de79b77bd63d900e5806b48f8eacae1ef0df', 'after-000200-episode-18-frame-093-seed-777.npz': '3d1ac544cf53c9650f9eacb45ebe92a6910c1afb6adad406e35ff9241a7652cc', 'after-000200-episode-18-frame-093-seed-888.npz': 'bf7cbd00e096fd3c2ecf9e8509d38965293e613b62f5b1488d4576488ba52171', 'after-000200-episode-18-frame-093-seed-7.npz': 'b4cf806d3b2d5383e7247cfa469c0086a39d1807d8dc06d2160b8ee12dda93b9', 'after-000200-episode-18-frame-093-seed-20261016.npz': '045e8cc2011d97b67e6a793e67135581bacc56d8d576a97c084a46b97fe54548', 'after-000200-episode-45-frame-000-seed-777.npz': '20c8fa1a33595af404c34fdd0f78d7fb044e653525c81e881d2f9e917880bc04', 'after-000200-episode-45-frame-000-seed-888.npz': 'f4a4f7b27ceb39b509211070e9bd2e9c891ae52b4a15c033355534795546b04d', 'after-000200-episode-45-frame-000-seed-7.npz': '7fc5bf8f50a6b862d3f6317c0bb6d43bee7a3d0619052327bed1a975971bac50', 'after-000200-episode-45-frame-000-seed-20261016.npz': 'd6f07de205cef11c121982a64699927b365e5f2ccc3774d1f300f35316827a36', 'after-000200-episode-45-frame-047-seed-777.npz': 'a3deebfb36b286f4556dd92fa340311b9de08006a3b5783acce6dc161b1ddf6d', 'after-000200-episode-45-frame-047-seed-888.npz': '17a925fb0dd8f1989abf1890a4441643f667891349ae478d630518c58aba448a', 'after-000200-episode-45-frame-047-seed-7.npz': '9d8c99083f63376fae94cec7812f3bd0d4e0875d2d604e61d9e2cc25fbbb2b29', 'after-000200-episode-45-frame-047-seed-20261016.npz': 'ec12f1c95b993ee8afb81d652c0015d0ccf4556ffae30bcc82f396736a1fd134', 'after-000200-episode-45-frame-094-seed-777.npz': 'a95daf83d24dc8b2143722d8e2647b66533b259071248b934a6e4fc62ecc099c', 'after-000200-episode-45-frame-094-seed-888.npz': '60699d679456d60a8db5bc3af5858d775274d8fb2eefa297e0db7f35177048e4', 'after-000200-episode-45-frame-094-seed-7.npz': '5c7feadec1265a065a6f2881feefb201fc5b30478824ad1fd7e6ef114766d688', 'after-000200-episode-45-frame-094-seed-20261016.npz': '1b03dba979940c75c4a3f768355221f80bd00671bf7c43c120f59b4d3a97a1df', 'after-000200-episode-47-frame-000-seed-777.npz': 'f1a21b527d805a837cdc95b187f4a0bdbb527d37c35975cc5eb8f000cba37578', 'after-000200-episode-47-frame-000-seed-888.npz': '14acb3b3fe2c71cdf7fd4a085ba86cf48da5e3982fcbef46031ef5676507c70e', 'after-000200-episode-47-frame-000-seed-7.npz': '7aebab83982e52aa50d703c68da10a3d645c8c20435c7ed80fa4201a0d2b5fc8', 'after-000200-episode-47-frame-000-seed-20261016.npz': 'b2141802db4689ea6af7803c8adac66d28da476c5e83571755a14bfe5971aaec', 'after-000200-episode-47-frame-044-seed-777.npz': '285e17987b6c61551ac091a0bfc4f7ba3299329b1450217734455327125a212e', 'after-000200-episode-47-frame-044-seed-888.npz': 'e6b29f76d9ce498008abc515f7dd6db0ac49606d4ab552440411948040815f8c', 'after-000200-episode-47-frame-044-seed-7.npz': 'b7b6a64ec183873f54c1eb22329df9ab7080fe04f1b6f92ce17c70cc4e51668b', 'after-000200-episode-47-frame-044-seed-20261016.npz': '8d267d9780293b5806b5d00ff3b447ccf54dd9e53015e2db9142cbbf3c3847ac', 'after-000200-episode-47-frame-089-seed-777.npz': '19b74f471c49d7074e50aa007100dd4b17bdf433262a9388c45c4c672bea94d9', 'after-000200-episode-47-frame-089-seed-888.npz': '0bc4ab0ba58f539a3b3a88b86fab8d851c4725e19deb0b4119ebbf68f3ff3b6e', 'after-000200-episode-47-frame-089-seed-7.npz': '5ba931f789c814a59f48af8f4ec3ec6fc610c0a65de141bb2467436add03ce72', 'after-000200-episode-47-frame-089-seed-20261016.npz': 'b9a7459aa872e19afd0d187d76a5a617431d61e2865608c90f2e8dfd8b0d1c24', 'after-000200-episode-48-frame-000-seed-777.npz': '5192ffc132b47b8332144365c89ac17324be28e3b305f54e93c5c581c7684fee', 'after-000200-episode-48-frame-000-seed-888.npz': '0ac49d0a9e261fc939c402af3830e6496a09c7c617f04cac791a0f81e16d2f57', 'after-000200-episode-48-frame-000-seed-7.npz': '02044ac18c9553da48d55ab3fe0bcb057fdacfb42b83c62a4c0df7eb42cda6b7', 'after-000200-episode-48-frame-000-seed-20261016.npz': '3aa37955fe494dc806a4b8b56edb17659560fc64e5691e5c3ef9db74cbeb2ebe', 'after-000200-episode-48-frame-047-seed-777.npz': '2b4c984b8b7291787c8b40b364fdf9cda796df0ab6fbe7185b92fdc3a94bc593', 'after-000200-episode-48-frame-047-seed-888.npz': 'f7d1436ce61b3d5157d9916539a299444dddd1ec033b3932bb4f891fcba6a0cf', 'after-000200-episode-48-frame-047-seed-7.npz': '3da99c7d8ecacfc6bc1bccbdf39087a3c501c885ee7ad8388d499afb96e59bf0', 'after-000200-episode-48-frame-047-seed-20261016.npz': '929d5f25e1179d3ea25189c6218927489f2c6c00dd0083291eb28babc09511f3', 'after-000200-episode-48-frame-094-seed-777.npz': 'a24eb3f20ee3deecba93d5096a6242dc9ed5fe91367a946f2bb15e8ec6344b67', 'after-000200-episode-48-frame-094-seed-888.npz': '5651290f34a31f5dfaf19d0fc3fd5f2edce7cb2e446f659b6d51cb3aeba13804', 'after-000200-episode-48-frame-094-seed-7.npz': '74c734218ebfa1fd71654957041c24b629d34c4f2f8e272743807eb5f6935b68', 'after-000200-episode-48-frame-094-seed-20261016.npz': 'f826e08d4acd02530ff43bd84d8f1b53ae88c7b36b9d4cc4b738a5f6e7b09f67', 'after-000200-episode-49-frame-000-seed-777.npz': '7090a40954b8934efe50625092edabbb4295265e0a96c2cc67efba2db4b23af5', 'after-000200-episode-49-frame-000-seed-888.npz': '8a2e2f2a741097968d5506108f5e3bd32e2ff04510fb66448f99815264b9eaf1', 'after-000200-episode-49-frame-000-seed-7.npz': 'a063c17bfd52fb5e39fe15137e25db339fc7f4e2604f8dcdfcf0e934911e0237', 'after-000200-episode-49-frame-000-seed-20261016.npz': '87d2174e12dbc7e162c3d222ca0f5fa9a8cf3376bb6f0c49d6b6c07875a3c7f4', 'after-000200-episode-49-frame-045-seed-777.npz': '0525cbb54c1333b7691d7b8403921b34e0487549eee17dd85c2c2d9bda378060', 'after-000200-episode-49-frame-045-seed-888.npz': '2c075a257c8d2455fce759cae289f1a28f1053768a1d4f4a57ba5474185254f6', 'after-000200-episode-49-frame-045-seed-7.npz': 'f58f2cc8710ece1774d395f8ec0380dd56cc5c1096ab7731abfec7b9cbb7a5eb', 'after-000200-episode-49-frame-045-seed-20261016.npz': 'efa7ff968fd501f482b46b227f3e98cb5668d0313c3830c1645837489ecfc812', 'after-000200-episode-49-frame-091-seed-777.npz': '8f9f9237570b3455ced2405dc631b7a9d842b20949e32a83f10ed5821309de7b', 'after-000200-episode-49-frame-091-seed-888.npz': 'a89a3ff94b3898d0773c20947154a3caf2427ef7a50bd00e0274a5268742e1b2', 'after-000200-episode-49-frame-091-seed-7.npz': '27c8ce2b3eca6639c88546202dd4f3ea0aa1d3bfebdc396b9cf1db5369de5e0a', 'after-000200-episode-49-frame-091-seed-20261016.npz': '73135cb2867ba5cf49244ae929703beea6648daa8894e285f7431a8e545bfb42'}
EVALUATION_SEEDS = (777, 888, 7, 20261016)
SAMPLING_SEED = 20261016
MAX_UPDATES = 400
TRAIN_SECONDS = 20 * 60
PHASE_PATTERN = ('initial', 'middle', 'late', 'middle', 'late')
CONFIRMATION_EPISODES = ()


def validate_phase_source():
    for name, expected in SOURCE_FILES.items():
        require(digest(SOURCE_RUN / name) == expected, 'Phase source evidence changed: ' + name)
    saved = json.loads((SOURCE_RUN / 'report.json').read_text())
    require(saved['status'] == 'COMPLETE' and saved['worker_exit_code'] == 0,
            'Source correction did not complete')
    metadata = json.loads((SOURCE_STAGE / 'checkpoint.json').read_text())
    require(metadata['completed_updates'] == 200, 'Expected source start-state +200 checkpoint')
    for name, expected in metadata['files'].items():
        require(Path(name).name == name and digest(SOURCE_STAGE / name) == expected,
                'Starting checkpoint hash mismatch: ' + name)
    report.update(start_checkpoint=str(SOURCE_STAGE), source_file_hashes=SOURCE_FILES,
                  start_checkpoint_files=metadata['files'])
    print('Pinned start-state +200 checkpoint and source outputs: PASS before GPU selection', flush=True)


def select_confirmation_episodes():
    global CONFIRMATION_EPISODES
    audited = _BOTTLE_AUDIT
    require(audited is not None, 'Raw audit must precede confirmation selection')
    chosen = []
    for side in ('left', 'right'):
        remaining = sorted(e for e, entry in audited.items()
                           if entry['split'] == 'audit_only' and entry['moving_arms'] == [side])
        require(remaining, 'No unused correction-stage confirmation episode for ' + side)
        chosen.append(remaining[0])
    CONFIRMATION_EPISODES = tuple(sorted(chosen))
    require(not set(CONFIRMATION_EPISODES) & set(TRAIN_EPISODES + EVAL_EPISODES), 'Confirmation overlap')
    report['confirmation_episodes'] = CONFIRMATION_EPISODES
    report['confirmation_scope'] = ('Excluded from all bottle-correction updates and candidate selection; '
        'original clean50 training may include them. Evaluated once for source and selected checkpoint after selection.')
    atomic_report()


def row_phase(row, entries):
    episode, frame, global_row = row
    require(entries[episode]['rows'].get(frame) == global_row, 'Row metadata mismatch')
    if frame == 0:
        return 'initial'
    # Split the remaining actual observation rows in half, including masked episode tails.
    last_observation = len(entries[episode]['states']) - 2
    require(0 < frame <= last_observation, 'Observation frame outside episode')
    return 'middle' if frame <= last_observation // 2 else 'late'


def phase_balanced_batches(rows, entries, updates=None, seed=SAMPLING_SEED):
    import numpy as np
    updates = MAX_UPDATES if updates is None else updates
    require(updates > 0 and updates % 5 == 0, 'Updates must be a positive multiple of five')
    require(rows and len(rows) == len(set(rows)), 'Missing or duplicate training rows')
    sides = {side: sorted(e for e, value in entries.items()
        if value['split'] == 'train' and value['moving_arms'] == [side]) for side in ('left', 'right')}
    require(all(len(ids) == 5 for ids in sides.values()), 'Need five training episodes per arm')
    require(set(r[0] for r in rows) == set(sides['left'] + sides['right']), 'Unexpected training episode')
    rng = np.random.default_rng(seed); groups = {}
    for episode in sides['left'] + sides['right']:
        own = sorted((row for row in rows if row[0] == episode), key=lambda row: row[1])
        require(len(own) == len(entries[episode]['rows']), 'Incomplete episode training rows')
        for phase in ('initial', 'middle', 'late'):
            subset = [row for row in own if row_phase(row, entries) == phase]
            require(subset and (phase != 'initial' or len(subset) == 1), 'Missing phase: ' + phase)
            groups[episode, phase] = [subset[i] for i in rng.permutation(len(subset)).tolist()]
    occurrences = dict.fromkeys(PHASE_PATTERN, 0); schedule = []
    for update in range(updates):
        phase = PHASE_PATTERN[update % 5]; occurrence = occurrences[phase]
        batch = []
        for side in ('left', 'right'):
            episode = sides[side][occurrence % 5]; choices = groups[episode, phase]
            batch.append(choices[(occurrence // 5) % len(choices)])
        schedule.append((update // 25, batch))
        occurrences[phase] += 1
    return schedule


def verify_phase_baseline(cases):
    import numpy as np
    for case in cases:
        name = f'after-000200-episode-{case["episode"]:02d}-frame-{case["frame"]:03d}-seed-{case["noise_seed"]}.npz'
        require(name in SOURCE_FILES, 'Baseline reference is not pinned')
        with np.load(SOURCE_RUN / name, allow_pickle=False) as old, np.load(OUT / case['array_file'], allow_pickle=False) as new:
            for key in ('normalized', 'commands', 'raw_target', 'raw_state', 'noise', 'active', 'instruction'):
                require(np.array_equal(old[key], new[key]), 'Starting-point replay differs: ' + name + ':' + key)
    require(len(cases) == 168, 'Incomplete exact +200 baseline replay')
    report['exact_phase_baseline_reproductions'] = len(cases)
    print('Exact source +200 baseline replays:', len(cases), flush=True)


def phase_summary(label, split='evaluation'):
    import numpy as np
    selected = [c for c in report['cases'] if c['label'] == label and c['split'] == split]
    require(selected, 'Missing phase metrics')
    result = {}
    for phase_index, phase in enumerate(('initial', 'middle', 'late')):
        group = []
        for episode in sorted({c['episode'] for c in selected}):
            own = [c for c in selected if c['episode'] == episode]
            frames = sorted({c['frame'] for c in own})
            require(len(frames) == 3, 'Incomplete three-phase evaluation')
            group.extend(c for c in own if c['frame'] == frames[phase_index])
        require(len(group) == len({c['episode'] for c in selected}) * len(EVALUATION_SEEDS), 'Missing phase seeds')
        stationary = [c['motion_metrics'][('right' if c['moving_arms'] == ['left'] else 'left') + '_arm_target_rmse_degrees'] for c in group]
        result[phase] = dict(cases=len(group),
            arm_rmse_degrees=float(np.mean([c['motion_metrics']['arm_target_rmse_degrees'] for c in group])),
            stationary_arm_rmse_degrees=float(np.mean(stationary)),
            worst_stationary_arm_rmse_degrees=float(max(stationary)),
            worst_first_gap_degrees=max(c['motion_metrics']['initial_largest_arm_target_change_degrees'] for c in group),
            worst_adjacent_gap_degrees=max(c['motion_metrics']['largest_adjacent_joint_target_change_degrees'] for c in group))
    return dict(phases=result, mean_phase_rmse_degrees=float(np.mean([p['arm_rmse_degrees'] for p in result.values()])),
        worst_first_gap_degrees=max(p['worst_first_gap_degrees'] for p in result.values()))


def phase_motion_gate(label):
    gate = start_motion_gate(label)
    baseline = phase_summary('before'); current = phase_summary(label)
    checks = dict(initial_fit_preserved=current['phases']['initial']['arm_rmse_degrees'] <= 1.10 * baseline['phases']['initial']['arm_rmse_degrees'],
        middle_fit_preserved=current['phases']['middle']['arm_rmse_degrees'] <= 1.10 * baseline['phases']['middle']['arm_rmse_degrees'],
        late_fit_not_worse=current['phases']['late']['arm_rmse_degrees'] <= baseline['phases']['late']['arm_rmse_degrees'],
        worst_first_gap_not_worse=current['worst_first_gap_degrees'] <= baseline['worst_first_gap_degrees'],
        requested_arm_preserved=gate['requested_arm_dominant'] == gate['initial_cases'],
        initial_stationary_arm=current['phases']['initial']['stationary_arm_rmse_degrees'] <= 5)
    failures = list(gate['failures']) + ['phase:' + key for key, passed in checks.items() if not passed]
    gate.update(status='PASS' if not failures else 'NOT_READY', failures=failures,
        phase_summary=current, preservation_checks=checks, eligible_for_phase_selection=all(checks.values()),
        score=current['mean_phase_rmse_degrees'],
        selection_scope='Preservation checks first; equal phase mean RMSE, then worst first gap; source baseline remains eligible. Confirmation never selects.')
    return gate


def choose_phase_candidate(stages, source_gate):
    baseline = dict(completed_updates=0, checkpoint=str(SOURCE_STAGE), motion_gate=source_gate,
                    role='unchanged_source_start_state_plus_200')
    # Always allow retaining the unchanged reference. Do not force a worse trained checkpoint.
    candidates = [baseline] + [stage for stage in stages if stage['motion_gate']['eligible_for_phase_selection']]
    return min(candidates, key=lambda stage: (stage['motion_gate']['score'],
        stage['motion_gate']['phase_summary']['worst_first_gap_degrees'], stage['completed_updates']))


def evaluate_confirmation(model, config, dataset, rows, entries, namespace, transform, selected):
    import torch
    from safetensors.torch import load_file
    require(len(rows) == 6 and {entries[r[0]]['moving_arms'][0] for r in rows} == {'left', 'right'},
            'Incomplete two-episode confirmation panel')
    require(not set(r[0] for r in rows) & set(TRAIN_EPISODES + EVAL_EPISODES), 'Confirmation leaked')
    for label, checkpoint in (('confirmation-before', SOURCE_STAGE), ('confirmation-selected', Path(selected['checkpoint']))):
        metadata = json.loads((checkpoint / 'checkpoint.json').read_text())
        require(all(digest(checkpoint / name) == value for name, value in metadata['files'].items()), 'Confirmation checkpoint hash mismatch')
        state = torch.load(checkpoint / 'resume-state.pt', map_location='cpu', weights_only=True)
        restore_capacity_start(model, load_file(str(checkpoint / 'adapter_model.safetensors')),
            load_file(str(checkpoint / 'projection_weights.safetensors')), state['persistent_buffers'], state['model_steps'])
        evaluate_episode_rows(model, config, dataset, rows, entries, namespace, transform, label, selected['completed_updates'] if label.endswith('selected') else 0)
    report['confirmation_comparison'] = dict(before=phase_summary('confirmation-before', 'confirmation'),
        selected=phase_summary('confirmation-selected', 'confirmation'), used_for_selection=False,
        cases=48, caveat=report['confirmation_scope'])


def prepare_phase_episode_split(dataset, corpus, archive, transform, namespace):
    import numpy as np
    import torch
    from lingbotvla.data.vla_data.transform import prepare_language
    audited = _BOTTLE_AUDIT if _BOTTLE_AUDIT is not None else audit_bottle_archive(archive)
    require(len(TRAIN_EPISODES) == 10 and len(EVAL_EPISODES) == 4, 'Balanced split was not selected')
    bottle, = [i for i, value in enumerate(corpus['tasks']) if value['task'] == 'adjust_bottle']
    child = dataset._datasets[bottle]
    metadata = child.dataset.hf_dataset.select_columns(['episode_index', 'frame_index']).with_format('numpy')[:]
    episodes, frames = (np.asarray(metadata[k]) for k in ('episode_index', 'frame_index'))
    require(episodes.ndim == 1 and episodes.shape == frames.shape, 'Invalid converted bottle frame metadata')
    global_start = int(dataset.dataset_start_index[bottle])
    entries = {}; training_rows = []; evaluation_rows = []; confirmation_rows = []
    for episode in TRAIN_EPISODES + EVAL_EPISODES + CONFIRMATION_EPISODES:
        entry = dict(audited[episode]); states = entry['states']
        if episode in CONFIRMATION_EPISODES: entry['split'] = 'confirmation'
        local_rows = np.flatnonzero(episodes == episode)
        require(len(local_rows) == len(states)-1 and set(frames[local_rows].tolist()) == set(range(len(states)-1)),
                'Full converted episode rows are missing or duplicated')
        by_frame = {int(frames[i]): global_start+int(i) for i in local_rows}
        tokens, masks = prepare_language(namespace['config'], namespace['processor'].tokenizer,
            {'state': torch.zeros(55), 'prompt': [entry['instruction']]})
        entry.update(rows=by_frame, language={'lang_tokens': tokens.cpu().clone(), 'lang_masks': masks.cpu().clone()})
        entries[episode] = entry
        if episode in TRAIN_EPISODES:
            training_rows.extend((episode, frame, by_frame[frame]) for frame in sorted(by_frame))
        (confirmation_rows if episode in CONFIRMATION_EPISODES else evaluation_rows).extend(
            (episode, frame, by_frame[frame]) for frame in (0, (len(states)-51)//2, len(states)-51))
    require(len(evaluation_rows) == 42, 'Incomplete balanced phase evaluation')
    require({entries[e]['moving_arms'][0] for e in TRAIN_EPISODES} == {'left', 'right'},
            'Training split is missing an arm')
    report['episode_split'] = [{k: v for k, v in entry.items() if k not in ('states', 'rows', 'language')}
                              for entry in entries.values()]
    report['evaluation_split_caveat'] = 'Evaluation is excluded from this correction stage; original clean50 training may include these episodes.'
    return entries, training_rows, evaluation_rows, confirmation_rows

def phase_correction(model, config, dataset, corpus, archive, namespace, transform):
    import numpy as np
    import torch
    from safetensors.torch import load_file
    from inference_cache_recovery import clear_visual_cache
    from inference_common import equal_tree, to_cpu
    from lingbot_zero_padding import sample_actions
    verify_padding_helper(model, config, namespace)
    entries, rows, evaluation, confirmation = prepare_phase_episode_split(dataset, corpus, archive, transform, namespace)
    schedule = phase_balanced_batches(rows, entries)
    report.update(scope='Isolated balanced-arm bottle correction; no simulator or benchmark score.',
        maximum_updates=MAX_UPDATES, full_schedule_updates=len(schedule),
        training_budget_seconds=TRAIN_SECONDS, batch_size=2, data_workers=0, evaluation_seeds=EVALUATION_SEEDS,
        cases=[], learning_measurements=[], stage_results=[], first_action_weight=FIRST_ACTION_WEIGHT,
        training_objective='Unchanged installed masked loss and fivefold first-target weighting; 20/40/40 percent true starts/middle/late observations; one real episode per arm; auxiliary losses skipped in memory.',
        normalization='Unchanged full clean50 normalization.', branch='lora_plus_projections',
        source_checkpoint=str(SOURCE_STAGE), optimizer='Fresh AdamW lr 1e-4, weight decay .01, clip 1.')
    original = snapshot_branch(model)
    guarded = {str(Path(namespace['checkpoint']) / name): value for name, value in namespace['record']['checkpoint_files'].items()}
    for path in (RUN/'training-smoke/latest-checkpoint.json', RUN/'training-smoke/resolved-inputs.json',
                 ROOT/'lingbot-vla-v2/lingbotvla/models/vla/lingbot_vla/modeling_lingbot_vla_v2.py'):
        guarded[str(path)] = digest(path)
    core = model.model; precision = torch.get_float32_matmul_precision(); configs = []
    for value in (config, core.config):
        if not any(value is old[0] for old in configs): configs.append((value, value.use_cache, value.align_params, value.num_steps))
    flags = {name: getattr(core, name, None) for name in ('use_depth_align', 'use_future_video', 'use_current_video_patch')}
    completed = consumed = 0; visited = set(); saved = None; training_elapsed = 0.0
    guarded.update({str(SOURCE_RUN/name):value for name,value in SOURCE_FILES.items()})
    guarded.update({str(SOURCE_STAGE/name):value for name,value in report['start_checkpoint_files'].items()})
    try:
        source_state=torch.load(SOURCE_STAGE/'resume-state.pt', map_location='cpu', weights_only=True)
        require(source_state['completed_updates'] == 200, 'Wrong source +200 resume state')
        restore_capacity_start(model, load_file(str(SOURCE_STAGE/'adapter_model.safetensors')),
            load_file(str(SOURCE_STAGE/'projection_weights.safetensors')), source_state['persistent_buffers'], source_state['model_steps'])
        del source_state
        trainable, frozen = select_capacity_parameters(model)
        torch.set_float32_matmul_precision('highest')
        for value, cache, align, count in configs:
            value.use_cache=False; value.align_params={}; value.num_steps=10
        baseline=evaluate_episode_rows(model, config, dataset, evaluation, entries, namespace, transform, 'before', 0)
        verify_phase_baseline(baseline)
        source_gate=phase_motion_gate('before')
        report['baseline_summary'] = summarize_motion_stage('before')
        optimizer = torch.optim.AdamW(list(trainable.values()), lr=1e-4, weight_decay=.01, foreach=False)
        torch.manual_seed(SAMPLING_SEED); torch.cuda.manual_seed_all(SAMPLING_SEED)
        segment_started = time.monotonic()
        for update, (schedule_block, batch_rows) in enumerate(schedule[:MAX_UPDATES], 1):
            if training_elapsed + time.monotonic() - segment_started >= TRAIN_SECONDS: break
            items = [episode_item(dataset, row, entries, transform) for row in batch_rows]
            require({entries[row[0]]['moving_arms'][0] for row in batch_rows} == {'left', 'right'}, 'Optimizer batch lost arm balance')
            batch = episode_batch(items, namespace['device']); model.train()
            with first_action_loss_scope(core, batch): measurements = probe_train_step(model, batch, trainable, optimizer)
            require(all(p.grad is None and p._version == version for _, p, version in frozen), 'Frozen parameters changed')
            completed=update; consumed+=2; visited.update(batch_rows)
            measurements.update(update=update, schedule_block=schedule_block, rows=batch_rows, sample_phase=PHASE_PATTERN[(update-1)%5])
            report['learning_measurements'].append(measurements)
            report.update(completed_updates=completed, samples_consumed=consumed, unique_training_pairs=len(visited),
                training_seconds=training_elapsed + time.monotonic() - segment_started)
            if update <= 3 or update % 20 == 0:
                report['phase']=f'balanced correction {update}/{min(MAX_UPDATES, len(schedule))}'; atomic_report()
                print(f'Balanced update {update}: action loss={measurements["action_loss"]:.6f}; covered={len(visited)}/{len(rows)} pairs', flush=True)
            if update % 100 == 0: saved=save_episode_checkpoint(model, optimizer, completed, consumed, SOURCE_STAGE, schedule)
            if update in (200, 400):
                training_elapsed += time.monotonic() - segment_started
                evaluate_episode_rows(model, config, dataset, evaluation, entries, namespace, transform, f'after-{completed:06d}', completed)
                gate=phase_motion_gate(f'after-{completed:06d}')
                report['stage_results'].append(dict(completed_updates=completed, checkpoint=str(saved), motion_gate=gate,
                    summary=summarize_motion_stage(f'after-{completed:06d}')))
                print('Initial-state correction offline motion gate:', gate['status'], gate['failures'], flush=True)
                atomic_report(); segment_started=time.monotonic()
        require(completed > 0, 'No optimizer update completed')
        training_elapsed += time.monotonic() - segment_started
        if completed % 100: saved=save_episode_checkpoint(model, optimizer, completed, consumed, SOURCE_STAGE, schedule)
        optimizer.zero_grad(set_to_none=True)
        label=f'after-{completed:06d}'
        if not report['stage_results'] or report['stage_results'][-1]['completed_updates'] != completed:
            evaluate_episode_rows(model, config, dataset, evaluation, entries, namespace, transform, label, completed)
            report['stage_results'].append(dict(completed_updates=completed, checkpoint=str(saved), motion_gate=phase_motion_gate(label), summary=summarize_motion_stage(label)))
        report['consumed_start_uses']={str(e):sum(row[0]==e and row[1]==0 for m in report['learning_measurements'] for row in m['rows']) for e in TRAIN_EPISODES}
        report['consumed_phase_uses']={str(e):{phase:sum(row[0]==e and row_phase(row, entries)==phase for m in report['learning_measurements'] for row in m['rows']) for phase in ('initial','middle','late')} for e in TRAIN_EPISODES}
        fitted=snapshot_branch(model); metadata=json.loads((saved/'checkpoint.json').read_text())
        require(all(digest(saved/name) == value for name, value in metadata['files'].items()), 'Saved checkpoint hash mismatch')
        state=torch.load(saved/'resume-state.pt', map_location='cpu', weights_only=True)
        require(state['completed_updates'] == completed and state['samples_consumed'] == consumed and state['schedule'] == schedule,
                'Saved consumed cursor or schedule differs')
        restore_capacity_start(model, load_file(str(saved/'adapter_model.safetensors')), load_file(str(saved/'projection_weights.safetensors')),
                               state['persistent_buffers'], state['model_steps'])
        require(branch_equals(model, fitted), 'Adapter/projections/buffers reload differs')
        optimizer.load_state_dict(state['optimizer']); require(equal_tree(state['optimizer'], to_cpu(optimizer.state_dict())), 'Optimizer reload differs')
        item=episode_item(dataset, evaluation[-1], entries, transform)
        observation={name: item[name].unsqueeze(0).to(namespace['device']) for name in ('images', 'img_masks', 'lang_tokens', 'lang_masks', 'state', 'image_grid_thw')}
        observation['images']=observation['images'].float(); observation['state']=observation['state'].float(); observation['image_grid_thw']=observation['image_grid_thw'].long()
        last=report['cases'][-1]
        with np.load(OUT/last['array_file'], allow_pickle=False) as a: noise=torch.from_numpy(a['noise'].copy()).to(namespace['device']); expected=a['normalized'].copy()
        with namespace['inference_cache_scope'](model, config): actual=sample_actions(core, observation, action_joint_mask=item['action_joint_mask'], noise=noise)
        require(np.array_equal(actual.cpu().numpy(), expected), 'Generated action reload differs')
        best=choose_phase_candidate(report['stage_results'], source_gate)
        # The best candidate can be the earlier evaluated update-200 stage.
        # Verify that candidate independently instead of only reloading the end.
        candidate_folder=Path(best['checkpoint'])
        candidate_metadata=json.loads((candidate_folder/'checkpoint.json').read_text())
        require(all(digest(candidate_folder/name) == value for name, value in candidate_metadata['files'].items()),
                'Selected candidate checkpoint hash mismatch')
        candidate_state=torch.load(candidate_folder/'resume-state.pt', map_location='cpu', weights_only=True)
        restore_capacity_start(model, load_file(str(candidate_folder/'adapter_model.safetensors')),
            load_file(str(candidate_folder/'projection_weights.safetensors')), candidate_state['persistent_buffers'], candidate_state['model_steps'])
        candidate_case=[c for c in report['cases'] if c['label'] == best['motion_gate']['label']][-1]
        with np.load(OUT/candidate_case['array_file'], allow_pickle=False) as a:
            candidate_noise=torch.from_numpy(a['noise'].copy()).to(namespace['device']); candidate_expected=a['normalized'].copy()
        with namespace['inference_cache_scope'](model, config):
            candidate_actual=sample_actions(core, observation, action_joint_mask=item['action_joint_mask'], noise=candidate_noise)
        require(np.array_equal(candidate_actual.cpu().numpy(), candidate_expected), 'Selected candidate generated-action reload differs')
        report.update(exact_tensor_and_optimizer_reload=True, exact_generated_action_reload=True, training_seconds=training_elapsed,
            coverage_complete=len(visited) == len(rows), schedule_complete=completed == len(schedule),
            training_stage_status='COMPLETE' if completed == len(schedule) else 'PARTIAL',
            stop_reason='complete_phase_schedule' if completed == len(schedule) else 'update_cap' if completed == MAX_UPDATES else 'training_time_budget',
            selected_candidate=best, motion_gate=best['motion_gate'], exact_selected_candidate_action_reload=True)
        evaluate_confirmation(model, config, dataset, confirmation, entries, namespace, transform, best)
        candidate=dict(directory=best['checkpoint'], completed_updates=best['completed_updates'], motion_gate=best['motion_gate'])
        (OUT/'candidate-checkpoint.json.partial').write_text(json.dumps(candidate, indent=2)+'\n')
        os.replace(OUT/'candidate-checkpoint.json.partial', OUT/'candidate-checkpoint.json')
    finally:
        clear_visual_cache(model)
        for value, cache, align, count in configs: value.use_cache=cache; value.align_params=align; value.num_steps=count
        torch.set_float32_matmul_precision(precision)
        restore_capacity_start(model, original['adapter'], original['projections'], original['buffers'], original['step'])
        report['original_model_restored']=branch_equals(model, original)
        report['original_files_unchanged']=all(digest(path) == value for path, value in guarded.items()); atomic_report()
    require(report['original_model_restored'] and report['original_files_unchanged'], 'Original state/file preservation failed')
    require({name: getattr(core, name, None) for name in flags} == flags, 'Auxiliary prefix flags changed')
    report['peak_allocated_gib']=torch.cuda.max_memory_allocated()/1024**3
    print('PHASE-BALANCED CORRECTION FINISHED. Offline motion gate:', report['motion_gate']['status'], flush=True)
    print('Remaining checks:', report['motion_gate']['failures'], flush=True)
    print('No live motion, collision, grasping or official score was measured. Original checkpoint preserved.', flush=True)

def main():
    began = time.monotonic()
    atomic_report()
    require(digest(OLD / 'server.py') == '4fcde47967b0edaf27f8a9526cb85834c80c30db743a105fe7ea556b36ae70a1', 'Saved live server changed; offline reuse stopped.')
    require(digest(OLD / 'inference_common.py') == 'e87f3036866274b4f5153d7a821059d3c237a288f2d17921a14824022172e5c8', 'Saved inference builder changed.')
    identity = json.loads((RUN / 'training-smoke/resolved-inputs.json').read_text())
    checkpoint = Path(json.loads((RUN / 'training-smoke/latest-checkpoint.json').read_text())['directory']).resolve()
    record = json.loads((OLD / 'evaluation-inputs.json').read_text())
    require(checkpoint == Path(record['checkpoint']).resolve(), 'Checkpoint differs from the stopped rollout.')
    require(checkpoint.parent == (RUN / 'training-smoke/checkpoints').resolve(), 'Checkpoint escaped training run.')
    metadata = json.loads((checkpoint / 'checkpoint.json').read_text())
    require(metadata['identity'] == identity and metadata['completed_updates'] == 10000, 'Wrong trained checkpoint identity.')
    require(metadata['files'] == record['checkpoint_files'], 'Checkpoint file listing changed.')
    for name, expected in metadata['files'].items():
        require(Path(name).name == name and digest(checkpoint / name) == expected, 'Checkpoint hash mismatch: ' + name)
    for name, expected in identity['harness_hashes'].items():
        require(name in ('training.py', 'train_stream_core.py', 'validated_training_common.py')
                and digest(RUN / name) == expected, 'Training harness changed: ' + name)
    for name, key in [('modeling_lingbot_vla_v2.py', 'policy_sha256'), ('qwen2_action_expert.py', 'moe_sha256')]:
        require(digest(ROOT / 'lingbot-vla-v2/lingbotvla/models/vla/lingbot_vla' / name) == identity[key],
                'Installed policy source changed: ' + name)
    for path, key in [(ROOT / 'models/lingbot-vla-v2-6b-base/source-manifest.json', 'base_manifest_sha256'),
                      (ROOT / 'models/Qwen3-VL-4B-Instruct-assets/source-manifest.json', 'qwen_manifest_sha256')]:
        require(digest(path) == identity[key], 'Model asset provenance changed: ' + key)
    cache = RUN / 'inference-cache-recovery-v1/inference_cache_recovery.py'
    require(digest(cache) == '7b2eb0a73ca07b62190a195fc6c9a5f81f56a28ee18efaa41ae016cdc9200bc5', 'Cache helper changed.')
    archive = ROOT / 'dataset-audit/adjust_bottle/adjust_bottle-aloha-agilex_clean_50.zip'
    require(archive.is_file() and archive.stat().st_size == 298659710 and
            digest(archive) == '5554b6b30e37c6ed2f0bbc48079e8ad79d9512e9d4f910a5e71b0d5ad8fbe50e',
            'Pinned bottle archive missing or changed.')
    validate_phase_source()
    audit_bottle_archive(archive)
    select_confirmation_episodes()
    validate_padding_reference()
    select_gpu()
    os.environ['LINGBOT_EVAL_OUT'] = os.environ['LINGBOT_PROBE_OUT'] = str(OUT)
    shutil.copyfile(OLD / 'evaluation-inputs.json', OUT / 'evaluation-inputs.json')
    shutil.copyfile(OLD / 'inference_common.py', OUT / 'inference_common.py')
    namespace = {'__name__': 'offline_loaded_policy', '__file__': str(OLD / 'server.py')}
    print('Loading the exact saved update-10000 inference policy with timing instrumentation ...', flush=True)
    cleanup_trace = install_load_trace()
    try:
        exec(compile(verified_prefix((OLD / 'server.py').read_text()), str(OLD / 'server.py'), 'exec'), namespace)
    finally:
        cleanup_trace()
    report['phase'] = 'offline motion comparisons'
    atomic_report()
    model, config, transform = [namespace[k] for k in ('model', 'config', 'transform')]
    predict, packet = namespace['predict'], namespace['packet_observation']
    import cv2
    import h5py
    import numpy as np
    import torch
    sys.path.insert(0, str(RUN))
    from validated_training_common import prepare_dataset
    settings, dataset, align, corpus, manifest, norm, data_settings = prepare_dataset()
    require(digest(norm) == identity['normalization_sha256'], 'Actual loader uses different normalization.')
    report['checkpoint'] = str(checkpoint)
    phase_correction(model, config, dataset, corpus, archive, namespace, transform)
    report.update(status='COMPLETE', phase='complete', duration_seconds=time.monotonic()-began)
    atomic_report()

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        report.update(status='ERROR', error=str(error), traceback=traceback.format_exc())
        atomic_report()
        raise
