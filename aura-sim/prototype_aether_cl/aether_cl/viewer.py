"""Read-only browser viewer for a bounded simulator or controller run."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import traceback
from urllib.parse import urlsplit

from .runtime import config_from_args, parser, run


class Snapshot:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = {"state": "waiting", "frame_number": 0}
        self.jpeg = None
        self.frame_number = 0

    def publish(self, status, jpeg):
        with self.lock:
            if jpeg is not None:
                self.jpeg = jpeg
                self.frame_number += 1
            self.status = {**status, "frame_number": self.frame_number}

    def read(self):
        with self.lock:
            return {**self.status}, self.jpeg


class Server(ThreadingHTTPServer):
    daemon_threads = True


def make_server(port, snapshot):
    page = Path(__file__).with_name("index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            status, jpeg = snapshot.read()
            if path == "/":
                body, mime, code = page, "text/html; charset=utf-8", 200
            elif path == "/api/status":
                body = json.dumps(status, allow_nan=False).encode("utf-8")
                mime, code = "application/json", 200
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

        def log_message(self, format, *args):
            pass

    return Server(("127.0.0.1", port), Handler)


def main():
    args_parser = parser("AETHER-CL live simulator and fixed-controller viewer")
    args_parser.add_argument("--port", type=int, default=8765)
    args = args_parser.parse_args()
    config = config_from_args(args)
    config.validate()
    if not config.render:
        args_parser.error("the live viewer requires rendering; use smoke --no-render instead")
    if not 1 <= args.port <= 65535:
        args_parser.error("port must be between 1 and 65535")
    snapshot, stop = Snapshot(), threading.Event()
    # Bind first so an occupied port cannot start an unwanted simulator job.
    server = make_server(args.port, snapshot)

    def worker():
        try:
            run(config, snapshot.publish, stop)
        except BaseException as error:
            status, _ = snapshot.read()
            snapshot.publish({**status, "state": "error",
                              "error": f"{type(error).__name__}: {error}"}, None)
            traceback.print_exc()

    thread = threading.Thread(target=worker, name="aether-simulation", daemon=True)
    thread.start()
    print(f"AETHER-CL viewer: http://127.0.0.1:{args.port}", flush=True)
    print(f"Controller: {config.controller}. Ctrl+C stops the viewer and the run.", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
