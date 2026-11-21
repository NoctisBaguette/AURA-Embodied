import os
from pathlib import Path
import signal
import subprocess
import time

def proc_info(pid):
    try:
        path = Path('/proc') / str(pid)
        values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=int(pid), state=values[0], session=os.getsid(int(pid)), start=int(values[19]), uid=path.stat().st_uid)
    except (OSError, ValueError, IndexError):
        return None

def owned_session(pid, birth):
    leader = proc_info(pid)
    if leader and leader['start'] != birth:
        return []
    result = []
    for candidate in process_ids():
        info = proc_info(candidate)
        if info and info['uid'] == os.getuid() and (info['session'] == pid) and (info['start'] >= birth) and (info['state'] != 'Z'):
            result.append(info)
    return result

def process_ids():
    return [int(path.name) for path in Path('/proc').iterdir() if path.name.isdecimal()]

def stop_session(process, birth):
    for signum, grace in ((signal.SIGTERM, 2), (signal.SIGKILL, 2)):
        victims = owned_session(process.pid, birth)
        if not victims:
            break
        for victim in victims:
            current = proc_info(victim['pid'])
            if current and all((current[k] == victim[k] for k in ('start', 'session', 'uid'))):
                try:
                    os.kill(victim['pid'], signum)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and owned_session(process.pid, birth):
            time.sleep(0.05)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    return not owned_session(process.pid, birth)
