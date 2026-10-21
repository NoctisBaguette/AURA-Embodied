"""CPU/file checks before waiting, repeated after admission before GPU work."""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

PROJECT=Path('/path/to/lingbot-workspace')
SIM_PY=Path('/path/to/conda/envs/robotwin-sim/bin/python')

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def run(home,output):
    home=Path(home);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    protected={}
    def pin(path,expected=None):
        path=Path(path);actual=digest(path)
        if expected is not None and actual!=expected:raise RuntimeError('Pinned source changed: '+str(path))
        protected[str(path)]=actual
    manifest=json.loads((home/'source-pins.json').read_text())
    for relative,expected in manifest.items():pin(PROJECT/relative,expected)
    generator=PROJECT/'RoboTwin/description/utils/generate_episode_instructions.py'
    if not generator.is_file():raise RuntimeError('Existing RoboTwin instruction generator missing: '+str(generator))
    compile(generator.read_text(),str(generator),'exec');pin(generator)
    previous=os.environ.get('LINGBOT_MOTION_OUT');os.environ['LINGBOT_MOTION_OUT']=str(output.parent)
    try:
        spec=importlib.util.spec_from_file_location('preflight_core',home/'model_core.py')
        core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
        core.validate_phase_source()
        for name,expected in core.SOURCE_FILES.items():pin(core.SOURCE_RUN/name,expected)
        metadata=json.loads((core.SOURCE_STAGE/'checkpoint.json').read_text());pin(core.SOURCE_STAGE/'checkpoint.json')
        for name,expected in metadata['files'].items():pin(core.SOURCE_STAGE/name,expected)
        for name in ('latest-checkpoint.json','resolved-inputs.json'):pin(core.RUN/'training-smoke'/name)
        identity=json.loads((core.RUN/'training-smoke/resolved-inputs.json').read_text())
        checkpoint=Path(json.loads((core.RUN/'training-smoke/latest-checkpoint.json').read_text())['directory'])
        original=json.loads((checkpoint/'checkpoint.json').read_text())
        if original['completed_updates']!=10000 or original['identity']!=identity:raise RuntimeError('Original training identity changed')
        pin(checkpoint/'checkpoint.json')
        for name,expected in original['files'].items():
            if Path(name).name!=name:raise RuntimeError('Unsafe checkpoint filename')
            pin(checkpoint/name,expected)
        for name,key in [('modeling_lingbot_vla_v2.py','policy_sha256'),('qwen2_action_expert.py','moe_sha256')]:
            pin(PROJECT/'lingbot-vla-v2/lingbotvla/models/vla/lingbot_vla'/name,identity[key])
    finally:
        if previous is None:os.environ.pop('LINGBOT_MOTION_OUT',None)
        else:os.environ['LINGBOT_MOTION_OUT']=previous
    # Run in the simulator interpreter without importing SAPIEN or creating CUDA.
    code=r'''
import pyexpat, compileall, json, sys
from pathlib import Path
import cv2, numpy as np, yaml
sim=Path(sys.argv[1]);temporary=Path(sys.argv[2]);robot=sim/'assets/embodiments/aloha-agilex'
for side in ('left','right'):
    config=yaml.safe_load((robot/f'curobo_{side}.yml').read_text())['robot_cfg']['kinematics']
    for key in ('urdf_path','collision_spheres'):
        value=config[key];assert isinstance(value,str) and Path(value).is_file(),(side,key,value)
path=temporary/'codec.mp4';writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),10.,(512,384))
assert writer.isOpened(),'MP4 writer unavailable'
for value in (0,128):writer.write(np.full((384,512,3),value,np.uint8))
writer.release();reader=cv2.VideoCapture(str(path));okay,frame=reader.read();reader.release()
assert okay and frame.shape==(384,512,3),'MP4 cannot be decoded'
print('CPU XML/YAML/OpenCV/MP4 and existing planner paths: PASS')
'''
    with tempfile.TemporaryDirectory(prefix='rollout-codec-') as temporary:
        result=subprocess.run([str(SIM_PY),'-u','-c',code,str(PROJECT/'RoboTwin'),temporary],
            env={**os.environ,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=90)
        print(result.stdout,end='',flush=True)
        if result.returncode:raise RuntimeError('Simulator CPU preflight failed: '+result.stderr[-5000:])
    report=dict(status='PASS',gpu_work_started=False,protected_files=protected,
        instruction_generator='Existing official evaluator API; runtime generation checked again in the scene',
        simulation='Not started by CPU preflight')
    output.write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    run(args.home,args.output)
