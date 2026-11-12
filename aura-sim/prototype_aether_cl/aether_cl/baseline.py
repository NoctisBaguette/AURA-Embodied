"""Evaluate the fixed PickCube controller candidate, without recovery."""

import json

from .runtime import config_from_args, parser, run


def main():
    cli = parser("AETHER-CL fixed state-based PickCube controller candidate")
    cli.set_defaults(controller="fixed_pick_cube", max_steps=360, episodes=5,
                     output="runs/baseline")
    args = cli.parse_args()
    if args.controller != "fixed_pick_cube":
        cli.error("baseline requires --controller fixed_pick_cube")
    result = run(config_from_args(args))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
