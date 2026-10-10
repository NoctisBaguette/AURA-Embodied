"""V3 subprocess adapter with explicit frozen attribution-family argument."""

import json
import os
import signal
import subprocess
import sys

def run_v3_process(config, environment):
    module = "aether_cl.m5_v3"
    """Use exec, not fork reuse: native imports can modify process environment."""
    config.output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", module, "--system",
               getattr(config, "system", "v1" if config.verification else "baseline"), "--no-render",
               "--seed", str(config.seed), "--episodes", str(config.episodes),
               "--max-steps", str(config.max_steps), "--render-device", config.render_device,
               "--fps", str(config.fps),
               "--disturbance", config.disturbance, "--disturbance-magnitude",
               str(config.disturbance_magnitude), "--output", str(config.output), "--family", config.family]
    with (config.output / "process.stdout.log").open("w", encoding="utf-8") as stdout, \
            (config.output / "process.stderr.log").open("w", encoding="utf-8") as stderr:
        # The target is Linux. A separate session lets Ctrl+C reach the suite,
        # which then signals and joins this child before evidence is archived.
        process = subprocess.Popen(command, env=environment.copy(), stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        try:
            returncode = process.wait()
        except KeyboardInterrupt:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise
    if returncode:
        raise RuntimeError(f"Trial process exited {returncode}; see {config.output / 'process.stderr.log'}")
    results = sorted(config.output.glob("*/result.json"))
    if len(results) != 1:
        raise RuntimeError(f"Expected one trial result, found {len(results)} in {config.output}")
    return json.loads(results[0].read_text(encoding="utf-8"))

