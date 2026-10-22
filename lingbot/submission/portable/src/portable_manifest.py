"""Content-bound export for the retained clean50 and joint50 producers. CPU only."""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import tempfile

FORMAT = 'lingbot-portable-v2'
PAYLOAD = {'adapter_model.safetensors', 'adapter_config.json', 'resume-state.pt', 'norm-stats-clean50.json'}
PROJECTIONS = {'state_proj': (768,55), 'action_in_proj': (768,55),
               'action_out_proj': (55,768), 'action_time_mlp_in': (768,1536),
               'action_time_mlp_out': (768,768)}
TARGET = r'model\.qwenvl_with_expert\.qwen_expert\.model\.layers\.(\d+)\.self_attn\.([qkvo])_proj'
BUILDER_SHA = '0673bb7f0ebd8e103dd24994ea951bb319c4ff95b996367f5dd8ee0aa56e6f9f'
PADDING_SHA = 'c19331adff45535fc58a4b1dd8c1862cb91234aaaf8d59a0e627ba5c42d94c4d'
CACHE_SHA = '7b2eb0a73ca07b62190a195fc6c9a5f81f56a28ee18efaa41ae016cdc9200bc5'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'Duplicate JSON key: '+key)
        out[key] = value
    return out


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+s)))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def relative(name):
    require(isinstance(name, str) and bool(name) and '\\' not in name, 'Invalid relative path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix() == name and all(v not in ('.','..') for v in p.parts), 'Unsafe relative path: '+name)
    require(':' not in name, 'Unsafe drive/path: '+name)
    return p


def files_under(root):
    root = Path(root)
    found = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'Package symlink: '+str(p))
        if p.is_file():
            found[p.relative_to(root).as_posix()] = p
    return found


def tensor_headers(path, finite_f32=False):
    """Validate full safetensors layout; no Torch import or GPU initialization."""
    size = Path(path).stat().st_size
    with Path(path).open('rb') as f:
        raw = f.read(8)
        require(len(raw) == 8, 'Truncated safetensors prefix')
        length = struct.unpack('<Q', raw)[0]
        require(2 <= length <= min(100_000_000, size-8), 'Invalid safetensors header length')
        entries = json.loads(f.read(length), object_pairs_hook=_pairs)
        require(isinstance(entries, dict), 'Invalid safetensors header')
        entries.pop('__metadata__', None)
        require(bool(entries), 'Empty tensor dictionary')
        widths = {'F64':8,'F32':4,'F16':2,'BF16':2,'I64':8,'I32':4,'I16':2,'I8':1,'U8':1,'BOOL':1}
        intervals = []
        for name, info in entries.items():
            require(isinstance(info, dict) and set(info)=={'dtype','shape','data_offsets'}, 'Invalid tensor entry: '+name)
            dtype, shape, offset = info['dtype'], info['shape'], info['data_offsets']
            require(dtype in widths and isinstance(shape,list) and all(type(n) is int and n>=0 for n in shape), 'Invalid tensor shape/dtype: '+name)
            require(isinstance(offset,list) and len(offset)==2 and all(type(n) is int and n>=0 for n in offset), 'Invalid tensor offsets: '+name)
            require(offset[1]-offset[0] == math.prod(shape)*widths[dtype], 'Tensor byte size mismatch: '+name)
            intervals.append((offset[0],offset[1],name))
        cursor = 0
        for start,end,name in sorted(intervals):
            require(start == cursor and end>=start, 'Tensor gap/overlap: '+name)
            cursor = end
        require(8+length+cursor == size, 'Safetensors payload length mismatch')
        if finite_f32:
            require(all(e['dtype']=='F32' for e in entries.values()), 'Expected FP32 checkpoint tensors')
            while True:
                block=f.read(1024*1024)
                if not block: break
                require(all(math.isfinite(x[0]) for x in struct.iter_unpack('<f',block)), 'Nonfinite checkpoint tensor')
    return entries


