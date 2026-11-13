"""Fallback cleanup of recorded owned sessions after the bounded task exits."""
import json
from pathlib import Path
import sys
import time
import owned_processes

def cleanup(home):
    path = Path(home) / 'owned-children.json'
    if not path.exists():
        return True
    outcomes = []

    class ProcessRef:

        def __init__(self, pid):
            self.pid = pid

        def wait(self, timeout):
            deadline = time.monotonic() + timeout
            while owned_processes.proc_info(self.pid) is not None and time.monotonic() < deadline:
                time.sleep(0.05)
    for record in reversed(json.loads(path.read_text(encoding='utf-8'))):
        outcomes.append(owned_processes.stop_session(ProcessRef(record['pid']), record['birth']))
    return all(outcomes)
if __name__ == '__main__':
    raise SystemExit(0 if cleanup(sys.argv[1]) else 1)
