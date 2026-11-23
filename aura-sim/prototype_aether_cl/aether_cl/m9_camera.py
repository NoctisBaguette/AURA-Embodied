"""M9a candidate camera I/O. No verifier, task truth or motor-command interface."""

import hashlib
import io
import json
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np

WIDTH, HEIGHT, HZ = 640, 480, 20
VIEW_PORT = 18709
ARRAY_KEYS = ("primary_rgb", "primary_depth_mm", "primary_validity", "secondary_rgb", "qpos")
CAMERAS = (
    {"uid": "m9_primary", "eye": [.55, -.55, .70], "target": [-.08, 0., .15]},
    {"uid": "m9_secondary", "eye": [.10, .80, .55], "target": [-.08, 0., .15]},
)


def array(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.array(value, copy=True)


def validate_packet(packet):
    if set(packet) != set(ARRAY_KEYS):
        raise ValueError("Camera packet contains missing or non-allowlisted fields")
    for key in ("primary_rgb", "secondary_rgb"):
        value = packet[key]
        if value.shape != (HEIGHT, WIDTH, 3) or value.dtype != np.uint8 or value.max() == value.min():
            raise ValueError("Require nonconstant native RGB8: " + key)
    depth, valid = packet["primary_depth_mm"], packet["primary_validity"]
    if depth.shape != (HEIGHT, WIDTH) or depth.dtype not in (np.dtype("int16"), np.dtype("uint16")):
        raise ValueError("Require documented native integer millimeter depth")
    if np.any(depth < 0) or np.any(depth > 3000):
        raise ValueError("Depth exceeds the candidate camera's 3m far plane")
    if valid.shape != depth.shape or valid.dtype != np.uint8 or not np.array_equal(valid, depth > 0):
        raise ValueError("Validity must come only from scalar depth, not segmentation")
    qpos = packet["qpos"]
    if qpos.shape != (9,) or not np.isfinite(qpos).all():
        raise ValueError("Require measured Panda joint positions")


def packet_hashes(packet):
    validate_packet(packet)
    return {key: hashlib.sha256(np.ascontiguousarray(packet[key]).tobytes()).hexdigest()
            for key in ARRAY_KEYS}


def save_packet(path, packet):
    validate_packet(packet)
    with ZipFile(path, "x", compression=ZIP_DEFLATED, compresslevel=1) as archive:
        for key in ARRAY_KEYS:
            with archive.open(key + ".npy", "w") as stream:
                np.lib.format.write_array(stream, packet[key], allow_pickle=False)


class CameraPair:
    def __init__(self, base):
        from mani_skill.sensors.camera import Camera, CameraConfig
        from mani_skill.utils import sapien_utils

        self.base = base
        self.cameras = [Camera(CameraConfig(spec["uid"],
            sapien_utils.look_at(eye=spec["eye"], target=spec["target"]),
            WIDTH, HEIGHT, np.pi / 2, .01, 3., shader_pack="minimal"), base.scene)
            for spec in CAMERAS]
        self.calibration = {
            "candidate_not_frozen": True, "specifications": CAMERAS,
            "width": WIDTH, "height": HEIGHT, "shader": "minimal",
            "depth_unit": "millimeter", "depth_quantization_mm": 1,
            "invalid_depth": 0, "validity_source": "scalar_depth_positive_only",
            "parameters": [{k: array(v).tolist() for k, v in camera.get_params().items()}
                           for camera in self.cameras],
            "static_cube_edge_m": .04, "robot_base_world_pose": [-.615, 0., 0., 1., 0., 0., 0.],
        }

    def capture(self):
        # Match the installed state_dict sensor path's visual hiding. No pose,
        # velocity, material or contact state is changed by this adapter.
        for obj in self.base._hidden_objects:
            obj.hide_visual()
        self.base.scene.update_render(update_sensors=False, update_human_render_cameras=False)
        primary_start = time.monotonic_ns()
        self.cameras[0].capture()
        primary = self.cameras[0].get_obs(rgb=True, depth=True, position=False,
            segmentation=False, normal=False, albedo=False)
        secondary_start = time.monotonic_ns()
        self.cameras[1].capture()
        secondary = self.cameras[1].get_obs(rgb=True, depth=False, position=False,
            segmentation=False, normal=False, albedo=False)
        if set(primary) != {"rgb", "depth"} or set(secondary) != {"rgb"}:
            raise ValueError("Unexpected camera modalities; retain evidence before adaptation")
        rgb = array(primary["rgb"])[0]
        depth = array(primary["depth"])[0, ..., 0]
        packet = {"primary_rgb": rgb, "primary_depth_mm": depth,
                  "primary_validity": (depth > 0).astype(np.uint8),
                  "secondary_rgb": array(secondary["rgb"])[0],
                  "qpos": array(self.base.agent.robot.get_qpos()).reshape(-1)}
        validate_packet(packet)
        return packet, {"primary_capture_request_monotonic_ns": primary_start,
                        "secondary_capture_request_monotonic_ns": secondary_start,
                        "pixels_ready_monotonic_ns": time.monotonic_ns()}


def display_frame(packet, step, mode):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (WIDTH * 2, HEIGHT + 48))
    image.paste(Image.fromarray(packet["primary_rgb"]), (0, 0))
    image.paste(Image.fromarray(packet["secondary_rgb"]), (WIDTH, 0))
    ImageDraw.Draw(image).text((12, HEIGHT + 10),
        f"M9a DEVELOPMENT / Baseline / seed100 / zero force / {mode} / action {step}/800 / sim {step/HZ:.2f}s", fill="white")
    return np.asarray(image)