def checkpoint_info(folder):
    folder=Path(folder)
    require(folder.is_dir() and not folder.name.endswith('.partial'), 'Incomplete checkpoint directory')
    metadata=read_json(folder/'checkpoint.json')
    identity=metadata.get('identity')
    require(isinstance(identity,dict) and bool(identity), 'Missing checkpoint identity')
    batch=identity.get('batch_size')
    joint='initializer' in identity
    require(type(batch) is int and batch == (2 if joint else 4), 'Checkpoint generation/batch mismatch')
    expected=PAYLOAD | ({'projection_weights.safetensors'} if joint else set())
    require(set(metadata.get('files',{})) == expected, 'Incomplete checkpoint payload manifest')
    actual=files_under(folder)
    require(set(actual)==expected|{'checkpoint.json'}, 'Unexpected/missing checkpoint file')
    for name, digest in metadata['files'].items():
        require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest), 'Invalid checkpoint hash')
        require(sha(folder/name)==digest, 'Checkpoint hash mismatch: '+name)
    update=metadata.get('completed_updates'); samples=metadata.get('samples_consumed')
    require(type(update) is int and update>=0 and type(samples) is int and samples==update*batch, 'Checkpoint sample cursor mismatch')
    require(identity.get('normalization_sha256')==sha(folder/'norm-stats-clean50.json'), 'Normalization identity mismatch')
    cfg=read_json(folder/'adapter_config.json')
    require(cfg.get('peft_type')=='LORA' and cfg.get('r')==8 and cfg.get('lora_alpha')==16 and cfg.get('bias')=='none' and cfg.get('lora_dropout')==0, 'Unsupported adapter configuration')
    require(not cfg.get('use_dora',False) and not cfg.get('use_rslora',False) and not cfg.get('modules_to_save') and not cfg.get('rank_pattern') and not cfg.get('alpha_pattern'), 'Unsupported adapter variant')
    targets=cfg.get('target_modules')
    wanted={f'model.qwenvl_with_expert.qwen_expert.model.layers.{i}.self_attn.{p}_proj' for i in range(36) for p in 'qkvo'}
    require(isinstance(targets,list) and len(targets)==144 and set(targets)==wanted, 'Wrong LoRA target modules')
    entries=tensor_headers(folder/'adapter_model.safetensors',finite_f32=True)
    expected_keys={n+'.lora_'+ab+'.weight' for n in wanted for ab in 'AB'}
    require(set(entries)==expected_keys, 'Missing/unexpected adapter tensors')
    for n in wanted:
        a=entries[n+'.lora_A.weight']['shape']; b=entries[n+'.lora_B.weight']['shape']
        part=n.rsplit('.',1)[1]
        out_dim,in_dim={'q_proj':(4096,768),'k_proj':(1024,768),'v_proj':(1024,768),'o_proj':(768,4096)}[part]
        require(a==[8,in_dim] and b==[out_dim,8], 'LoRA tensor shape mismatch: '+n)
    require(sum(math.prod(x['shape']) for x in entries.values())==3833856, 'LoRA parameter count mismatch')
    if joint:
        entries=tensor_headers(folder/'projection_weights.safetensors',finite_f32=True)
        wanted_shapes={f'model.{n}.{part}': list(shape if part=='weight' else (shape[0],)) for n,shape in PROJECTIONS.items() for part in ('weight','bias')}
        require({n:i['shape'] for n,i in entries.items()}==wanted_shapes, 'Projection names/shapes differ')
    return {'generation':'joint50' if joint else 'clean50-fallback', 'completed_updates':update, 'samples_consumed':samples, 'metadata':metadata}


