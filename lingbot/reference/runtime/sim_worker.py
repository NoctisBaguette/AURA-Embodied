"""Unattended source +200 clean scene; installed qpos/TOPP control stays in place."""
# XML must load before native graphics, SAPIEN before the task's Open3D import.
import pyexpat
import argparse
import io
import json
import os
import random
import sys
import time
import traceback
import urllib.request
from copy import deepcopy
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

ROOT=Path('/path/to/lingbot-workspace');SIM=ROOT/'RoboTwin'
sys.path.insert(0,str(SIM))
import sapien.core as sapien
from sapien.render import set_global_config
set_global_config(max_num_materials=50000,max_num_textures=50000)
_scene_renderer_bootstrap=sapien.SapienRenderer()
print('SAPIEN renderer bootstrap: PASS',flush=True)
from envs.adjust_bottle import adjust_bottle
from rollout_telemetry import EpisodeStop,joint_snapshot,observe_controller,contact_sample,telemetry_summary,ARM


def instruction_for(task):
    # Match the official evaluator's instruction API without running play_once.
    sys.path.insert(0,str(SIM/'description/utils'))
    from generate_episode_instructions import generate_episode_descriptions
    side='right' if task.qpose_tag==1 else 'left'
    info={'{A}':f'001_bottle/base{task.model_id}','{a}':side}
    generated=generate_episode_descriptions('adjust_bottle',[info],1)
    assert isinstance(generated,list) and generated and isinstance(generated[0].get('seen'),list),'Instruction generator returned an unexpected schema'
    seen=generated[0]['seen'];other='right' if side=='left' else 'left'
    candidates=[text for text in seen if isinstance(text,str) and text.strip() and side in text.lower() and other not in text.lower()]
    assert candidates,'No arm-consistent seen task instruction generated'
    return candidates[0],side,info


def make_task(seed,output):
    robot_dir=SIM/'assets/embodiments/aloha-agilex'
    args=yaml.safe_load((SIM/'task_config/demo_clean.yml').read_text())
    robot=yaml.safe_load((robot_dir/'config.yml').read_text())
    args.update(task_name='adjust_bottle',task_config='demo_clean',embodiment_name='aloha-agilex',
        left_robot_file=str(robot_dir),right_robot_file=str(robot_dir),left_embodiment_config=deepcopy(robot),
        right_embodiment_config=deepcopy(robot),dual_arm_embodied=True,render_freq=0,save_data=False,
        collect_data=False,eval_mode=True,need_plan=True,seed=seed,now_ep_num=0,save_path=str(output),eval_video_save_dir=None)
    assert args['domain_randomization']['random_background'] is False
    args['data_type'].update(rgb=True,qpos=True,pointcloud=False,depth=False)
    random.seed(seed);task=adjust_bottle();task.setup_demo(**args)
    return task


def observer_camera(task):
    from scipy.spatial.transform import Rotation
    camera=task.scene.add_camera('lingbot_diagnostic_observer',512,384,np.deg2rad(65),.1,100)
    eye=np.array([.9,.8,1.55]);forward=np.array([0.,-.35,.9])-eye;forward/=np.linalg.norm(forward)
    left=np.cross([0.,0.,1.],forward);left/=np.linalg.norm(left);up=np.cross(forward,left)
    xyzw=Rotation.from_matrix(np.column_stack([forward,left,up])).as_quat()
    camera.set_pose(sapien.Pose(p=eye,q=xyzw[[3,0,1,2]]));return camera


class Recording:
    def __init__(self,output):
        import cv2
        self.cv2=cv2;self.frames=0;self.path=output/'observer.mp4'
        self.writer=cv2.VideoWriter(str(self.path),cv2.VideoWriter_fourcc(*'mp4v'),10.,(512,384))
        assert self.writer.isOpened(),'Observer MP4 encoder unavailable'
    def write(self,rgb):
        assert rgb.shape==(384,512,3) and rgb.dtype==np.uint8
        self.writer.write(self.cv2.cvtColor(rgb,self.cv2.COLOR_RGB2BGR));self.frames+=1
    def close(self):self.writer.release()


