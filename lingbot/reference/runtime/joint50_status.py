"""Read-only watcher/run progress and current review package location."""
import json
from pathlib import Path

def show_status(root):
    root = Path(root)
    pointer = root / 'active-run.txt'
    if pointer.exists():
        run = Path(pointer.read_text(encoding='utf-8').strip()).resolve()
        if run.parent != root.resolve() or not run.name.startswith('run-'):
            raise RuntimeError('Invalid run pointer')
        print('Latest attempt:', run)
        path = run / 'report.json'
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            print('Run status:', value['status'], 'phase:', value['phase'])
            print('Native simulator commissioned:', len(value.get('commissioned_cases', [])), '/16; complete:', value.get('native_simulator_commissioned', False))
            print('Baseline completed:', len(value.get('baseline', [])), '/32; candidate completed:', len(value.get('trained', [])), '/32')
            admission = value.get('policy_gpu_admission', {})
            if admission:
                print('Policy GPU gate:', admission.get('status'), 'UUID:', admission.get('uuid'), 'attempts:', admission.get('attempts'), 'model load stage entered:', admission.get('model_load_started', False))
        progress = run / 'training/progress.json'
        if progress.exists():
            value = json.loads(progress.read_text(encoding='utf-8'))
            print('Training:', value.get('status'), 'updates:', value.get('completed_updates', value.get('update')), 'samples:', value.get('samples_consumed'), 'last loss:', value.get('action_loss'))
        for path in (run / 'check.log', run / 'policy.log'):
            if path.exists():
                print('\nLatest ' + path.name + ':\n' + '\n'.join(path.read_text(errors='replace', encoding='utf-8').splitlines()[-8:]))
    if pointer.exists() and (run / 'report.json').exists() and (json.loads((run / 'report.json').read_text(encoding='utf-8')).get('status') == 'ERROR'):
        from joint50_failure_report import collect, render
        print(render(collect(run)))
    latest = root / 'latest.zip'
    if latest.exists():
        print('Review package:', latest, '->', latest.resolve())