def verify_package(folder):
    root=Path(folder)
    m=read_json(root/'package-manifest.json')
    require(m.get('format')==FORMAT and isinstance(m.get('files'),dict) and bool(m['files']), 'Invalid/empty package manifest')
    actual=files_under(root); actual.pop('package-manifest.json',None)
    require(set(actual)==set(m['files']), 'Package file coverage mismatch')
    for name, entry in m['files'].items():
        relative(name)
        require(isinstance(entry,dict) and entry.get('bytes')==actual[name].stat().st_size and entry.get('sha256')==sha(actual[name]), 'Package content mismatch: '+name)
    recipe=read_json(root/'runtime/profile.json')
    require(recipe.get('format')==FORMAT and recipe.get('precision')=='FP32' and recipe.get('num_steps')==10, 'Wrong runtime profile')
    mandatory={'runtime/runtime-versions.json','runtime/model_builder.py','runtime/inference_cache_recovery.py','runtime/lingbot_zero_padding.py','runtime/robotwin.yaml','runtime/initializer-identity.json','source/lingbotvla/__init__.py','base/source-manifest.json','qwen/source-manifest.json','qwen/config.json','qwen/preprocessor_config.json','qwen/tokenizer_config.json','qwen/tokenizer.json'}
    require(mandatory <= set(actual), 'Missing runtime/base/tokenizer assets: '+str(sorted(mandatory-set(actual))))
    identity=read_json(root/'runtime/initializer-identity.json')
    require(all(isinstance(identity.get(k),dict) and identity[k] for k in ('package_versions','model_settings','data_settings')), 'Incomplete initializer settings')
    versions=read_json(root/'runtime/runtime-versions.json')
    require(isinstance(versions,dict) and {'torch','transformers','peft','safetensors','torchvision','accelerate','tokenizers','Pillow','PyYAML'}<=set(versions), 'Incomplete runtime version receipt')
    require(all(versions.get(k)==v for k,v in identity['package_versions'].items()), 'Runtime receipt differs from initializer')
    for group in ('base','qwen'):
        require(sha(root/group/'source-manifest.json')==identity.get(group+'_manifest_sha256'), 'Initializer source receipt differs: '+group)
    require(sha(root/'runtime/inference_cache_recovery.py')==CACHE_SHA, 'Cache helper identity differs')
    require(sha(root/'runtime/model_builder.py')==BUILDER_SHA, 'Builder identity differs')
    require(sha(root/'runtime/lingbot_zero_padding.py')==PADDING_SHA, 'Padding helper identity differs')
    policy='source/lingbotvla/models/vla/lingbot_vla/modeling_lingbot_vla_v2.py'
    require(policy in actual and sha(actual[policy])==identity.get('policy_sha256'), 'Policy source identity differs')
    moe='source/lingbotvla/models/vla/lingbot_vla/qwen2_action_expert.py'
    require(moe in actual and sha(actual[moe])==identity.get('moe_sha256'), 'MoE source identity differs')
    shards=list((root/'base').glob('model-*.safetensors'))
    require(len(shards)==6, 'Expected six base shards')
    names=set()
    for shard in shards:
        h=tensor_headers(shard)
        require(not names.intersection(h), 'Duplicate base tensor')
        names.update(h)
    info=checkpoint_info(root/'checkpoint')
    require(info['metadata']['identity']['normalization_sha256']==identity['normalization_sha256'], 'Initializer/checkpoint normalization differs')
    if info['generation']=='clean50-fallback':
        require(info['metadata']['identity']==identity, 'Fallback/initializer identity differs')
    return {'format':FORMAT,'manifest_sha256':sha(root/'package-manifest.json'), 'generation':info['generation'],'completed_updates':info['completed_updates'],'files':len(actual), 'scope':'CPU content/structure only; model load and output parity not run'}


