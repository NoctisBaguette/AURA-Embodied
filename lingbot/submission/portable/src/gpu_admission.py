"""Bounded same-UUID admission with three stable samples and a final recheck."""
import csv
import json
import math
import os
import subprocess
import time
from portable_manifest import require


def wait_gpu(uuid, timeout=600, query=None, sleep=time.sleep, clock=time.monotonic,
             *, deadline_epoch=None, wall_clock=time.time, progress=None, cancelled=None):
    require(isinstance(uuid,str) and uuid.startswith('GPU-') and os.environ.get('CUDA_VISIBLE_DEVICES')==uuid,
            'GPU UUID/environment mismatch')
    require(type(timeout) is int and 15 <= timeout <= 43200, 'Admission timeout outside 15s..12h')
    if deadline_epoch is not None:
        require(type(deadline_epoch) in (int,float) and math.isfinite(deadline_epoch)
                and deadline_epoch <= wall_clock()+43205, 'Invalid original admission deadline')
    def inventory():
        r=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.free,utilization.gpu',
            '--format=csv,noheader,nounits'],check=True,text=True,capture_output=True,timeout=15)
        return list(csv.reader(r.stdout.splitlines()))
    query=query or inventory
    local_deadline=clock()+timeout
    def remains():
        return min(local_deadline-clock(), deadline_epoch-wall_clock() if deadline_epoch is not None else float('inf'))
    def sample():
        rows=[r for r in query() if len(r)==3 and r[0].strip()==uuid]
        require(len(rows)==1, 'Admitted GPU absent or ambiguous')
        free=float(rows[0][1])/1024; util=float(rows[0][2])
        require(math.isfinite(free) and math.isfinite(util) and free>=0 and 0<=util<=100, 'Invalid GPU inventory')
        return free,util
    stable=0
    while remains()>0:
        require(not cancelled or not cancelled(), 'GPU wait cancelled before model load')
        free,util=sample()
        stable=stable+1 if free>=60 and util<=10 else 0
        event=dict(status='CHECKING' if stable else 'WAITING', uuid=uuid, free_gib=free,
                   utilization=util, stable_samples=stable, required_samples=3)
        print(json.dumps(event),flush=True)
        if progress: progress(event)
        if stable>=3:
            free,util=sample()
            if free>=60 and util<=10 and remains()>0 and (not cancelled or not cancelled()):
                if progress: progress(dict(status='ADMITTED',uuid=uuid,free_gib=free,utilization=util,final_recheck=True))
                return
            stable=0
        # Check cancellation/deadline every second while retaining bounded polling.
        until=clock()+min(5,max(0,remains()))
        while clock()<until and remains()>0:
            require(not cancelled or not cancelled(), 'GPU wait cancelled before model load')
            sleep(min(1,until-clock(),max(0,remains())))
    if progress: progress(dict(status='EXPIRED',uuid=uuid))
    raise TimeoutError('Original GPU admission deadline; no model load attempted')