class Recorder:
    def __init__(self, directory):
        import imageio_ffmpeg

        self.directory = Path(directory)
        (self.directory / "frames").mkdir()
        self.count = 0
        self.writer = imageio_ffmpeg.write_frames(str(self.directory / "camera.mp4"),
            (WIDTH * 2, HEIGHT + 48), fps=HZ, codec="libx264", pix_fmt_in="rgb24",
            pix_fmt_out="yuv420p", quality=None, macro_block_size=1, ffmpeg_timeout=30,
            output_params=["-crf", "20", "-preset", "veryfast"])
        self.writer.send(None)

    def put(self, packet, image, step):
        if step != self.count:
            raise ValueError("Missing, duplicate or reordered recorded frame")
        save_packet(self.directory / "frames" / f"frame_{step:05d}.npz", packet)
        self.writer.send(np.ascontiguousarray(image))
        self.count += 1

    def close(self):
        self.writer.close()


PAGE = b'''<!doctype html><meta charset="utf-8"><title>AURA M9a camera commissioning</title>
<style>body{background:#15191f;color:#eee;font:17px system-ui;margin:24px}img{width:100%;max-width:1280px}button{padding:12px;font-size:17px}</style>
<h2>AURA M9a: actual simulator camera</h2><p>Development commissioning, Baseline, retained seed100, zero force. Left: primary RGB-D camera RGB. Right: complementary RGB camera.</p>
<button id="go" onclick="fetch('/start',{method:'POST'})">Start the recorded live episode</button>
<p id="status">Waiting for camera...</p><img id="frame"><p><a href="/video">Recorded MP4</a></p>
<script>setInterval(async()=>{try{let s=await(await fetch('/status')).json();document.querySelector('#status').textContent=JSON.stringify(s);document.querySelector('#go').disabled=s.state!=='waiting_for_start';if(s.frame_available)document.querySelector('#frame').src='/frame.jpg?t='+Date.now()}catch(e){}},250)</script>'''


class LiveView:
    """HTTP reads cached bytes only. Start gates only the pre-action boundary."""
    def __init__(self, directory, port=VIEW_PORT):
        self.directory = Path(directory)
        self.lock, self.start = threading.Lock(), threading.Event()
        self.jpeg = None
        self.status = {"state": "preparing", "frame_available": False}
        self.requests = {"frame": 0, "status": 0, "start": 0}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, data, kind):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                try:
                    if path == "/":
                        self.reply(200, PAGE, "text/html; charset=utf-8")
                    elif path in ("/status", "/frame.jpg"):
                        with owner.lock:
                            key = "status" if path == "/status" else "frame"
                            owner.requests[key] += 1
                            value = (json.dumps(owner.status).encode() if key == "status" else owner.jpeg)
                        self.reply(200 if value else 503, value or b"No frame yet",
                                   "application/json" if key == "status" else "image/jpeg")
                    elif path == "/video" and owner.status.get("state") in ("finished", "error"):
                        target = owner.directory / "camera.mp4"
                        if not target.is_file():
                            self.reply(404, b"No completed recording", "text/plain")
                        else:
                            self.send_response(200)
                            self.send_header("Content-Type", "video/mp4")
                            self.send_header("Content-Length", str(target.stat().st_size))
                            self.end_headers()
                            with target.open("rb") as stream:
                                for block in iter(lambda: stream.read(1024 * 1024), b""):
                                    self.wfile.write(block)
                    else:
                        self.reply(404, b"Not found", "text/plain")
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):
                with owner.lock:
                    allowed = self.path == "/start" and owner.status["state"] == "waiting_for_start"
                    if allowed:
                        owner.requests["start"] += 1
                        owner.start.set()
                self.reply(200 if allowed else 409, b"Start requested" if allowed else b"No active start gate", "text/plain")

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def publish(self, image, state, step):
        from PIL import Image
        stream = io.BytesIO()
        Image.fromarray(image).save(stream, format="JPEG", quality=85)
        with self.lock:
            self.jpeg = stream.getvalue()
            self.status = {"state": state, "step": step, "simulation_time_s": step/HZ,
                           "frame_available": True, "port": self.port}

    def complete(self, state):
        with self.lock:
            self.status = {**self.status, "state": state}

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def distribution_summary(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {"count": 0}
    return {"count": len(values), "mean": float(values.mean()), "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)), "p99": float(np.percentile(values, 99)),
            "max": float(values.max())}
