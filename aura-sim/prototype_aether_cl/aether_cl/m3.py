"""M3 baseline/V1/V2 runs and optional read-only live viewer."""

import argparse
import json
from pathlib import Path
import threading
import traceback

from .m3_runtime import M3Config, run
from .viewer import Snapshot, make_server


def parser():
    cli = argparse.ArgumentParser(description="AETHER-CL M3 matched-budget recovery candidate")
    cli.add_argument("--system", choices=("baseline", "v1", "v2"), default="v2")
    cli.add_argument("--seed", type=int, default=0)
    cli.add_argument("--episodes", type=int, default=1)
    cli.add_argument("--max-steps", type=int, default=360)
    cli.add_argument("--disturbance", choices=("none", "object_shift", "object_drop"), default="none")
    cli.add_argument("--disturbance-magnitude", type=float, default=.12)
    cli.add_argument("--render-device", default="cuda:0")
    cli.add_argument("--fps", type=float, default=10)
    cli.add_argument("--output", type=Path, default=Path("runs/m3"))
    render = cli.add_mutually_exclusive_group()
    render.add_argument("--live", action="store_true", help="Render and serve the finite run in a browser")
    render.add_argument("--no-render", action="store_true", help="Run without rendering (the default)")
    cli.add_argument("--port", type=int, default=8765)
    return cli


def config_from_args(args):
    return M3Config(system=args.system, verification=args.system != "baseline",
                    seed=args.seed, episodes=args.episodes, max_steps=args.max_steps,
                    disturbance=args.disturbance, disturbance_magnitude=args.disturbance_magnitude,
                    render=args.live, render_device=args.render_device, fps=args.fps, output=args.output)


def serve(config, port):
    config.validate()
    if not config.render:
        raise ValueError("Live runs require rendering")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    snapshot, stop = Snapshot(), threading.Event()
    server = make_server(port, snapshot)

    def worker():
        try:
            run(config, snapshot.publish, stop)
        except BaseException as error:
            status, _ = snapshot.read()
            snapshot.publish({**status, "state": "error", "error": f"{type(error).__name__}: {error}"}, None)
            traceback.print_exc()

    thread = threading.Thread(target=worker, name="aether-m3", daemon=True)
    thread.start()
    print(f"AETHER-CL M3 {config.system}: http://127.0.0.1:{port}", flush=True)
    print("Ctrl+C stops the viewer and the run. Final frame stays available after completion.", flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=10)


def main():
    args = parser().parse_args()
    config = config_from_args(args)
    if args.live:
        serve(config, args.port)
    else:
        print(json.dumps(run(config), indent=2))


if __name__ == "__main__":
    main()
