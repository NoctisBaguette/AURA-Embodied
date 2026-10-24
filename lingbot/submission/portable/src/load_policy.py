"""Fresh-process FP32 load and captured-input parity. Import/CPU verification never starts CUDA."""
import argparse
import copy
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from portable_manifest import checkpoint_info, read_json, require, sha, verify_package, PROJECTIONS


def module_from_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def restore_state(model, checkpoint):
    import torch
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from safetensors.torch import load_file
    info=checkpoint_info(checkpoint)
    metadata=info['metadata']
    saved=torch.load(checkpoint/'resume-state.pt',map_location='cpu',weights_only=True)
    require(saved['identity']==metadata['identity'] and saved['completed_updates']==info['completed_updates'] and saved['samples_consumed']==info['samples_consumed'], 'Resume state/metadata mismatch')
    require(type(saved['model_steps']) is int and saved['model_steps']>=0, 'Invalid model counter')
    adapter=load_file(str(checkpoint/'adapter_model.safetensors'))
    current=get_peft_model_state_dict(model)
    require(set(current)==set(adapter), 'Live adapter key mismatch')
    for name,value in adapter.items():
        require(value.shape==current[name].shape and value.dtype==current[name].dtype and torch.isfinite(value).all().item(), 'Live adapter layout mismatch: '+name)
    parameters=dict(model.named_parameters())
    persistent={n:v for n,v in model.named_buffers() if n in model.state_dict()}
    buffers=saved['persistent_buffers']
    require(set(buffers)==set(persistent), 'Missing/unexpected persistent buffers')
    projections=load_file(str(checkpoint/'projection_weights.safetensors')) if info['generation']=='joint50' else {}
    # Validate every tensor before mutating this freshly constructed model.
    for values,live in ((projections,parameters),(buffers,persistent)):
        for name,value in values.items():
            require(torch.is_tensor(value) and name in live and value.shape==live[name].shape and value.dtype==live[name].dtype and torch.isfinite(value).all().item(), 'State layout/content mismatch: '+name)
    outcome=set_peft_model_state_dict(model,adapter)
    require(not outcome.unexpected_keys, 'Unexpected adapter load keys')
    actual=get_peft_model_state_dict(model)
    require(all(torch.equal(actual[n].detach().cpu(),v) for n,v in adapter.items()), 'Adapter reload differs')
    with torch.no_grad():
        for values,live in ((projections,parameters),(buffers,persistent)):
            for name,value in values.items():
                live[name].copy_(value.to(live[name].device))
                require(torch.equal(live[name].detach().cpu(),value), 'State reload differs: '+name)
    model.model.steps=saved['model_steps']
    model.requires_grad_(False); model.eval()
    return info


