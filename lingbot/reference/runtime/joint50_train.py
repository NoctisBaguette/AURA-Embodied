"""Isolated joint50 continuation; original targets/checkpoints stay unchanged."""
import bisect
import copy
import json
import math
from pathlib import Path
import random
import shutil
import time
import numpy as np
from joint50_common import AUDIT, atomic_json, digest, require
BATCH = 2
UPDATES = 50000
SEED = 20261019
TRAIN_SECONDS = 22 * 3600
MILESTONES = {100, 1000, 5000, 10000, 25000, 50000}

def lr_factor(position):
    require(0 <= position <= UPDATES, 'Scheduler position out of range')
    if position < 500:
        return (position + 1) / 500
    return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (position - 500) / (UPDATES - 500)))

def rng_state(torch):
    state = np.random.get_state()
    return dict(python=random.getstate(), numpy=(state[0], state[1].tolist(), *state[2:]), cpu=torch.get_rng_state(), cuda=torch.cuda.get_rng_state())

def restore_rng(torch, saved):
    random.setstate(saved['python'])
    value = saved['numpy']
    np.random.set_state((value[0], np.asarray(value[1], dtype=np.uint32), *value[2:]))
    torch.set_rng_state(saved['cpu'])
    torch.cuda.set_rng_state(saved['cuda'])

def save_checkpoint(home, core, model, optimizer, scheduler, update, identity, metrics):
    import torch
    from safetensors.torch import save_file
    folder = home / 'checkpoints' / f'update-{update:06d}-{time.time_ns()}'
    stage = folder.with_name(folder.name + '.partial')
    stage.mkdir(parents=True)
    branch = core.snapshot_branch(model)
    require(all((torch.isfinite(v).all().item() for values in (branch['adapter'], branch['projections'], branch['buffers']) for v in values.values())), 'Nonfinite checkpoint tensors')
    save_file({k: v.contiguous() for k, v in branch['adapter'].items()}, str(stage / 'adapter_model.safetensors'))
    save_file({k: v.contiguous() for k, v in branch['projections'].items()}, str(stage / 'projection_weights.safetensors'))
    model.peft_config['default'].save_pretrained(str(stage))
    from inference_common import to_cpu
    torch.save(dict(optimizer=to_cpu(optimizer.state_dict()), scheduler=scheduler.state_dict(), rng=rng_state(torch), persistent_buffers=branch['buffers'], model_steps=branch['step'], completed_updates=update, samples_consumed=update * BATCH, identity=identity), stage / 'resume-state.pt')
    shutil.copyfile(identity['normalization_path'], stage / 'norm-stats-clean50.json')
    names = ('adapter_model.safetensors', 'projection_weights.safetensors', 'adapter_config.json', 'resume-state.pt', 'norm-stats-clean50.json')
    atomic_json(stage / 'checkpoint.json', dict(identity=identity, completed_updates=update, samples_consumed=update * BATCH, files={name: digest(stage / name) for name in names}, generated_metrics=metrics))
    for path in stage.iterdir():
        with path.open('rb') as handle:
            import os
            os.fsync(handle.fileno())
    stage.rename(folder)
    atomic_json(home / 'latest-checkpoint.json', dict(directory=str(folder)))
    complete = [p for p in sorted((home / 'checkpoints').glob('update-*')) if not p.name.endswith('.partial')]
    keep = set(complete[-3:]) | {p for p in complete if int(p.name.split('-')[1]) in MILESTONES}
    for path in complete:
        if path not in keep:
            shutil.rmtree(path)
    return folder

