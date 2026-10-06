"""M6 support placement/release runtime and correctly labelled paused live viewer."""

import argparse
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import threading
import traceback
from urllib.parse import urlsplit

from .m3 import PreviewSnapshot
from .viewer import Server
from .m6_runtime import M6Config, run
from .m6_policy import MAX_STEPS


def make_server(port, snapshot):
    page = Path(__file__).with_name("m6_index.html").read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            status, jpeg = snapshot.read()
            if path == "/":
                body, mime, code = page, "text/html; charset=utf-8", 200
            elif path == "/api/status":
                body, mime, code = json.dumps(status, allow_nan=False).encode(), "application/json", 200
            elif path == "/frame.jpg" and jpeg is not None:
                body, mime, code = jpeg, "image/jpeg", 200
            else:
                body, mime, code = b"Not found\n", "text/plain", 404
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
        def log_message(self, *args):
            pass
    return Server(("127.0.0.1", port), Handler)


def serve(config, port):
    config.validate()
    if not config.render or not 1 <= port <= 65535:
        raise ValueError("Live viewing requires rendering and a valid port")
    stop = threading.Event()
    snapshot = PreviewSnapshot(stop)
    server = make_server(port, snapshot)
    def worker():
        try:
            run(config, snapshot.publish, stop)
        except BaseException as error:
            status, _ = snapshot.read()
            snapshot.publish({**status, "state": "error", "error": f"{type(error).__name__}: {error}"}, None)
            traceback.print_exc()
        finally:
            snapshot.ready.set()
    worker_thread = threading.Thread(target=worker, daemon=True)
    http_thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.2), daemon=True)
    http_thread.start(); worker_thread.start()
    print(f"AETHER-CL M6 {config.system}: http://127.0.0.1:{port}", flush=True)
    print("Initializing the preview. The arm waits for Enter.", flush=True)
    try:
        while not snapshot.ready.wait(.1):
            pass
        status, _ = snapshot.read()
        if status["state"] == "ready_to_start":
            print(f"OPEN http://127.0.0.1:{port} NOW. Initial frame ready; arm paused.", flush=True)
            input("Press Enter HERE after opening the preview: ")
            snapshot.release.set()
        while http_thread.is_alive():
            stop.wait(.2)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop.set(); snapshot.release.set()
        server.shutdown(); server.server_close()
        worker_thread.join(timeout=10); http_thread.join(timeout=5)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--system", choices=("baseline", "v1", "v2"), default="v2")
    cli.add_argument("--seed", type=int, default=100)
    cli.add_argument("--episodes", type=int, default=1)
    cli.add_argument("--max-steps", type=int, default=MAX_STEPS)
    cli.add_argument("--disturbance", choices=("none", "post_release_shift"), default="none")
    cli.add_argument("--disturbance-magnitude", type=float, default=.08)
    cli.add_argument("--render-device", default="cuda:0")
    cli.add_argument("--fps", type=float, default=10.)
    cli.add_argument("--output", type=Path, default=Path("runs/m6-live"))
    group = cli.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true")
    group.add_argument("--no-render", action="store_true")
    cli.add_argument("--port", type=int, default=8765)
    args = cli.parse_args()
    from .m6_sweep import preflight
    preflight()
    config = M6Config(system=args.system, verification=args.system != "baseline", seed=args.seed, episodes=args.episodes,
                      max_steps=args.max_steps, disturbance=args.disturbance, disturbance_magnitude=args.disturbance_magnitude,
                      render=args.live, render_device=args.render_device, fps=args.fps, output=args.output)
    if args.live:
        serve(config, args.port)
    else:
        print(json.dumps(run(config), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