def run_episode(task,args,instruction,side,info):
    output=Path(args.output);identity=json.loads(Path(args.ready).read_text())
    assert identity['ready'] and identity['baseline_replays']==24 and identity['role']=='retained_start_state_plus_200'
    original_limit=int(task.step_lim);task.step_lim=min(original_limit,200);task.set_instruction(instruction)
    observer=observer_camera(task);video=Recording(output);current={'action':0}
    rows=[];events=[];actions_done=[];command_records=[];chunk_records=[];timestamps=[];ticks=0;failure=None
    scene=task.scene;started=time.monotonic();stop=None;status='RUNNING';last_rgb=None
    table_height=.74+float(task.table_z_bias)
    bottle_name=str(task.bottle.actor.name);grippers=set(task.robot.gripper_name)
    def save_progress():
        progress=dict(status=status,scene_seed=args.seed,noise_seed=args.noise,requested_arm=side,instruction=instruction,
            instruction_info=info,action_steps_completed=len(actions_done),controller_actions_started=int(task.take_action_cnt),
            chunks=len(chunk_records),stop_reason=stop,original_step_limit=original_limit,debug_step_limit=task.step_lim,
            physics_steps=ticks,simulated_seconds=ticks/250.,wall_seconds=time.monotonic()-started,
            task_success=bool(task.eval_success or task.check_success()),bottle_functional_point=np.asarray(task.bottle.get_functional_point(0)).tolist(),
            scope='Bounded clean-scene engineering diagnostic; no official score',execution_prefix=50,
            normalization='Exact source +200 clean50 normalization',policy_checkpoint=identity['checkpoint'],
            telemetry=telemetry_summary(rows,events),observer_frames=video.frames,observer_video=video.path.name,
            video_time='10 fps simulation-time samples; inference pauses omitted; capture cap 2400 frames',
            contact_sampling='Every 25 physics steps and command endpoints; missing samples do not establish collision freedom',
            state_semantics='Policy input is unchanged drive-target state; measured arm qpos and physical finger qpos logged separately')
        path=output/'episode-report.json';temporary=path.with_suffix('.json.partial');temporary.write_text(json.dumps(progress,indent=2)+'\n');os.replace(temporary,path)
        return progress
    def capture():
        nonlocal last_rgb
        scene.update_render();observer.take_picture()
        rgb=np.clip(observer.get_picture('Color')[...,:3]*255,0,255).astype(np.uint8);last_rgb=rgb
        if video.frames<2400 and (not timestamps or timestamps[-1]['physics_step']!=ticks):
            video.write(rgb);timestamps.append(dict(frame=video.frames,physics_step=ticks,action_index=current['action'],wall_seconds=time.monotonic()-started))
        return rgb
    def sample(n,force=False):
        nonlocal ticks
        ticks=n
        if n%5==0 or force:
            drive,measured,fingers=joint_snapshot(task.robot);bottle=np.asarray(task.bottle.get_functional_point(0),dtype=float)
            contacts=contact_sample(scene,grippers,bottle_name) if n%25==0 or force else []
            rows.append(dict(physics_step=n,action_index=current['action'],drive=drive,measured_arm=measured,
                measured_finger_qpos=fingers,bottle=bottle,contacts=contacts))
            if n%25==0:capture()
            if bottle[2]<table_height-.10:raise EpisodeStop('bottle_fell_below_table')
        if time.monotonic()-started>=360:raise EpisodeStop('wall_time_limit')
    def request(observation,index):
        packet={'task':np.asarray(instruction),'observation.state':np.asarray(observation['joint_action']['vector'],dtype=np.float32),
            'episode_id':np.asarray(f'seed-{args.seed}-noise-{args.noise}'),'chunk_index':np.asarray(index),
            'noise_seed':np.asarray(args.noise+index-1)}
        for camera,key in [('head_camera','observation.images.cam_high'),('left_camera','observation.images.cam_left_wrist'),('right_camera','observation.images.cam_right_wrist')]:
            packet[key]=np.asarray(observation['observation'][camera]['rgb'],dtype=np.uint8)
        buffer=io.BytesIO();np.savez_compressed(buffer,**packet)
        url=f'http://127.0.0.1:{int(identity["port"])}/infer'
        req=urllib.request.Request(url,data=buffer.getvalue(),headers={'Content-Type':'application/octet-stream','X-LingBot-Run':identity['nonce']})
        with urllib.request.urlopen(req,timeout=120) as response:result=json.load(response)
        assert result['episode_id']==str(packet['episode_id']) and result['chunk_index']==index and result['checkpoint']==identity['checkpoint']
        commands=np.asarray(result['actions'],dtype=np.float32);assert commands.shape==(50,14) and np.isfinite(commands).all()
        np.savez_compressed(output/f'chunk-{index:03d}.npz',**packet,predicted_actions=commands,
            conditioned_tokens=np.asarray(result['conditioned_tokens']),conditioned_text=np.asarray(result['conditioned_text']))
        return commands,result
    try:
        Image.fromarray(capture()).save(output/'observer-start.png');sample(0,force=True);save_progress()
        with observe_controller(task,sample,events,current) as wrapped:
            while task.take_action_cnt<task.step_lim and not task.eval_success:
                if time.monotonic()-started>=360:raise EpisodeStop('wall_time_limit')
                observation=task.get_obs();index=len(chunk_records)+1;commands,response=request(observation,index)
                drive,measured,fingers=joint_snapshot(task.robot)
                chunk_records.append(dict(index=index,action_start=int(task.take_action_cnt),inference_seconds=response['inference_seconds'],
                    first_gap_drive_degrees=float(np.rad2deg(abs(commands[0,ARM]-drive[ARM]).max())),
                    first_gap_measured_degrees=float(np.rad2deg(abs(commands[0,ARM]-measured).max())),
                    largest_adjacent_target_change_degrees=float(np.rad2deg(abs(np.diff(commands[:,ARM],axis=0)).max()))))
                for offset,command in enumerate(commands):
                    if task.take_action_cnt>=task.step_lim or task.eval_success:break
                    current['action']=int(task.take_action_cnt)+1
                    before_drive,before_real,before_fingers=joint_snapshot(task.robot)
                    record=dict(chunk=index,offset=offset,action_index=current['action'],command=command.tolist(),
                        drive_before=before_drive.tolist(),measured_arm_before=before_real.tolist(),physics_before=wrapped.steps)
                    command_records.append(record)
                    try:task.take_action(command,action_type='qpos')
                    finally:
                        after_drive,after_real,after_fingers=joint_snapshot(task.robot)
                        record.update(drive_after=after_drive.tolist(),measured_arm_after=after_real.tolist(),physics_after=wrapped.steps)
                        record['endpoint_tracking_error_degrees']=float(np.rad2deg(abs(command[ARM]-after_real).max()))
                    actions_done.append(command.copy());sample(wrapped.steps,force=True)
                    if len(actions_done)%10==0:save_progress()
        stop='task_success' if task.eval_success or task.check_success() else 'step_limit'
        status='COMPLETE'
    except EpisodeStop as error:stop=str(error);status='COMPLETE'
    except Exception as error:
        failure=error;stop='runtime_error';status='ERROR';traceback.print_exc()
    finally:
        if last_rgb is not None:Image.fromarray(last_rgb).save(output/'observer-end.png')
        video.close()
        if rows:
            np.savez_compressed(output/'physics-telemetry.npz',physics_step=np.asarray([r['physics_step'] for r in rows]),
                action_index=np.asarray([r['action_index'] for r in rows]),drive=np.asarray([r['drive'] for r in rows]),
                measured_arm=np.asarray([r['measured_arm'] for r in rows]),measured_finger_qpos=np.asarray([r['measured_finger_qpos'] for r in rows]),
                bottle=np.asarray([r['bottle'] for r in rows]))
        for name,values in [('commands.json',command_records),('chunks.json',chunk_records),('topp-events.json',events),
                            ('video-timestamps.json',timestamps),('contacts.json',[dict(physics_step=r['physics_step'],contacts=r['contacts']) for r in rows if r['contacts']])]:
            (output/name).write_text(json.dumps(values,indent=2)+'\n')
        np.save(output/'executed-targets.npy',np.asarray(actions_done,dtype=np.float32).reshape(-1,14))
        report=save_progress()
        if failure:report['error']=repr(failure);(output/'episode-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if failure:raise failure
    print('EPISODE COMPLETE:',args.seed,args.noise,'task_success=',report['task_success'],'stop=',stop,flush=True)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,required=True);parser.add_argument('--noise',type=int,default=777)
    parser.add_argument('--output',required=True);parser.add_argument('--ready');parser.add_argument('--probe',action='store_true');args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True);task=None
    try:
        task=make_task(args.seed,output);instruction,side,info=instruction_for(task)
        drive,real,fingers=joint_snapshot(task.robot)
        initial=dict(status='READY',scene_seed=args.seed,requested_arm=side,instruction=instruction,model_id=int(task.model_id),
            qpose_tag=int(task.qpose_tag),drive=drive.tolist(),measured_arm=real.tolist(),bottle=np.asarray(task.bottle.get_functional_point(0)).tolist(),instruction_info=info)
        observation=task.get_obs()
        for camera in ('head_camera','left_camera','right_camera'):
            rgb=np.asarray(observation['observation'][camera]['rgb']);assert rgb.shape==(240,320,3) and rgb.dtype==np.uint8
            Image.fromarray(rgb).save(output/f'{camera}-start.png')
        (output/'scene-report.json').write_text(json.dumps(initial,indent=2)+'\n')
        if not args.probe:run_episode(task,args,instruction,side,info)
    except BaseException as error:
        path=output/'scene-report.json'
        initial=json.loads(path.read_text()) if path.exists() else {}
        initial.update(status='ERROR',error=repr(error),traceback=traceback.format_exc())
        path.write_text(json.dumps(initial,indent=2)+'\n');raise
    finally:
        if task is not None and hasattr(task,'scene'):task.close_env()


if __name__=='__main__':main()
