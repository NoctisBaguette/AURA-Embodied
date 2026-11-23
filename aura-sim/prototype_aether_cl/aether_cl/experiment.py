"""M2 baseline or passive-verification runs under matched task rules."""

import json

from .runtime import config_from_args, parser, run


def main():
    cli = parser("AETHER-CL M2 passive verification; no recovery")
    cli.set_defaults(controller="fixed_pick_cube", protocol="m2", verification=True,
                     max_steps=360, episodes=1, output="runs/m2")
    cli.add_argument("--system", choices=("baseline", "v1"), default="v1")
    args = cli.parse_args()
    if args.controller != "fixed_pick_cube" or args.protocol != "m2":
        cli.error("experiment requires fixed_pick_cube and protocol m2")
    args.verification = args.system == "v1"
    print(json.dumps(run(config_from_args(args)), indent=2))


if __name__ == "__main__":
    main()
