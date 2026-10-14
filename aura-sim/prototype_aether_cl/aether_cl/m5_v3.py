"""Native child CLI for the preregistered V3 scheduled causal control."""

import argparse
import json
from pathlib import Path

from .m5_v3_runtime import V3Config, run


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--system", choices=("v3",), default="v3")
    cli.add_argument("--family", choices=("shift", "drop"), required=True)
    cli.add_argument("--seed", type=int, default=80)
    cli.add_argument("--episodes", type=int, default=1)
    cli.add_argument("--max-steps", type=int, default=360)
    cli.add_argument("--disturbance", choices=("none", "object_shift", "object_drop"), default="none")
    cli.add_argument("--disturbance-magnitude", type=float, default=.12)
    cli.add_argument("--render-device", default="cuda:0")
    cli.add_argument("--fps", type=float, default=5.)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--no-render", action="store_true")
    args = cli.parse_args()
    result = run(V3Config(family=args.family, seed=args.seed, episodes=args.episodes,
                         max_steps=args.max_steps, disturbance=args.disturbance,
                         disturbance_magnitude=args.disturbance_magnitude,
                         render=False, render_device=args.render_device, fps=args.fps, output=args.output))
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["state"] == "finished" else 2)


if __name__ == "__main__":
    main()
