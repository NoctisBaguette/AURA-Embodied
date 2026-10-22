import argparse
import json
from portable_manifest import export_package, export_from_plan

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-checkpoint',required=True)
    assets=p.add_mutually_exclusive_group(required=True)
    assets.add_argument('--assets-root'); assets.add_argument('--assets-plan')
    p.add_argument('--output',required=True)
    a=p.parse_args()
    result=export_from_plan(a.source_checkpoint,a.assets_plan,a.output) if a.assets_plan else export_package(a.source_checkpoint,a.assets_root,a.output)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