def restore_checkpoint(folder, core, model, optimizer, scheduler, identity):
    import torch
    from safetensors.torch import load_file
    from inference_common import equal_tree, to_cpu
    metadata = json.loads((folder / 'checkpoint.json').read_text(encoding='utf-8'))
    require(metadata['identity'] == identity, 'Continuation checkpoint identity differs')
    for name, expected in metadata['files'].items():
        require(Path(name).name == name and digest(folder / name) == expected, 'Continuation checkpoint hash mismatch')
    state = torch.load(folder / 'resume-state.pt', map_location='cpu', weights_only=True)
    require(state['identity'] == identity and state['samples_consumed'] == state['completed_updates'] * BATCH, 'Continuation sample cursor differs')
    core.restore_capacity_start(model, load_file(str(folder / 'adapter_model.safetensors')), load_file(str(folder / 'projection_weights.safetensors')), state['persistent_buffers'], state['model_steps'])
    optimizer.load_state_dict(state['optimizer'])
    scheduler.load_state_dict(state['scheduler'])
    require(equal_tree(to_cpu(optimizer.state_dict()), state['optimizer']) and equal_tree(scheduler.state_dict(), state['scheduler']), 'Optimizer/scheduler restore differs')
    restore_rng(torch, state['rng'])
    require(equal_tree(rng_state(torch), state['rng']), 'RNG restore differs')
    return state['completed_updates']

