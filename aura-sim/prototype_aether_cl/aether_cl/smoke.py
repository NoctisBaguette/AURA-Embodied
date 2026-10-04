"""Run a finite smoke test and save its logs and latest rendered frame."""

import json

from .runtime import config_from_args, parser, run


def main():
    args = parser("AETHER-CL environment smoke test; random actions, not a baseline").parse_args()
    result = run(config_from_args(args))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
