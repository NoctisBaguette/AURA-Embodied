"""Native simulator/transport commissioning before policy loading; no policy actions."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import threading
import time
import numpy as np
from joint50_common import CAMERAS, PILOT, SIM_PY, PROJECT, atomic_json, require
CHECKPOINT = 'NO_MODEL_TRANSPORT_COMMISSION'

@contextmanager
def probe_server(home, nonce):
    home = Path(home)
    receipts = []

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                require(self.path == '/infer' and self.headers.get('X-LingBot-Run') == nonce, 'Commission route/run mismatch')
                length = int(self.headers.get('Content-Length', '0'))
                require(0 < length <= 8 * 1024 ** 2, 'Invalid commission packet length')
                with np.load(io.BytesIO(self.rfile.read(length)), allow_pickle=False) as packet:
                    for key in CAMERAS:
                        require(packet[key].shape == (240, 320, 3) and packet[key].dtype == np.uint8, 'Commission camera contract differs')
                    state = packet['observation.state'].copy()
                    require(state.shape == (14,) and state.dtype == np.float32 and np.isfinite(state).all(), 'Commission state contract differs')
                    episode = str(packet['episode_id'].item())
                    chunk = int(packet['chunk_index'])
                    seed = int(packet['noise_seed'])
                    text = str(packet['task'].item())
                    require(chunk == 1 and seed == 777 and text.strip(), 'Commission first request differs')
                receipts.append(dict(episode_id=episode, chunk_index=chunk, noise_seed=seed, instruction=text, scope='Transport echo; no learned policy'))
                atomic_json(home / 'commission-transport.json', dict(requests=receipts, learned_policy=False))
                value = dict(actions=np.tile(state, (50, 1)).tolist(), episode_id=episode, chunk_index=chunk, noise_seed=seed, stage='commission', checkpoint=CHECKPOINT, inference_seconds=0.0, conditioned_text=text, conditioned_tokens=[])
                data = json.dumps(value, allow_nan=False).encode('utf-8')
                self.send_response(200)
            except Exception as error:
                data = json.dumps(dict(error=str(error))).encode('utf-8')
                self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        ready = dict(stage='commission', checkpoint=CHECKPOINT, nonce=nonce, port=server.server_address[1], scope='Echo-only commissioning; simulator must stop before applying returned commands')
        atomic_json(home / 'commission-ready.json', ready)
        try:
            yield ready
        finally:
            server.shutdown()
            thread.join(timeout=3)
            require(not thread.is_alive(), 'Commission server did not stop')

def run(home, environment, owned, state, save, check_cancel, package):
    import cv2
    home = Path(home)
    deadline = time.monotonic() + 3600
    results = []
    nonce = (home / 'run-nonce.txt').read_text(encoding='utf-8').strip()
    with probe_server(home, nonce):
        for index, (task, setting) in enumerate(((task, setting) for task in PILOT for setting in ('clean', 'randomized'))):
            check_cancel()
            directory = home / 'commission' / f'{index:02d}-{task}-{setting}'
            directory.mkdir(parents=True)
            child = owned.spawn(home / 'joint50_sim.py', directory / 'sim.log', environment, ['--task', task, '--setting', setting, '--job-id', index, '--output', directory, '--ready', home / 'commission-ready.json', '--commission'], python=SIM_PY, cwd=PROJECT / 'RoboTwin')
            owned.scene_children.add(child.pid)
            limit = min(deadline, time.monotonic() + 600)
            while child.poll() is None:
                check_cancel()
                require(time.monotonic() < limit, 'Simulator commissioning timed out: ' + str(directory))
                time.sleep(0.5)
            stopped = owned.stop(child)
            require(stopped and child.returncode == 0, 'Simulator commissioning failed: ' + str(directory) + ' exit=' + str(child.returncode))
            report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
            require(report['status'] == 'COMPLETE' and report['native_commissioned'] is True and (report['checkpoint'] == CHECKPOINT) and (report['policy_actions_executed'] == 0) and (report['chunks'] == 1) and (not report['episodes']), 'Native commissioning contract failed')
            transport = json.loads((home / 'commission-transport.json').read_text(encoding='utf-8'))
            require(transport['learned_policy'] is False and len(transport['requests']) == index + 1 and (transport['requests'][-1]['episode_id'] == report['directory']), 'Missing matching native transport receipt')
            capture = cv2.VideoCapture(str(directory / report['directory'] / report['video']))
            count = 0
            while True:
                okay, frame = capture.read()
                if not okay:
                    break
                require(frame.shape == (384, 512, 3), 'Commission video shape differs')
                count += 1
            capture.release()
            require(count == report['video_frames'] and count > 0, 'Commission video decode/count differs')
            results.append(dict(task=task, setting=setting, scene_seed=report['scene_seed'], policy_actions_executed=0, video_frames=count))
            state['commissioned_cases'] = results
            save()
            print('Native commissioning:', task, setting, len(results), '/16; no policy actions.', flush=True)
    require(len(results) == 16, 'Incomplete native commissioning')
    state['native_simulator_commissioned'] = True
    save()
    package(home)
    return results