def run(core, model, config, dataset, namespace, transform, audit, schedule, output):
    import torch
    from lingbotvla.data.vla_data.transform import prepare_language
    from training import IndexedDataset, IndexedCollator
    from inference_cache_recovery import clear_visual_cache
    home = output / 'training'
    home.mkdir(exist_ok=True)
    entries = sorted(audit['episodes'], key=lambda e: e['global_start'])
    starts = [entry['global_start'] for entry in entries]
    for task_index, child in enumerate(dataset._datasets):
        meta = child.dataset.hf_dataset.select_columns(['episode_index', 'frame_index']).with_format('numpy')[:]
        own = [entry for entry in entries if entry['task_index'] == task_index]
        offset = int(dataset.dataset_start_index[task_index])
        for entry in own:
            start = entry['global_start'] - offset
            stop = start + entry['rows']
            require(np.all(np.asarray(meta['episode_index'])[start:stop] == entry['episode']) and np.array_equal(np.asarray(meta['frame_index'])[start:stop], np.arange(entry['rows'])), 'Actual loader rows differ from reviewed schedule')
    language = {}
    for entry in entries:
        if entry['first_explicit_arm_conflict']:
            language[entry['global_start']] = prepare_language(config, namespace['processor'].tokenizer, dict(state=torch.zeros(55), prompt=[entry['selected_text']]))
    require(len(language) == 2, 'Only the two reviewed contradictory source texts may change')
    indexed = IndexedDataset(dataset, SEED)
    collator = IndexedCollator()

    def item(position, index):
        entry = entries[bisect.bisect_right(starts, index) - 1]
        require(entry['global_start'] <= index < entry['global_start'] + entry['rows'], 'Row escaped reviewed episode')
        value = indexed[position, index]
        if entry['global_start'] in language:
            tokens, mask = language[entry['global_start']]
            value.update(lang_tokens=tokens.clone(), lang_masks=mask.clone())
        return value
    fixed = []
    for task in audit['evaluation']['pilot_tasks']:
        entry = next((e for e in entries if e['task'] == task and e['episode'] == 0))
        for frame in sorted({0, entry['rows'] // 2, max(0, entry['rows'] - 50)}):
            value = item(0, entry['global_start'] + frame)
            fixed.append((task, frame, {k: v.detach().cpu().clone() for k, v in value.items() if torch.is_tensor(v)}))
    identity = dict(initializer=audit['original_checkpoint'], schedule_sha256=audit['schedule']['sha256'], audit_archive_sha256=__import__('joint50_common').AUDIT_SHA, batch_size=BATCH, max_updates=UPDATES, seed=SEED, trainable_scope='action-attention LoRA plus five state/action/time projections', learning_rate=0.0001, minimum_lr=1e-05, warmup_updates=500, weight_decay=0.01, max_grad_norm=1.0, teacher_losses=False, first_action_weight=1.0, label_changes=2, normalization_path=str(core.ROOT / 'data-preparation/clean50-conversion/norm-stats-clean50.json'), normalization_sha256=digest(core.ROOT / 'data-preparation/clean50-conversion/norm-stats-clean50.json'), trainer_sha256=digest(Path(__file__)), inference_helper_sha256=digest(output / 'lingbot_zero_padding.py'))
    atomic_json(home / 'identity.json', identity)
    for cfg in (config, model.model.config):
        cfg.use_cache = False
        cfg.align_params = {}
        cfg.num_steps = 10
    core.report['branch'] = 'lora_plus_projections'
    trainable, frozen = core.select_capacity_parameters(model)
    require(sum((p.numel() for p in trainable.values())) == 5733175, 'Trainable capacity differs')
    optimizer = torch.optim.AdamW(list(trainable.values()), lr=0.0001, weight_decay=0.01, foreach=False)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_factor)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    update = 0
    if (home / 'latest-checkpoint.json').exists():
        folder = Path(json.loads((home / 'latest-checkpoint.json').read_text(encoding='utf-8'))['directory'])
        require(folder.parent.resolve() == (home / 'checkpoints').resolve(), 'Resume path escaped new run')
        update = restore_checkpoint(folder, core, model, optimizer, scheduler, identity)
        trainable, frozen = core.select_capacity_parameters(model)
    device = namespace['device']
    from lingbot_zero_padding import sample_actions

    def evaluate(label):
        model.eval()
        clear_visual_cache(model)
        metrics = []
        arrays = []
        for task, frame, value in fixed:
            observation = {name: value[name].unsqueeze(0).to(device) for name in ('images', 'img_masks', 'lang_tokens', 'lang_masks', 'state', 'image_grid_thw')}
            observation['images'] = observation['images'].float()
            observation['state'] = observation['state'].float()
            observation['image_grid_thw'] = observation['image_grid_thw'].long()
            noise = torch.randn((1, 50, 55), device=device, generator=torch.Generator(device=device).manual_seed(777))
            with torch.inference_mode(), namespace['inference_cache_scope'](model, config):
                predicted = sample_actions(model.model, observation, action_joint_mask=value['action_joint_mask'], noise=noise)
            require(torch.isfinite(predicted).all().item(), 'Nonfinite generated checkpoint actions')
            arrays.append(predicted.detach().cpu().numpy().copy())
            valid = (~value['action_is_pad'].bool())[:, None] & value['action_joint_mask'][None, :]
            metrics.append(dict(task=task, frame=frame, masked_generated_normalized_rmse=float(((predicted[0].cpu() - value['actions'])[valid] ** 2).mean().sqrt())))
        np.savez_compressed(home / (label + '.npz'), normalized=np.concatenate(arrays, axis=0))
        clear_visual_cache(model)
        atomic_json(home / (label + '.json'), dict(scope='Source-exposed generated-target diagnostics, not task success', cases=metrics))
        return metrics
    before = evaluate('generated-before')
    began = time.monotonic()
    last_saved = began
    task_counts = np.zeros(50, dtype=np.int64)
    start_counts = np.zeros(50, dtype=np.int64)
    for count in range(update * BATCH):
        task_counts[schedule['task_indices'][count]] += 1
        if schedule['forced_episode_start'][count]:
            start_counts[schedule['task_indices'][count]] += 1
    metrics = before
    checkpoint = None
    with (home / 'updates.jsonl').open('a', buffering=1, encoding='utf-8') as log:
        while update < UPDATES and time.monotonic() - began < TRAIN_SECONDS and (not (output / 'STOP_TRAIN').exists()):
            started = time.perf_counter()
            position = update * BATCH
            indices = schedule['global_indices'][position:position + BATCH].tolist()
            batch, positions, actual_indices = collator([item(position + i, index) for i, index in enumerate(indices)])
            require(positions.tolist() == [position, position + 1] and actual_indices.tolist() == indices, 'Consumed cursor differs')
            batch = {key: batch[key].to(device) for key in ('images', 'img_masks', 'state', 'lang_tokens', 'lang_masks', 'actions', 'joint_mask', 'action_is_pad', 'image_grid_thw')}
            for key in ('images', 'state', 'actions'):
                batch[key] = batch[key].float()
            batch['image_grid_thw'] = batch['image_grid_thw'].long()
            require(batch['actions'].shape == (BATCH, 50, 55), 'Training batch shape differs')
            active = torch.zeros(55, dtype=torch.bool, device=device)
            active[list(range(12)) + [28, 29]] = True
            require(batch['joint_mask'].shape == (BATCH, 50, 55) and torch.equal(batch['joint_mask'].bool(), active[None, None, :].expand(BATCH, 50, -1)) and (batch['action_is_pad'].shape == (BATCH, 50)) and (torch.count_nonzero(batch['actions'][:, :, ~active]).item() == 0), 'Training masks/unused targets differ')
            model.train()
            result = core.probe_train_step(model, batch, trainable, optimizer)
            scheduler.step()
            require(all((p.grad is None and p._version == version for _, p, version in frozen)), 'Frozen base changed')
            update += 1
            for cursor in range(position, position + BATCH):
                task_counts[schedule['task_indices'][cursor]] += 1
                if schedule['forced_episode_start'][cursor]:
                    start_counts[schedule['task_indices'][cursor]] += 1
            result.update(update=update, samples_consumed=update * BATCH, indices=indices, learning_rate_next=optimizer.param_groups[0]['lr'], wall_seconds=time.monotonic() - began, end_to_end_seconds=time.perf_counter() - started)
            log.write(json.dumps(result, allow_nan=False) + '\n')
            if update <= 3 or update % 20 == 0:
                atomic_json(home / 'progress.json', dict(status='TRAINING', **result, task_counts=task_counts, forced_start_counts=start_counts))
                print('Joint update', update, '/', UPDATES, 'samples', update * BATCH, 'loss', result['action_loss'], flush=True)
            if update in MILESTONES or update % 500 == 0 or time.monotonic() - last_saved >= 300:
                optimizer.zero_grad(set_to_none=True)
                checkpoint = save_checkpoint(home, core, model, optimizer, scheduler, update, identity, metrics)
                last_saved = time.monotonic()
            del batch
    require(update > 0, 'No complete joint update')
    optimizer.zero_grad(set_to_none=True)
    metrics = evaluate('generated-after')
    checkpoint = save_checkpoint(home, core, model, optimizer, scheduler, update, identity, metrics)
    snapshot = core.snapshot_branch(model)
    restore_checkpoint(checkpoint, core, model, optimizer, scheduler, identity)
    require(core.branch_equals(model, snapshot), 'Saved joint tensors/buffers/step restore differs')
    after_reload = evaluate('generated-reloaded')
    require(metrics == after_reload, 'Saved generated metrics differ after restore')
    with np.load(home / 'generated-after.npz', allow_pickle=False) as before_reload, np.load(home / 'generated-reloaded.npz', allow_pickle=False) as restored:
        require(np.array_equal(before_reload['normalized'], restored['normalized']), 'Generated actions differ after checkpoint restore')
    model.requires_grad_(False)
    model.eval()
    clear_visual_cache(model)
    report = dict(status='COMPLETE' if update == UPDATES else 'PAUSED', completed_updates=update, samples_consumed=update * BATCH, checkpoint=str(checkpoint), wall_seconds=time.monotonic() - began, task_counts=task_counts, forced_start_counts=start_counts, source_label_changes=2, trainable_parameters=5733175, in_process_checkpoint_restore=True, generated_metrics_restore=True, fresh_process_reload=False, official_score=False, stop_reason='sample_budget' if update == UPDATES else 'stop_request' if (output / 'STOP_TRAIN').exists() else '22_hour_budget')
    atomic_json(home / 'report.json', report)
    atomic_json(home / 'progress.json', report)
    del optimizer, scheduler, fixed, trainable, frozen
    torch.cuda.empty_cache()
    return report
