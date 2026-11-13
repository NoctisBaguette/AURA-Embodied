"""Run the retained scene code normally, with the audited instruction/stack hooks."""
import ast
import faulthandler
import hashlib
import os
from pathlib import Path
import signal
import sys
import traceback

import startup_support as startup

HERE = Path(__file__).resolve().parent
SUPPORT_SHA = '5690b4dd4acf27b3fad489b199e43ac2707aab59a8963af791f6a60b865ea977'


def record_failure(error, output):
    frames = traceback.extract_tb(error.__traceback__)
    setup_path = str(startup.PROJECT / 'RoboTwin/envs/_base_task.py')
    during_setup = any(f.filename == setup_path and f.name == '_init_task_env_' for f in frames)
    probe = '--probe' in sys.argv and '--noise' not in sys.argv and '--ready' not in sys.argv
    typed = type(error).__module__ == 'envs.utils.create_actor' and type(error).__name__ == 'UnStableError'
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else None
    value = dict(schema_version=1, scene_seed=seed, pid=os.getpid(), exception_module=type(error).__module__,
                 exception_type=type(error).__name__, message=str(error),
                 during_setup=during_setup, probe=probe,
                 category='UNSTABLE_SETUP' if typed and during_setup and probe else 'FATAL_SCENE_ERROR',
                 traceback=''.join(traceback.format_exception(type(error), error, error.__traceback__)))
    startup.atomic_json(output / 'scene-failure.json', value)


def run():
    if hashlib.sha256((HERE / 'startup_support.py').read_bytes()).hexdigest() != SUPPORT_SHA:
        raise RuntimeError('Audited startup support changed')
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=True)
    startup.OUT = output
    startup._active_stages.clear()
    originals = []
    source = HERE / 'sim_worker.py'
    with (output / 'startup-stacks.log').open('a', buffering=1) as stacks, (output / 'startup-stages.jsonl').open('a', buffering=1) as events:
        startup._events = events
        faulthandler.enable(file=stacks, all_threads=True)
        faulthandler.register(signal.SIGUSR1, file=stacks, all_threads=True, chain=False)
        faulthandler.dump_traceback_later(30, repeat=True, file=stacks)
        tree = startup.instrument_scene(source.read_text())
        (output / 'instrumented-scene.py').write_text(ast.unparse(tree) + '\n')
        namespace = dict(__name__='__main__', __file__=str(source),
                         _startup_stage=startup.stage, _startup_originals=originals,
                         _startup_install_hooks=startup.install_hooks,
                         _startup_instruction=startup.traced_instruction)
        def wrap(function, label):
            @startup.functools.wraps(function)
            def call(*args, **kwargs):
                startup.stage(label)
                try:
                    result = function(*args, **kwargs)
                except BaseException as error:
                    startup.stage(label, 'ERROR', error=repr(error))
                    raise
                startup.stage(label, 'END')
                return result
            return call
        namespace['_startup_wrap_function'] = wrap
        try:
            startup.stage('execute_saved_scene')
            # Keep the actual --seed/--probe or --noise/--ready arguments.
            exec(compile(tree, str(source), 'exec'), namespace)
            startup.stage('execute_saved_scene', 'END')
        except BaseException as error:
            record_failure(error, output)
            startup.stage('execute_saved_scene', 'ERROR', error=repr(error))
            raise
        finally:
            for cls, name, original in reversed(originals):
                setattr(cls, name, original)
            startup.stage('method_hooks_restored', 'END', count=len(originals))
            faulthandler.cancel_dump_traceback_later()
            faulthandler.unregister(signal.SIGUSR1)
            # Keep shutdown faults visible after the dedicated file closes.
            faulthandler.enable(file=sys.stderr, all_threads=True)
            faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True, chain=False)
            faulthandler.dump_traceback_later(30, repeat=True, file=sys.stderr)


if __name__ == '__main__':
    run()
