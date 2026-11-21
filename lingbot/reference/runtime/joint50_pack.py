"""Atomic review packages; weights and large processed-image tensors stay external."""
import argparse
import io
import json
import os
from pathlib import Path
import time
import zipfile
import numpy as np
from joint50_common import ROOT, atomic_json, digest

def package(home, exit_code=None):
    home = Path(home)
    if exit_code is not None:
        (home / 'check.exit').write_text(str(exit_code) + '\n', encoding='utf-8')
        path = home / 'report.json'
        if path.exists():
            report = json.loads(path.read_text(encoding='utf-8'))
            report['worker_exit_code'] = exit_code
            if exit_code and report.get('status') != 'ERROR':
                report.update(status='ERROR', error='Outer task exited ' + str(exit_code))
            atomic_json(path, report)
    folder = home / 'packages'
    folder.mkdir(exist_ok=True)
    archive = folder / f'review-{time.time_ns()}.zip'
    manifest = {}
    raw_stages = set()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=2) as bundle:
        for path in sorted(home.rglob('*')):
            if not path.is_file() or folder in path.parents or path.suffix in ('.pt', '.safetensors', '.pyc') or path.name.startswith('core.') or (path.name == 'core'):
                continue
            if any((part == '__pycache__' for part in path.parts)):
                continue
            relative = path.relative_to(home)
            if path.suffix == '.npz':
                if path.name.endswith('.input.npz'):
                    stage = path.parent.name
                    if stage in raw_stages:
                        continue
                    raw_stages.add(stage)
                with np.load(path, allow_pickle=False) as values:
                    data = {key: values[key] for key in values.files if key != 'images'}
                stream = io.BytesIO()
                np.savez_compressed(stream, **data)
                payload = stream.getvalue()
                bundle.writestr(str(relative), payload)
                manifest[str(relative)] = {'source_sha256': digest(path), 'packaged_array_keys': list(data)}
            elif path.suffix in ('.json', '.jsonl', '.py', '.sh', '.txt', '.log', '.exit', '.jpg', '.png', '.mp4'):
                bundle.write(path, str(relative))
                manifest[str(relative)] = {'sha256': digest(path), 'bytes': path.stat().st_size}
        bundle.writestr('PACKAGE-SCOPE.txt', 'Actual camera images/videos and numerical predictions. One raw first-request packet per policy stage is included. Repeated processed-image tensors, weight/optimizer bytes and other raw packets remain on the server. Pilot results are not a full official score.\n')
        bundle.writestr('package-manifest.json', json.dumps(manifest, indent=2))
    (folder / (archive.name + '.sha256')).write_text(digest(archive) + '\n', encoding='utf-8')
    ROOT.mkdir(exist_ok=True, parents=True)
    temporary = ROOT / ('latest-' + str(time.time_ns()) + '.partial')
    temporary.symlink_to(archive)
    os.replace(temporary, ROOT / 'latest.zip')
    print('Review package:', archive, flush=True)
    return archive
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('home')
    parser.add_argument('exit_code', nargs='?', type=int)
    args = parser.parse_args()
    package(args.home, args.exit_code)