class PortablePolicy:
    def __init__(self, package, *, admitted_gpu_uuid, admission_timeout=600, admission_deadline_epoch=None, admission_progress=None, cancelled=None):
        self.root=Path(package).resolve()
        self.receipt=verify_package(self.root)
        require(isinstance(admitted_gpu_uuid,str) and admitted_gpu_uuid.startswith('GPU-') and os.environ.get('CUDA_VISIBLE_DEVICES')==admitted_gpu_uuid, 'Use exactly the captain-admitted UUID in CUDA_VISIBLE_DEVICES')
        identity=read_json(self.root/'runtime/initializer-identity.json')
        for name, version in identity['package_versions'].items():
            require(importlib.metadata.version(name)==version, 'Runtime package version differs: '+name)
        versions=read_json(self.root/'runtime/runtime-versions.json')
        for name,version in versions.items():
            require(importlib.metadata.version(name)==version,'Export/load dependency differs: '+name)
        from gpu_admission import wait_gpu
        wait_gpu(admitted_gpu_uuid,timeout=admission_timeout,deadline_epoch=admission_deadline_epoch,progress=admission_progress,cancelled=cancelled)
        if admission_progress: admission_progress(dict(status='MODEL_LOADING',model_load_started=True))
        sys.dont_write_bytecode=True
        sys.path.insert(0,str(self.root/'source'))
        # No already-imported unrelated checkout can silently supply the model implementation.
        require(not any(n=='lingbotvla' or n.startswith('lingbotvla.') for n in sys.modules), 'Load in a fresh process before importing lingbotvla')
        os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
        import numpy as np
        import torch
        from transformers import AutoProcessor
        from torchvision.transforms.v2 import Resize
        from lingbotvla.data.vla_data.utils import FeatureTransform
        import random
        random.seed(42); np.random.seed(42); torch.manual_seed(42)
        require(torch.cuda.is_available() and torch.cuda.device_count()==1, 'One admitted CUDA device required')
        torch.set_float32_matmul_precision('highest')
        builder=module_from_file('portable_builder',self.root/'runtime/model_builder.py')
        self.model,self.config,_=builder.build_inference_policy(copy.deepcopy(identity['model_settings']),self.root)
        self.info=restore_state(self.model,self.root/'checkpoint')
        for cfg in (self.config,self.model.model.config):
            cfg.use_cache=False; cfg.align_params={}; cfg.num_steps=10
        self.cache=module_from_file('portable_cache',self.root/'runtime/inference_cache_recovery.py')
        self.padding=module_from_file('portable_padding',self.root/'runtime/lingbot_zero_padding.py')
        self.processor=AutoProcessor.from_pretrained(str(self.root/'qwen'),padding_side='right',local_files_only=True)
        self.transform=FeatureTransform(str(self.root/'runtime/robotwin.yaml'),SimpleNamespace(**copy.deepcopy(identity['data_settings'])),self.config,self.processor,chunk_size=50,norm_stats_path=str(self.root/'checkpoint/norm-stats-clean50.json'),image_augment=False,use_future_image=False)
        require(not any(self.transform.action_subtract_state.values()),'Expected absolute joint targets')
        self.resize=Resize((256,256))
        self.camera_keys=('observation.images.cam_high','observation.images.cam_left_wrist','observation.images.cam_right_wrist')
        self.device=torch.device('cuda',0)
        self.versions={n:p._version for n,p in self.model.named_parameters()}
        self.buffers={n:v.detach().cpu().clone() for n,v in self.model.named_buffers() if n in self.model.state_dict()}
        self.step=self.model.model.steps
        self.cache.clear_visual_cache(self.model)

    def predict(self, packet, *, noise):
        import numpy as np
        import torch
        with np.load(io.BytesIO(packet),allow_pickle=False) as item:
            instruction=str(item['task'].item())
            require(instruction.strip() and len(instruction)<4096,'Invalid instruction')
            state=np.asarray(item['observation.state'],dtype=np.float32).copy()
            require(state.shape==(14,) and np.isfinite(state).all(),'Invalid state')
            raw={'task':instruction,'observation.state':torch.from_numpy(state)}
            for key in self.camera_keys:
                rgb=np.asarray(item[key]).copy()
                require(rgb.shape==(240,320,3) and rgb.dtype==np.uint8,'Invalid RGB input: '+key)
                raw[key]=self.resize(torch.from_numpy(rgb).permute(2,0,1).contiguous().float())
        applied=self.transform.apply(raw,policy_eval=True)
        require(tuple(applied['images'].shape)==(3,256,1536) and tuple(applied['image_grid_thw'].shape)==(3,3),'Processed image shape differs')
        active=torch.zeros(55,dtype=torch.bool); active[list(range(12))+[28,29]]=True
        require(torch.equal(applied['state_joint_mask'].cpu(),active) and torch.equal(applied['action_joint_mask'].cpu(),active),'Joint mask differs')
        require(applied['img_masks'].tolist()==[True,True,True],'Missing camera')
        observation={k:applied[k].unsqueeze(0).to(self.device) for k in ('images','img_masks','lang_tokens','lang_masks','state','image_grid_thw')}
        observation['images']=observation['images'].float(); observation['state']=observation['state'].float(); observation['image_grid_thw']=observation['image_grid_thw'].long()
        require(noise.shape==(1,50,55) and noise.dtype==np.float32 and np.isfinite(noise).all(),'Invalid captured noise')
        self.cache.clear_visual_cache(self.model)
        try:
            with torch.inference_mode(),self.cache.inference_cache_scope(self.model,self.config):
                predicted=self.padding.sample_actions(self.model.model,observation,action_joint_mask=applied['action_joint_mask'],noise=torch.from_numpy(noise.copy()).to(self.device))
            decoded=self.transform.unapply({**copy.deepcopy(applied),'actions':predicted[0].detach().cpu().clone()})
            commands=decoded['action'].numpy().copy()
            require(commands.shape==(50,14) and np.isfinite(commands).all(),'Invalid decoded actions')
            require(all(p._version==self.versions[n] for n,p in self.model.named_parameters()) and self.model.model.steps==self.step,'Inference changed model parameters/counter')
            live=dict(self.model.named_buffers())
            require(all(torch.equal(live[n].detach().cpu(),v) for n,v in self.buffers.items()),'Inference changed persistent buffers')
            return {'normalized':predicted.detach().cpu().numpy(),'commands':commands,
                    'images':applied['images'].cpu().numpy(),'lang_tokens':applied['lang_tokens'].cpu().numpy(),'lang_masks':applied['lang_masks'].cpu().numpy()}
        finally:
            self.cache.clear_visual_cache(self.model)