def export_package(checkpoint, assets_root, output):
    """assets_root contains base/, qwen/, source/lingbotvla/, runtime/.

    Full copies: no hard links, overwrite, GPU work, or dependency installation.
    Missing/invalid inputs leave no published output or partial staging directory.
    """
    checkpoint=Path(checkpoint).resolve(); assets_root=Path(assets_root).resolve(); output=Path(output).absolute()
    require(not output.exists(), 'Output already exists')
    require(output!=checkpoint and checkpoint not in output.parents and output!=assets_root and assets_root not in output.parents, 'Output overlaps input')
    checkpoint_info(checkpoint)
    required={'base','qwen','source','runtime'}
    require({p.name for p in assets_root.iterdir()}==required and all((assets_root/g).is_dir() for g in required), 'assets-root must contain exactly base/qwen/source/runtime')
    # Validate input paths and reserve checkpoint/manifest names before any copying.
    inputs=files_under(assets_root)
    require(bool(inputs), 'Empty assets root')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=output.name+'.partial-',dir=output.parent))
    try:
        shutil.copytree(checkpoint,stage/'checkpoint')
        for group in sorted(required): shutil.copytree(assets_root/group,stage/group)
        entries={name:{'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in files_under(stage).items()}
        write_json(stage/'package-manifest.json',{'format':FORMAT,'files':entries})
        result=verify_package(stage)
        publish(stage,output)
        return result
    finally:
        if stage.exists(): shutil.rmtree(stage)


def publish(stage,output):
    # Linux renameat2 publishes the whole validated directory atomically and refuses overwrite.
    import ctypes, sys
    if sys.platform.startswith('linux'):
        libc=ctypes.CDLL(None,use_errno=True)
        require(hasattr(libc,'renameat2'), 'Atomic no-replace rename unavailable')
        result_code=libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(output),1)
        if result_code: raise OSError(ctypes.get_errno(), 'Atomic publication failed')
    elif os.name=='nt':
        os.rename(stage,output)  # Windows refuses an existing destination.
    else:
        raise RuntimeError('Atomic no-replace export currently supports Linux/Windows')


def export_from_plan(checkpoint, asset_plan, output):
    checkpoint=Path(checkpoint).resolve(); output=Path(output).absolute()
    require(not output.exists(), 'Output already exists')
    info=checkpoint_info(checkpoint)
    plan=read_json(asset_plan)
    require(plan.get('format')==FORMAT and isinstance(plan.get('files'),dict) and bool(plan['files']), 'Invalid asset plan')
    require(output!=checkpoint and checkpoint not in output.parents, 'Output overlaps checkpoint')
    for name,entry in plan['files'].items():
        rel=relative(name)
        require(rel.parts[0] in {'base','qwen','source','runtime'},'Reserved/unknown asset destination')
        source=Path(entry['source'])
        require(source.is_absolute() and source.is_file() and not source.is_symlink(),'Invalid planned source: '+name)
        require(output!=source and output not in source.parents,'Output overlaps planned source')
        require(source.stat().st_size==entry['bytes'],'Planned source size changed: '+name)
    required_bytes=sum(x['bytes'] for x in plan['files'].values())+sum(p.stat().st_size for p in checkpoint.iterdir())
    output.parent.mkdir(parents=True,exist_ok=True)
    require(shutil.disk_usage(output.parent).free>=required_bytes+1024**3,'Insufficient space for full immutable export plus 1 GiB margin')
    stage=Path(tempfile.mkdtemp(prefix=output.name+'.partial-',dir=output.parent))
    try:
        shutil.copytree(checkpoint,stage/'checkpoint')
        require(sha(checkpoint/'checkpoint.json')==sha(stage/'checkpoint/checkpoint.json'),'Checkpoint changed while exporting')
        for name,entry in plan['files'].items():
            destination=stage/name; destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(entry['source'],destination)
            require(sha(destination)==entry['sha256'],'Planned asset hash changed: '+name)
        entries={name:{'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in files_under(stage).items()}
        write_json(stage/'package-manifest.json',{'format':FORMAT,'files':entries,'asset_plan_sha256':sha(asset_plan)})
        result=verify_package(stage)
        publish(stage,output)
        return result
    finally:
        if stage.exists(): shutil.rmtree(stage)
