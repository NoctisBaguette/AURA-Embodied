"""Bounded read-only admission; never stops other processes or retries model failures."""
import csv
import json
import os
import subprocess
import time
from portable_manifest import require


def wait_gpu(uuid,timeout=600,query=None,sleep=time.sleep,clock=time.monotonic):
    require(isinstance(uuid,str) and uuid.startswith('GPU-') and os.environ.get('CUDA_VISIBLE_DEVICES')==uuid,'GPU UUID/environment mismatch')
    require(type(timeout) is int and 15<=timeout<=43200,'Admission timeout outside 15s..12h')
    def inventory():
        result=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],check=True,text=True,capture_output=True,timeout=15)
        return list(csv.reader(result.stdout.splitlines()))
    query=query or inventory
    deadline=clock()+timeout; stable=0
    while clock()<deadline:
        rows=[row for row in query() if len(row)==3 and row[0].strip()==uuid]
        require(len(rows)==1,'Admitted GPU absent or ambiguous')
        free_gib=float(rows[0][1])/1024; util=float(rows[0][2])
        stable=stable+1 if free_gib>=60 and util<=10 else 0
        print(json.dumps({'stage':'GPU_ADMISSION','uuid':uuid,'free_gib':free_gib,'utilization':util,'stable_samples':stable,'required_samples':3}),flush=True)
        if stable>=3:return
        sleep(min(5,max(0,deadline-clock())))
    raise TimeoutError('GPU admission deadline; no model load attempted')
