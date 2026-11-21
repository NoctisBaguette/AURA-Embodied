"""CPU checks and real demonstration frames before any GPU inventory query."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import traceback
from joint50_common import atomic_json, reviewed_inputs, source_frames

def run(home, output):
    from panel_preflight import run as old_preflight
    preview = Path(output).parent / 'source-preview'
    preview.mkdir(exist_ok=True)
    try:
        from joint50_common import PROJECT, require
        require(shutil.disk_usage(PROJECT).free >= 8 * 1024 ** 3, 'Need 8 GiB free for new checkpoints/videos; no GPU work started')
        result = old_preflight(home, output)
        audit, schedule = reviewed_inputs()
        from joint50_common import SIM_PY, PROJECT
        environment = {**os.environ, 'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0', 'PYTHONIOENCODING': 'utf-8', 'CUDA_VISIBLE_DEVICES': '', 'PYTHONPATH': str(home)}
        subprocess.run([SIM_PY, '-B', str(home / 'joint50_sim.py'), '--check-source', '--output', str(preview / 'ascii-source-check')], env=environment, cwd=PROJECT / 'RoboTwin', check=True, timeout=60)
        result['ascii_source_check'] = 'PASS'
        count = source_frames(preview / 'source-frames', audit)
        result.update(source_frames=count, input_audit='COMPLETE', planned_samples=len(schedule['global_indices']), scope='CPU/source/demo-image validation only; no model or simulator')
        atomic_json(output, result)
        atomic_json(preview / 'report.json', dict(result, stage='CPU_READY'))
        return result
    except BaseException as error:
        atomic_json(preview / 'failure.json', dict(error=str(error), traceback=traceback.format_exc()))
        raise
    finally:
        from joint50_pack import package
        package(preview)
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    run(Path(args.home), Path(args.output))