def parity(policy, packet, reference, *, checkpoint_metadata_sha256):
    import numpy as np
    require(sha(policy.root/'checkpoint/checkpoint.json')==checkpoint_metadata_sha256,'Reference checkpoint binding differs')
    with np.load(reference,allow_pickle=False) as ref:
        required={'normalized','commands','noise','lang_tokens','lang_masks'}
        require(required<=set(ref.files),'Reference missing arrays')
        frozen={k:ref[k].copy() for k in ref.files}
    first=policy.predict(Path(packet).read_bytes(),noise=frozen['noise'])
    second=policy.predict(Path(packet).read_bytes(),noise=frozen['noise'])
    metrics={}
    for k in ('normalized','commands','lang_tokens','lang_masks'):
        expected=frozen[k]; actual=first[k]
        require(actual.shape==expected.shape and actual.dtype==expected.dtype,'Reference layout differs: '+k)
        require(np.array_equal(actual,second[k]),'Same-input repeat differs: '+k)
        require(np.array_equal(actual,expected),'Fresh-process reference differs: '+k)
        metrics[k]={'exact':True,'shape':list(actual.shape),'dtype':str(actual.dtype)}
    if 'images' in frozen:
        require(np.array_equal(first['images'],frozen['images']),'Processed images differ')
    return {'status':'PASS','scope':'Fresh-process captured-input output parity; no simulator task success claimed',
            'manifest_sha256':policy.receipt['manifest_sha256'],'checkpoint_metadata_sha256':checkpoint_metadata_sha256,
            'packet_sha256':sha(packet),'reference_sha256':sha(reference),'arrays':metrics,'processed_images_checked':'images' in frozen}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--package',required=True); p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--verify-manifest',action='store_true',required=True)
    p.add_argument('--admission-timeout',type=int,default=600)
    p.add_argument('--admitted-gpu-uuid'); p.add_argument('--input'); p.add_argument('--reference')
    p.add_argument('--reference-checkpoint-sha256'); p.add_argument('--report')
    a=p.parse_args()
    if a.device=='cpu': print(json.dumps(verify_package(a.package),indent=2)); return
    require(all((a.admitted_gpu_uuid,a.input,a.reference,a.reference_checkpoint_sha256,a.report)),'CUDA parity requires admitted UUID, input, reference, bound checkpoint SHA and report')
    report=Path(a.report).resolve(); root=Path(a.package).resolve()
    require(report!=root and root not in report.parents,'Report must be outside package')
    require(not report.exists() and report.parent.is_dir(),'Report exists or its parent is missing')
    try:
        require(Path(a.input).is_file() and Path(a.reference).is_file(),'Missing captured input/reference')
        require(sha(root/'checkpoint/checkpoint.json')==a.reference_checkpoint_sha256,'Reference checkpoint binding differs')
        policy=PortablePolicy(a.package,admitted_gpu_uuid=a.admitted_gpu_uuid,admission_timeout=a.admission_timeout)
        result=parity(policy,a.input,a.reference,checkpoint_metadata_sha256=a.reference_checkpoint_sha256)
    except Exception as error:
        with report.open('x',encoding='utf-8') as f:
            json.dump({'status':'FAIL','scope':'Portable load/parity attempt; no task-success claim','error_type':type(error).__name__,'error':str(error)},f,indent=2,allow_nan=False)
            f.write('\n')
        raise
    with report.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
