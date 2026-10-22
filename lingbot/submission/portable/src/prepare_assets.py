"""Freeze a CPU-only file-copy plan from existing local assets; no downloads or model load."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
from portable_manifest import CACHE_SHA, FORMAT, read_json, require, sha, write_json


def prepare(base,qwen,repo,identity,robot_config,cache_helper,padding_helper,output):
    output=Path(output).absolute()
    require(not output.exists(),'Plan directory exists')
    identity=Path(identity); saved=read_json(identity)
    require(saved.get('batch_size')==4 and 'model_settings' in saved and 'data_settings' in saved and 'package_versions' in saved,'Supply original initializer resolved-inputs.json')
    base,qwen,repo=map(lambda p:Path(p).resolve(),(base,qwen,repo))
    for group,root in (('base',base),('qwen',qwen)):
        require(sha(root/'source-manifest.json')==saved[group+'_manifest_sha256'],'Source receipt changed: '+group)
    require(sha(cache_helper)==CACHE_SHA,'Cache helper changed')
    require(sha(padding_helper)=='c19331adff45535fc58a4b1dd8c1862cb91234aaaf8d59a0e627ba5c42d94c4d','Padding helper changed')
    require(output!=base and base not in output.parents and output!=qwen and qwen not in output.parents and output!=repo and repo not in output.parents,'Plan output overlaps assets')
    output.mkdir(parents=True)
    try:
        runtime=output/'runtime'; runtime.mkdir()
        for src,name in ((identity,'initializer-identity.json'),(robot_config,'robotwin.yaml'),(cache_helper,'inference_cache_recovery.py'),(padding_helper,'lingbot_zero_padding.py'),(Path(__file__).with_name('model_builder.py'),'model_builder.py')):
            shutil.copyfile(src,runtime/name)
        versions={name:importlib.metadata.version(name) for name in set(saved['package_versions'])|{'safetensors','torchvision','accelerate','tokenizers','Pillow','PyYAML'}}
        require(all(versions[k]==v for k,v in saved['package_versions'].items()),'Current versions differ from initializer')
        write_json(runtime/'runtime-versions.json',versions)
        write_json(runtime/'profile.json',{'format':FORMAT,'precision':'FP32','num_steps':10,'scope':'retained clean50/joint50 model and input contract'})
        files={}
        roots=(('base',base),('qwen',qwen),('source/lingbotvla',repo/'lingbotvla'),('runtime',runtime))
        for prefix,root in roots:
            require(root.is_dir(),'Missing input tree: '+str(root))
            for p in sorted(root.rglob('*')):
                rel=p.relative_to(root)
                if any(x in ('__pycache__','.git','.cache') for x in rel.parts) or p.suffix=='.pyc': continue
                require(not p.is_symlink(),'Resolve source symlink explicitly before preparing: '+str(p))
                if p.is_file():
                    name=prefix+'/'+rel.as_posix()
                    files[name]={'source':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
        plan={'format':FORMAT,'files':files,'provenance_scope':'Original source-manifest hashes bound to initializer; all present asset bytes frozen here. This is not an independent re-download/source authenticity audit.'}
        write_json(output/'asset-plan.json',plan)
        return {'plan':str(output/'asset-plan.json'),'files':len(files),'bytes_to_copy':sum(x['bytes'] for x in files.values()),'model_loaded':False}
    except BaseException:
        shutil.rmtree(output)
        raise


def main():
    p=argparse.ArgumentParser()
    for name in ('base','qwen','repo','identity','robot-config','cache-helper','padding-helper','output'): p.add_argument('--'+name,required=True)
    a=p.parse_args(); print(json.dumps(prepare(**vars(a)),indent=2))

if __name__=='__main__': main()
