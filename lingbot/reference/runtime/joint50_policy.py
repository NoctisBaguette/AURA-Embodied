"""Persistent original policy, isolated joint training, then candidate policy."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import time
import traceback
from joint50_common import atomic_json, digest, require, reviewed_inputs
OUT = Path(os.environ['LINGBOT_PANEL_OUT'])
POLICY = OUT / 'policy'
POLICY.mkdir(exist_ok=True)
shutil.copyfile(OUT / 'lingbot_zero_padding.py', POLICY / 'lingbot_zero_padding.py')
os.environ['LINGBOT_MOTION_OUT'] = str(POLICY)
spec = importlib.util.spec_from_file_location('joint50_approved_core', OUT / 'model_core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.report.update(scope='Original joint baseline, bounded new joint continuation, candidate visual pilot', cases=[])
admitted = json.loads((OUT / 'simulator-admission.json').read_text(encoding='utf-8'))
original_snapshot = core.gpu_snapshot

def admitted_snapshot():
    rows = original_snapshot()
    row = rows.get(admitted['uuid'])
    return {admitted['uuid']: row} if row is not None and row['index'] == admitted['index'] else {}
core.gpu_snapshot = admitted_snapshot
from joint50_admission import install as install_admission
install_admission(core, admitted, OUT, os.environ['LINGBOT_CONTROL_JOB'])

def workflow(model, config, dataset, corpus, archive, namespace, transform):
    import numpy as np
    import torch
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from inference_cache_recovery import clear_visual_cache
    from lingbot_zero_padding import sample_actions
    from joint50_train import run as train
    audit, schedule = reviewed_inputs()
    core.verify_padding_helper(model, config, namespace)
    torch.set_float32_matmul_precision('highest')
    for cfg in (config, model.model.config):
        cfg.use_cache = False
        cfg.align_params = {}
        cfg.num_steps = 10
    nonce = (OUT / 'run-nonce.txt').read_text(encoding='utf-8').strip()
    device = namespace['device']
    total_requests = 0

    def serve(stage, checkpoint):
        nonlocal total_requests
        model.requires_grad_(False)
        model.eval()
        clear_visual_cache(model)
        versions = {name: p._version for name, p in model.named_parameters()}
        buffers = {name: value.detach().cpu().clone() for name, value in model.named_buffers() if name in model.state_dict()}
        step = model.model.steps
        seen = set()
        requests = 0
        root = POLICY / stage
        root.mkdir(exist_ok=True)
        metadata_files = {name: digest(Path(checkpoint) / name) for name in json.loads((Path(checkpoint) / 'checkpoint.json').read_text(encoding='utf-8'))['files']}
        record = dict(ready=True, stage=stage, checkpoint=str(checkpoint), checkpoint_files=metadata_files, original_padding_replay=True, normalization_sha256=digest(Path(checkpoint) / 'norm-stats-clean50.json'), precision='FP32', physical_gpu=core.report['selected_gpu']['index'], gpu_uuid=core.report['selected_gpu']['uuid'], nonce=nonce, scope='32-episode pilot; one fixed checkpoint per stage; not official full-suite results')

        def infer(payload):
            nonlocal requests, total_requests
            with np.load(io.BytesIO(payload), allow_pickle=False) as values:
                episode = str(values['episode_id'].item())
                chunk = int(values['chunk_index'])
                seed = int(values['noise_seed'])
            require(episode and len(episode) <= 100 and all((c in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in episode)), 'Invalid request episode')
            require(1 <= chunk <= 40 and 0 <= seed < 2 ** 31, 'Invalid request chunk/noise')
            require((episode, chunk) not in seen, 'Duplicate inference request')
            applied, raw_state = namespace['packet_observation'](payload)
            observation = {key: applied[key].unsqueeze(0).to(device) for key in ('images', 'img_masks', 'lang_tokens', 'lang_masks', 'state', 'image_grid_thw')}
            observation['images'] = observation['images'].float()
            observation['state'] = observation['state'].float()
            observation['image_grid_thw'] = observation['image_grid_thw'].long()
            noise = torch.randn((1, 50, 55), device=device, dtype=torch.float32, generator=torch.Generator(device=device).manual_seed(seed))
            torch.cuda.synchronize()
            began = time.perf_counter()
            with torch.inference_mode(), namespace['inference_cache_scope'](model, config):
                predicted = sample_actions(model.model, observation, action_joint_mask=applied['action_joint_mask'], noise=noise)
            torch.cuda.synchronize()
            seconds = time.perf_counter() - began
            decoded = transform.unapply({**copy.deepcopy(applied), 'actions': predicted[0].detach().cpu().clone()})
            commands = decoded['action'].numpy().copy()
            require(commands.shape == (50, 14) and np.isfinite(commands).all(), 'Invalid decoded commands')
            require(all((parameter._version == versions[name] for name, parameter in model.named_parameters())), 'Inference changed parameters')
            require(model.model.steps == step, 'Inference changed model counter')
            live = dict(model.named_buffers())
            require(all((torch.equal(live[name].detach().cpu(), value) for name, value in buffers.items())), 'Inference changed persistent buffers')
            tokens = applied['lang_tokens'][applied['lang_masks'].bool()].cpu().tolist()
            text = namespace['processor'].tokenizer.decode(tokens, skip_special_tokens=False)
            values = dict(normalized=predicted.detach().cpu().numpy(), commands=commands, noise=noise.detach().cpu().numpy(), state=raw_state, lang_tokens=applied['lang_tokens'].cpu().numpy(), lang_masks=applied['lang_masks'].cpu().numpy())
            if chunk == 1:
                (root / (episode + '.input.npz')).write_bytes(payload)
                values['images'] = applied['images'].cpu().numpy()
            np.savez_compressed(root / f'{episode}-chunk-{chunk:03d}.npz', **values)
            clear_visual_cache(model)
            seen.add((episode, chunk))
            requests += 1
            total_requests += 1
            atomic_json(root / 'progress.json', dict(stage=stage, requests=requests, last_episode=episode, last_chunk=chunk))
            return dict(actions=commands.tolist(), episode_id=episode, chunk_index=chunk, noise_seed=seed, stage=stage, checkpoint=str(checkpoint), inference_seconds=seconds, conditioned_text=text, conditioned_tokens=tokens)

        class Handler(BaseHTTPRequestHandler):

            def log_message(self, *args):
                pass

            def reply(self, code, value):
                data = json.dumps(value, allow_nan=False).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self.reply(200, record) if self.path == '/health' else self.reply(404, dict(error='Unknown route'))

            def do_POST(self):
                try:
                    require(self.path == '/infer' and self.headers.get('X-LingBot-Run') == nonce, 'Wrong run or route')
                    length = int(self.headers.get('Content-Length', '0'))
                    require(0 < length <= 8 * 1024 ** 2, 'Invalid request length')
                    payload = self.rfile.read(length)
                    require(len(payload) == length, 'Incomplete request body')
                    self.reply(200, infer(payload))
                except Exception as error:
                    traceback.print_exc()
                    self.reply(500, dict(error=str(error)))
        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            record['port'] = server.server_address[1]
            server.timeout = 0.5
            atomic_json(OUT / (stage + '-ready.json'), record)
            print('JOINT50 POLICY READY:', stage, checkpoint, flush=True)
            while not (OUT / 'STOP_POLICY').exists():
                if stage == 'baseline' and (OUT / 'BEGIN_TRAIN').exists():
                    break
                server.handle_request()
        atomic_json(root / 'report.json', dict(status='COMPLETE', stage=stage, requests=requests, parameters_unchanged=True, persistent_buffers_unchanged=True, checkpoint=str(checkpoint)))
    serve('baseline', audit['original_checkpoint'])
    if not (OUT / 'STOP_POLICY').exists():
        trained = train(core, model, config, dataset, namespace, transform, audit, schedule, OUT)
        core.report['joint_training'] = trained
        if not (OUT / 'STOP_POLICY').exists():
            serve('trained', trained['checkpoint'])
    core.report.update(live_requests=total_requests, original_reference_files_preserved=True)
core.phase_correction = workflow
if __name__ == '__main__':
    try:
        core.main()
    except BaseException as error:
        core.report.update(status='ERROR', error=str(error), traceback=traceback.format_exc())
        core.atomic_report()
        raise
