"""Read-only prior-startup gate and original rollout CPU provenance/codec checks."""
import argparse
import hashlib
import json
from pathlib import Path
import rollout_preflight
import startup_support

PROJECT = Path('/path/to/lingbot-workspace')
REFERENCE = PROJECT / 'data-preparation/simulator-native-trace-v2/run-rpIiJrrN'
SUPPORT_SHA = '5690b4dd4acf27b3fad489b199e43ac2707aab59a8963af791f6a60b865ea977'


def reference_check():
    path = REFERENCE / 'report.json'
    result = json.loads(path.read_text())
    native = result.get('native_capture', {})
    expected = dict(status='COMPLETE', diagnostic_outcome='SIMULATOR_STARTED_UNDER_DEBUGGER',
                    scene_ready=True, simulator_qualified=True, original_files_unchanged=True,
                    owned_processes_stopped=True, model_loaded=False, policy_loaded=False,
                    training_updates=0, worker_exit_code=0)
    if any(result.get(k) != v for k, v in expected.items()) or not (
            native.get('inferior_exit_code') == native.get('debugger_exit_code') == 0
            and native.get('parent_timeout') is False):
        raise RuntimeError('Prior GDB startup report is not qualified')
    worker = REFERENCE / 'startup-original.py'
    if hashlib.sha256(worker.read_bytes()).hexdigest() != SUPPORT_SHA:
        raise RuntimeError('Prior qualified startup worker changed')
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, worker)}


def run(home, output):
    home = Path(home)
    manifest = json.loads((home / 'payload-sha256.json').read_text())
    for name, expected in manifest.items():
        if Path(name).name != name or hashlib.sha256((home / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Rollout payload changed before execution: ' + name)
    protected = reference_check()
    support = startup_support.preflight()
    protected.update(support['protected_files'])
    result = rollout_preflight.run(home, output)
    protected.update(result['protected_files'])
    result.update(protected_files=protected, prior_gdb_startup=str(REFERENCE),
                  instructions=support['instructions'], simulator_packages=support['packages'],
                  instruction_generator='Audited full seen-template cycle and whole arm words',
                  simulation='Fresh normal-process probes required before policy loading')
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.home, args.output)
