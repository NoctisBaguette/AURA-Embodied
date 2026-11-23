"""Render audited M7 records as a cutaway geometry movie, without simulation.

The orange/white peg, target inner channel, and TCP use recorded poses. The arm
is deliberately omitted. No environment is created, no seed is reset, and no
action or outcome is generated. Geometry is shown as a cutaway, not camera RGB.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial.transform import Rotation

MEASUREMENT = 'a51e5d2073c4033141b26e956804d593aa45d6df'
CONTROL_HZ = 20
FACES = np.array([[0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5]])
SIGNS = np.array([[-1,-1,-1],[-1,-1,1],[-1,1,-1],[-1,1,1],
                  [1,-1,-1],[1,-1,1],[1,1,-1],[1,1,1]])

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def vec(value, n):
    v=np.asarray(value,dtype=float).reshape(-1)
    if v.shape!=(n,) or not np.isfinite(v).all(): raise ValueError('Malformed finite state vector')
    return v

def rot(pose):
    q=vec(pose,7)[3:]
    return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()

def cuboid(lo, hi):
    lo,hi=np.asarray(lo),np.asarray(hi)
    return (lo+hi)/2 + SIGNS*(hi-lo)/2

def into_hole(vertices, actor, hole):
    actor,hole=vec(actor,7),vec(hole,7)
    world=vertices@rot(actor).T+actor[:3]
    return (world-hole[:3])@rot(hole)

def load(root, ratio, seed, system):
    suite=json.loads((root/'suite.json').read_text())
    if suite['state']!='passed' or suite['native']['software']['git_commit']!=MEASUREMENT:
        raise ValueError('Require the completed, frozen M7 record')
    trial=next(t for t in suite['trials'] if (t['ratio'],t['seed'],t['system'])==(ratio,seed,system))
    directory=root/trial['run_directory']
    if root not in directory.resolve().parents: raise ValueError('Unsafe trial path')
    index={e['path']:e for e in json.loads((root/'archive_index.json').read_text())['files']}
    hashes=[]
    for name in ('manifest.json','result.json','events.jsonl'):
        p=directory/name; entry=index[str(p.relative_to(root))]
        if sha(p)!=entry['sha256'] or p.stat().st_size!=entry['bytes']: raise ValueError('Raw record changed: '+name)
        hashes.append(entry)
    events=[json.loads(line) for line in (directory/'events.jsonl').open()]
    reset=next(e for e in events if e['event']=='reset')
    steps=[e for e in events if e['event']=='step']
    if [e['step'] for e in steps]!=list(range(1,1201)): raise ValueError('Require every original control state')
    if json.loads((directory/'result.json').read_text())!=trial['result']: raise ValueError('Child/parent result differs')
    first={'step':0,'observation':reset['observation'],'info':reset['info'],
           'controller_decision':{'phase':'reset'},'reference':None}
    return {'trial':trial,'states':[first]+steps,'hashes':hashes}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=140)
    ap.add_argument('--ratio',type=float,default=2.)
    ap.add_argument('--stride',type=int,default=2,choices=range(1,5))
    args=ap.parse_args();root=args.evidence.resolve();output=args.output.resolve()
    if root==output or root in output.parents: raise ValueError('Keep movies outside raw evidence')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() or output.with_suffix('.receipt.json').exists(): raise FileExistsError('Retain previous movie; choose a new output name')
    recordings=[load(root,args.ratio,args.seed,s) for s in ('baseline','v2')]
    # This chosen demonstration is an audited paired rescue, never a substituted outcome.
    if recordings[0]['trial']['result']['task_success_at_end'] or not recordings[1]['trial']['result']['task_success_at_end']:
        raise ValueError('The selected pair is not Baseline-fail / V2-success; choose and label it explicitly')
    baseline,v2=recordings
    for i in range(643):
        a,b=baseline['states'][i],v2['states'][i]
        if a['observation']!=b['observation'] or a['info']!=b['info']:
            raise ValueError('Selected pair changed before first recovery action')
    half=vec(baseline['states'][0]['observation']['extra']['peg_half_size'],3)
    aperture=float(vec(baseline['states'][0]['observation']['extra']['box_hole_radius'],1)[0])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelcolor':'#26323d',
                         'xtick.color':'#52606d','ytick.color':'#52606d','axes.edgecolor':'#b6c0c9'})
    fig=plt.figure(figsize=(12.8,8),dpi=100,facecolor='#ffffff')
    fig.text(.05,.965,'AETHER-CL M7 | recorded insertion replay',fontsize=20,weight='bold',color='#26323d')
    fig.text(.05,.925,f'Seed {args.seed} | {args.ratio*3:g} mm offset | {args.stride}x playback | peg / target / TCP; arm omitted',fontsize=12,color='#52606d')
    clock=fig.text(.95,.925,'',ha='right',fontsize=12,color='#26323d')
    axes=[fig.add_axes([.035,.32,.445,.53],projection='3d'),fig.add_axes([.52,.32,.445,.53],projection='3d')]
    palette=['#46525e','#226da6'];names=['Baseline: fixed insertion','V2: verification + one recovery']
    moving=[];labels=[];statuses=[]
    for ax,recording,color,name in zip(axes,recordings,palette,names):
        ax.set_proj_type('ortho');ax.view_init(elev=24,azim=-122)
        ax.set_xlim(-.64,.16);ax.set_ylim(-.28,.28);ax.set_zlim(-.13,.32)
        ax.set_box_aspect([.8,.56,.45]);ax.set_axis_off()
        ax.set_title(name,fontsize=15,color=color,pad=10,weight='bold')
        e=recording['states'][0]['observation']['extra'];hole=vec(e['box_hole_pose'],7);box=vec(e['box_pose'],7)
        center=into_hole(np.zeros((1,3)),hole,box)[0]
        # In box coordinates, the two visible walls retain the recorded channel
        # boundaries. Two near walls are removed solely for a legible cutaway.
        cx,cy,cz=center
        walls=[cuboid([-half[0],cy+aperture,-half[0]],[half[0],half[0],half[0]]),
               cuboid([-half[0],-half[0],-half[0]],[half[0],half[0],cz-aperture])]
        for wall in walls:
            vertices=into_hole(wall,box,hole)
            ax.add_collection3d(Poly3DCollection(vertices[FACES],facecolors='#c8b592',edgecolors='#ab9d86',linewidths=.55,alpha=.35))
        rim=np.array([[-half[0],-aperture,-aperture],[-half[0],-aperture,aperture],
                      [-half[0],aperture,aperture],[-half[0],aperture,-aperture],[-half[0],-aperture,-aperture]])
        ax.plot(*rim.T,color='#4b657b',lw=1.5)
        ax.plot([-.4,0],[0,0],[0,0],color='#a6b7c5',linestyle='--',lw=.8)
        ax.text(.025,.11,.14,'Target\ncutaway',fontsize=10,color='#66717c')
        front=Poly3DCollection([],facecolors='#ec7357',edgecolors='#9a4837',linewidths=.7)
        rear=Poly3DCollection([],facecolors='#edf6f9',edgecolors='#8798a6',linewidths=.7)
        ax.add_collection3d(front);ax.add_collection3d(rear)
        tcp,=ax.plot([],[],[],marker='o',ms=5,mfc='white',mec=color,linestyle='none',label='Recorded TCP')
        moving.append((front,rear,tcp))
        x=.05 if ax is axes[0] else .535
        labels.append(fig.text(x,.305,'',fontsize=12,color=color))
        statuses.append(fig.text(x,.265,'',fontsize=12,color='#26323d'))
    plot=fig.add_axes([.075,.115,.86,.105])
    times=np.arange(1201)/CONTROL_HZ
    for recording,color in zip(recordings,palette):
        depths=[np.nan]+[e['reference']['depth_m']*1000 for e in recording['states'][1:]]
        plot.plot(times,depths,color=color,lw=1.4)
    plot.axhspan(.8*half[0]*1000,1.2*half[0]*1000,color='#226da6',alpha=.07)
    plot.axvline(643/CONTROL_HZ,color='#8b99a6',lw=.8,linestyle='--')
    plot.text(643/CONTROL_HZ+.6,125,'Recovery starts',fontsize=9,color='#66717c')
    plot.set_xlim(0,60);plot.set_ylim(-100,145);plot.set_yticks([-50,0,100]);plot.set_ylabel('Depth (mm)',fontsize=10)
    plot.set_xlabel('Original simulation time (s)',fontsize=10,labelpad=3)
    plot.spines[['top','right']].set_visible(False);plot.grid(axis='y',color='#e9edf0',lw=.6)
    cursor=plot.axvline(0,color='#26323d',lw=1.2)
    fig.text(.05,.035,'Recorded native states | a51e5d2 | geometry reconstruction, not original camera footage | no new simulation or training',fontsize=10,color='#52606d')
    indices=list(range(0,1201,args.stride))
    if indices[-1]!=1200:indices.append(1200)
    indices += [1200]*40
    metadata={'title':f'AETHER-CL M7 recorded geometry replay: seed{args.seed} {args.ratio*3:g}mm paired rescue',
        'comment':'Recorded peg, target and TCP poses; arm omitted; target cutaway. Not camera video or a rerun. Native commit '+MEASUREMENT,
        'artist':'AURA-Embodied'}
    writer=FFMpegWriter(fps=CONTROL_HZ,codec='libx264',bitrate=2400,metadata=metadata,
                       extra_args=['-crf','20','-pix_fmt','yuv420p','-movflags','+faststart'])
    with writer.saving(fig,str(output),dpi=100):
        for number,index in enumerate(indices):
            for recording,actors,label,status in zip(recordings,moving,labels,statuses):
                state=recording['states'][index];extra=state['observation']['extra'];hole=extra['box_hole_pose']
                hp=vec(extra['peg_half_size'],3)
                head=into_hole(cuboid([0,-hp[1],-hp[2]],hp),extra['peg_pose'],hole)
                tail=into_hole(cuboid(-hp,[0,hp[1],hp[2]]),extra['peg_pose'],hole)
                actors[0].set_verts(head[FACES]);actors[1].set_verts(tail[FACES])
                tcp=into_hole(np.zeros((1,3)),extra['tcp_pose'],hole)[0]
                actors[2].set_data_3d([tcp[0]],[tcp[1]],[tcp[2]])
                phase=state['controller_decision']['phase'].replace('_',' ')
                label.set_text('Stage: '+phase)
                ref=state['reference']
                if ref:
                    verdict='TASK PASS' if ref['task_success'] else 'Task not yet satisfied'
                    if index==1200 and not ref['task_success']:verdict='FINAL TASK FAIL'
                    status.set_text(f"{verdict} | depth {ref['depth_m']*1000:.2f} mm | lateral {ref['lateral_error_m']*1000:.2f} mm")
                else:status.set_text('Initial recorded state')
            clock.set_text(f't = {index/CONTROL_HZ:04.1f} s')
            cursor.set_xdata([index/CONTROL_HZ]*2)
            writer.grab_frame()
            if index in (0,490,644,800,1200) and (number==0 or indices[number-1]!=index):
                fig.savefig(output.parent/f'preview-{index:04d}.png',dpi=100)
            if number%100==0:print(f'FRAME {number+1}/{len(indices)} original_action={index}',flush=True)
    plt.close(fig)
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,nb_frames,r_frame_rate:format=duration','-of','json',str(output)],check=True,capture_output=True,text=True)
    receipt={'purpose':'visualization_only_not_new_native_outcomes','native_measurement_commit':MEASUREMENT,
        'seed':args.seed,'ratio':args.ratio,'nominal_offset_mm':args.ratio*3,
        'selected_example':'audited_paired_rescue_not_an_aggregate_or_random_sample',
        'all_original_states':1201,'shown_original_indices':list(dict.fromkeys(indices)),
        'stride':args.stride,'control_hz':CONTROL_HZ,'video_fps':CONTROL_HZ,'playback_speed':args.stride,
        'target_cutaway':True,'robot_arm_omitted':True,'original_camera_footage':False,
        'sources':[{k:v for k,v in r.items() if k in ('hashes','trial')} for r in recordings],
        'native_outcomes':{'baseline':False,'v2':True},'geometry_video_tool_sha256':sha(__file__),
        'video_sha256':sha(output),'video_bytes':output.stat().st_size,'ffprobe':json.loads(probe.stdout)}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print('M7_RECORDED_GEOMETRY_VIDEO_READY',output,flush=True)

if __name__=='__main__':main()
