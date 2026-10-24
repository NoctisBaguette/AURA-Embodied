"""Synthetic CPU boundary tests. They do not load a neural model or run RoboTwin."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import portable_manifest as pm


def tensors(path, shapes):
    header={}; chunks=[]; pos=0
    for name,shape in shapes.items():
        n=1
        for dim in shape: n*=dim
        data=b'\0'*(n*4)
        header[name]={'dtype':'F32','shape':shape,'data_offsets':[pos,pos+len(data)]}
        chunks.append(data); pos+=len(data)
    encoded=json.dumps(header,separators=(',',':')).encode(); encoded+=b' '*((-len(encoded))%8)
    Path(path).write_bytes(struct.pack('<Q',len(encoded))+encoded+b''.join(chunks))


def make_checkpoint(path,joint=False):
    path.mkdir()
    targets=[f'model.qwenvl_with_expert.qwen_expert.model.layers.{i}.self_attn.{p}_proj' for i in range(36) for p in 'qkvo']
    shapes={}
    for n in targets:
        out_dim,in_dim={'q_proj':(4096,768),'k_proj':(1024,768),'v_proj':(1024,768),'o_proj':(768,4096)}[n.rsplit('.',1)[1]]
        shapes[n+'.lora_A.weight']=[8,in_dim];shapes[n+'.lora_B.weight']=[out_dim,8]
    tensors(path/'adapter_model.safetensors',shapes)
    pm.write_json(path/'adapter_config.json',dict(peft_type='LORA',r=8,lora_alpha=16,lora_dropout=0,bias='none',target_modules=targets))
    (path/'resume-state.pt').write_bytes(b'CPU fixture only, never torch.load this')
    pm.write_json(path/'norm-stats-clean50.json',{'fixture':True})
    identity={'batch_size':2 if joint else 4,'normalization_sha256':pm.sha(path/'norm-stats-clean50.json')}
    if joint:
        identity['initializer']='fixture-original'
        tensors(path/'projection_weights.safetensors',{f'model.{n}.{part}':list(shape if part=='weight' else (shape[0],)) for n,shape in pm.PROJECTIONS.items() for part in ('weight','bias')})
    names=pm.PAYLOAD|({'projection_weights.safetensors'} if joint else set())
    pm.write_json(path/'checkpoint.json',dict(identity=identity,completed_updates=10000,samples_consumed=10000*identity['batch_size'],files={n:pm.sha(path/n) for n in names}))


def refresh(path,name):
    meta=pm.read_json(path/'checkpoint.json');meta['files'][name]=pm.sha(path/name);pm.write_json(path/'checkpoint.json',meta)


class Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name)
        make_checkpoint(cls.root/'old');make_checkpoint(cls.root/'joint',True)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def setUp(self):
        self.work=Path(tempfile.mkdtemp(dir=self.root));self.ckpt=self.work/'checkpoint';shutil.copytree(self.root/'joint',self.ckpt)
    def tearDown(self): shutil.rmtree(self.work)
    def error(self, message, fn):
        with self.assertRaisesRegex((ValueError,OSError),message): fn()
    def test_old_contract(self):
        r=pm.checkpoint_info(self.root/'old');self.assertEqual((r['generation'],r['samples_consumed']),('clean50-fallback',40000))
    def test_joint_contract(self): self.assertEqual(pm.checkpoint_info(self.ckpt)['samples_consumed'],20000)
    def test_empty_payload(self):
        m=pm.read_json(self.ckpt/'checkpoint.json');m['files']={};pm.write_json(self.ckpt/'checkpoint.json',m);self.error('Incomplete checkpoint',lambda:pm.checkpoint_info(self.ckpt))
    def test_empty_identity(self):
        m=pm.read_json(self.ckpt/'checkpoint.json');m['identity']={};pm.write_json(self.ckpt/'checkpoint.json',m);self.error('Missing checkpoint identity',lambda:pm.checkpoint_info(self.ckpt))
    def test_wrong_batch(self):
        m=pm.read_json(self.ckpt/'checkpoint.json');m['identity']['batch_size']=4;pm.write_json(self.ckpt/'checkpoint.json',m);self.error('generation/batch',lambda:pm.checkpoint_info(self.ckpt))
    def test_wrong_cursor(self):
        m=pm.read_json(self.ckpt/'checkpoint.json');m['samples_consumed']=40000;pm.write_json(self.ckpt/'checkpoint.json',m);self.error('sample cursor',lambda:pm.checkpoint_info(self.ckpt))
    def test_wrong_norm(self):
        m=pm.read_json(self.ckpt/'checkpoint.json');m['identity']['normalization_sha256']='0'*64;pm.write_json(self.ckpt/'checkpoint.json',m);self.error('Normalization identity',lambda:pm.checkpoint_info(self.ckpt))
    def test_extra_file(self):
        (self.ckpt/'extra').touch();self.error('Unexpected/missing',lambda:pm.checkpoint_info(self.ckpt))
    def test_partial(self):
        p=self.work/'x.partial';self.ckpt.rename(p);self.error('Incomplete checkpoint directory',lambda:pm.checkpoint_info(p))
    def test_hash(self):
        with (self.ckpt/'resume-state.pt').open('ab') as f:f.write(b'x')
        self.error('hash mismatch',lambda:pm.checkpoint_info(self.ckpt))
    def test_same_shape_wrong_projection_name(self):
        shapes={f'model.{n}.{part}':list(shape if part=='weight' else (shape[0],)) for n,shape in pm.PROJECTIONS.items() for part in ('weight','bias')}
        shapes['wrong.weight']=shapes.pop('model.state_proj.weight');tensors(self.ckpt/'projection_weights.safetensors',shapes);refresh(self.ckpt,'projection_weights.safetensors');self.error('Projection names',lambda:pm.checkpoint_info(self.ckpt))
    def test_tiny_adapter(self):
        tensors(self.ckpt/'adapter_model.safetensors',{'anything':[1]});refresh(self.ckpt,'adapter_model.safetensors');self.error('adapter tensors',lambda:pm.checkpoint_info(self.ckpt))
    def test_invalid_tensor_payload(self):
        p=self.work/'invalid'; h=json.dumps({'x':{'dtype':'F32','shape':[1000],'data_offsets':[0,1]}}).encode();p.write_bytes(struct.pack('<Q',len(h))+h+b'0');self.error('byte size',lambda:pm.tensor_headers(p))
    def test_tensor_gap(self):
        p=self.work/'invalid'; h=json.dumps({'x':{'dtype':'F32','shape':[1],'data_offsets':[1,5]}}).encode();p.write_bytes(struct.pack('<Q',len(h))+h+b'00000');self.error('gap/overlap',lambda:pm.tensor_headers(p))
    def test_nan(self):
        p=self.work/'nan';tensors(p,{'x':[1]});b=p.read_bytes();p.write_bytes(b[:-4]+struct.pack('<f',float('nan')));self.error('Nonfinite',lambda:pm.tensor_headers(p,True))
    def test_duplicate_json(self):
        p=self.work/'d.json';p.write_text('{"x":1,"x":2}');self.error('Duplicate',lambda:pm.read_json(p))
    def test_empty_package(self):
        pm.write_json(self.work/'package-manifest.json',{'format':pm.FORMAT,'files':{}});self.error('empty package',lambda:pm.verify_package(self.work))
    def test_traversal(self):
        for path in ('../x','/x','a/../b','a\\b','C:/x','a//b'):
            self.error('path|relative|drive',lambda:pm.relative(path))
    def test_asset_collision(self):
        assets=self.work/'assets';assets.mkdir();(assets/'checkpoint').mkdir();self.error('exactly base',lambda:pm.export_package(self.ckpt,assets,self.work/'out'));self.assertFalse((self.work/'out').exists())
    def test_failed_export_cleanup(self):
        assets=self.work/'assets';assets.mkdir()
        for g in ('base','qwen','source','runtime'):(assets/g).mkdir()
        (assets/'runtime/profile.json').write_text('{}')
        self.error('Wrong runtime profile',lambda:pm.export_package(self.ckpt,assets,self.work/'out'))
        self.assertFalse((self.work/'out').exists());self.assertEqual(list(self.work.glob('out.partial-*')),[])
    def test_atomic_no_replace(self):
        stage=self.work/'stage';stage.mkdir();(stage/'evidence').write_text('original');out=self.work/'out';out.mkdir()
        with self.assertRaises(OSError):pm.publish(stage,out)
        self.assertEqual((stage/'evidence').read_text(),'original');self.assertEqual(list(out.iterdir()),[])
    def test_atomic_publish(self):
        stage=self.work/'stage';stage.mkdir();(stage/'evidence').write_text('original');out=self.work/'out';pm.publish(stage,out);self.assertFalse(stage.exists());self.assertEqual((out/'evidence').read_text(),'original')
    def test_reserved_plan_destination(self):
        plan=self.work/'plan.json';pm.write_json(plan,{'format':pm.FORMAT,'files':{'checkpoint/adapter_config.json':{'source':'/does-not-matter'}}});self.error('Reserved/unknown',lambda:pm.export_from_plan(self.ckpt,plan,self.work/'out'))
    def test_import_does_not_load_torch(self):
        import load_policy
        self.assertNotIn('torch',sys.modules)
    def test_complete_cpu_package_roundtrip_and_tamper(self):
        assets=self.work/'assets'
        for g in ('base','qwen','runtime','source/lingbotvla/models/vla/lingbot_vla'):(assets/g).mkdir(parents=True,exist_ok=True)
        (assets/'source/lingbotvla/__init__.py').write_text('')
        source=assets/'source/lingbotvla/models/vla/lingbot_vla'
        for n in ('modeling_lingbot_vla_v2.py','qwen2_action_expert.py'):(source/n).write_text('# synthetic CPU fixture only')
        for g in ('base','qwen'):pm.write_json(assets/g/'source-manifest.json',{'fixture':g})
        for n in ('config.json','preprocessor_config.json','tokenizer_config.json','tokenizer.json'):pm.write_json(assets/'qwen'/n,{'fixture':True})
        for i in range(6):tensors(assets/'base'/f'model-{i:05d}.safetensors',{f'fixture{i}':[1]})
        runtime=assets/'runtime'
        for n in ('inference_cache_recovery.py','model_builder.py','lingbot_zero_padding.py','robotwin.yaml'):(runtime/n).write_text('# synthetic CPU fixture only')
        versions={k:'fixture' for k in ('torch','transformers','peft','safetensors','torchvision','accelerate','tokenizers','Pillow','PyYAML')}
        ident={'batch_size':4,'model_settings':{'fixture':True},'data_settings':{'fixture':True},'package_versions':{'torch':'fixture'},'normalization_sha256':pm.sha(self.ckpt/'norm-stats-clean50.json'),'policy_sha256':pm.sha(source/'modeling_lingbot_vla_v2.py'),'moe_sha256':pm.sha(source/'qwen2_action_expert.py'),**{g+'_manifest_sha256':pm.sha(assets/g/'source-manifest.json') for g in ('base','qwen')}}
        pm.write_json(runtime/'initializer-identity.json',ident);pm.write_json(runtime/'runtime-versions.json',versions);pm.write_json(runtime/'profile.json',{'format':pm.FORMAT,'precision':'FP32','num_steps':10})
        # Fixture-only constants, clearly separate from the production helper SHA requirements.
        with patch.object(pm,'CACHE_SHA',pm.sha(runtime/'inference_cache_recovery.py')),patch.object(pm,'BUILDER_SHA',pm.sha(runtime/'model_builder.py')),patch.object(pm,'PADDING_SHA',pm.sha(runtime/'lingbot_zero_padding.py')):
            out=self.work/'out';r=pm.export_package(self.ckpt,assets,out)
            self.assertEqual(r['manifest_sha256'],pm.verify_package(out)['manifest_sha256'])
            (out/'qwen/tokenizer.json').unlink()
            self.error('coverage mismatch',lambda:pm.verify_package(out))
            # Even editing the manifest to omit the file does not bypass mandatory closure.
            manifest=pm.read_json(out/'package-manifest.json');del manifest['files']['qwen/tokenizer.json'];pm.write_json(out/'package-manifest.json',manifest)
            self.error('Missing runtime/base/tokenizer',lambda:pm.verify_package(out))
    def test_admission_stability_and_deadline(self):
        from gpu_admission import wait_gpu
        import os
        now=[0]; values=iter([[("GPU-fixture",61440,0)],[("GPU-fixture",60000,0)],[("GPU-fixture",70000,0)],[("GPU-fixture",70000,0)],[("GPU-fixture",70000,0)],[("GPU-fixture",70000,0)]])
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'GPU-fixture'}):
            wait_gpu('GPU-fixture',timeout=30,query=lambda:next(values),sleep=lambda n:now.__setitem__(0,now[0]+n),clock=lambda:now[0])
            self.assertEqual(now[0],20)
            with self.assertRaisesRegex(TimeoutError,'no model load'):
                wait_gpu('GPU-fixture',timeout=15,query=lambda:[('GPU-fixture',100,99)],sleep=lambda n:now.__setitem__(0,now[0]+n),clock=lambda:now[0])
    def test_original_real_metadata_generation(self):
        # Independent producer receipt: older fallback really is batch4/40000 and four payloads.
        path=Path(__file__).parent/'fallback-schema.json'
        m=pm.read_json(path);self.assertEqual(m['batch_size'],4);self.assertEqual(m['samples_consumed'],m['completed_updates']*4);self.assertEqual(set(m['payload_files']),pm.PAYLOAD)

if __name__=='__main__': unittest.main(verbosity=2)
