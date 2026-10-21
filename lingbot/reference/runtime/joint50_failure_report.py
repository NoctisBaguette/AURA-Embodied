"""Read a retained run directory/ZIP and show nested failures; never launch work."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

class Evidence:

    def __init__(self, source):
        self.source = Path(source).resolve()
        self.archive = None
        if self.source.is_dir():
            self.names = {p.relative_to(self.source).as_posix() for p in self.source.rglob('*') if p.is_file()}
        else:
            self.archive = zipfile.ZipFile(self.source)
            items = self.archive.namelist()
            if len(items) != len(set(items)):
                raise ValueError('Duplicate archive entries')
            for name in items:
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('Unsafe archive entry')
            bad = self.archive.testzip()
            if bad:
                raise ValueError('Archive CRC failed: ' + bad)
            self.names = {n for n in items if not n.endswith('/')}

    def close(self):
        if self.archive:
            self.archive.close()

    def text(self, name):
        if name not in self.names:
            return None
        if self.archive:
            data = self.archive.read(name)
        else:
            path = (self.source / name).resolve()
            if not path.is_relative_to(self.source):
                raise ValueError('Evidence symlink escaped run directory')
            data = path.read_bytes()
        return data.decode('utf-8', errors='replace')

    def json(self, name):
        value = self.text(name)
        return json.loads(value) if value is not None else None

def collect(source):
    evidence = Evidence(source)
    try:
        parent = evidence.json('report.json') or {}
        result = dict(source=str(evidence.source), parent=parent, failures=[])
        error = str(parent.get('error', ''))
        match = re.search('Simulator (?:pilot case|commissioning) (?:failed|timed out): (.+?)(?: exit=-?\\d+|$)', error)
        cases = set()
        if match:
            parts = PurePosixPath(match.group(1)).parts
            for i, part in enumerate(parts):
                if part in ('baseline', 'trained', 'commission') and i + 1 < len(parts):
                    cases.add('/'.join(parts[i:i + 2]))
                    break
        for name in evidence.names:
            parts = PurePosixPath(name).parts
            if len(parts) == 3 and parts[0] in ('baseline', 'trained', 'commission') and (parts[2] == 'failure.json'):
                cases.add('/'.join(parts[:2]))
        for case in sorted(cases):
            failure = evidence.json(case + '/failure.json') or {}
            result['failures'].append(dict(component='simulator', directory=case, error=failure.get('error'), traceback=failure.get('traceback'), structured_failure=failure, case_report=evidence.json(case + '/report.json'), sim_log=evidence.text(case + '/sim.log'), native_stacks=evidence.text(case + '/native-stacks.log')))
        if not result['failures']:
            policy = evidence.json('policy/report.json') or {}
            if policy.get('status') == 'ERROR' or parent.get('phase') in ('BASELINE_POLICY_LOADING', 'WAITING_POLICY_GPU'):
                result['failures'].append(dict(component='policy', directory='policy', error=policy.get('error'), traceback=policy.get('traceback'), structured_failure=policy, sim_log=evidence.text('policy.log')))
        result['nested_evidence_available'] = any((f.get('traceback') or f.get('sim_log') for f in result['failures']))
        return result
    finally:
        evidence.close()

def render(result):
    parent = result['parent']
    lines = ['Retained evidence: ' + result['source'], 'Run status: ' + str(parent.get('status')) + '; phase: ' + str(parent.get('phase')), 'Manager error: ' + str(parent.get('error', 'none recorded'))]
    for failure in result['failures']:
        lines += ['\n=== ' + failure['component'].upper() + ': ' + failure['directory'] + ' ===', 'Structured error: ' + str(failure.get('error', 'missing'))]
        case = failure.get('case_report') or {}
        if case:
            lines += ['Child status: ' + str(case.get('status')) + '; child-recorded episodes: ' + str(len(case.get('episodes', []))), 'Candidate seeds: ' + str(case.get('candidate_seeds', [])), 'Recorded rejections: ' + json.dumps(case.get('rejections', []), allow_nan=False)]
        for key, label in [('traceback', 'Full structured traceback'), ('sim_log', 'Full process log'), ('native_stacks', 'Full native stack capture')]:
            if failure.get(key):
                lines += ['\n--- ' + label + ' ---', failure[key]]
    if not result['nested_evidence_available']:
        lines += ['No nested traceback/log found. The parent exit code does not establish the root cause.']
    return '\n'.join(lines) + '\n'
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = collect(args.source)
    print(json.dumps(result, indent=2, allow_nan=False) if args.json else render(result), end='\n' if args.json else '')
