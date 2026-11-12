"""Frozen fresh M7 matrix with a retained first18 pilot and guarded resume."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
from uuid import uuid4

import numpy as np

from .m7_frozen import (SEEDS, RATIOS, SOURCES, SCOPE, SESSION_FIELDS, ROOT, PROTOCOL_PATH,
                        preflight, preflight_native, checked_trial, validate_commission, sha256)
from .m7_runtime import SYSTEMS
from .m7_development import file_index
from .m7_audit import suite_pairs
from .m7_summary import summarize, write_csvs


def write_json(path, value):
    temporary = path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def child_environment():
    return {k:v for k,v in os.environ.items() if k not in SESSION_FIELDS}


def environment_digest(environment):
    return hashlib.sha256(json.dumps(environment,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def plan(output):
    natural=[{'ratio':r,'seed':s,'system':system,
              'output':str(output/f'ratio-{r:g}'/f'seed-{s}'/system)}
             for r in RATIOS for s in SEEDS for system in SYSTEMS]
    pilot=[item for r in (0.,.5,2.) for s in SEEDS[:2] for item in natural if item['ratio']==r and item['seed']==s]
    selected={(item['ratio'],item['seed'],item['system']) for item in pilot}
    return pilot+[item for item in natural if (item['ratio'],item['seed'],item['system']) not in selected]


def seed_history(output, resume):
    root=Path(__file__).resolve().parents[1]/'runs'
    seen=set();count=0
    for path in sorted(root.rglob('events.jsonl')):
        if resume and output in path.resolve().parents:
            continue
        count+=1
        with path.open() as stream:
            for line in stream:
                e=json.loads(line)
                if e['event'] in ('reset','controller_reset') and 'seed' in e:
                    seen.add(e['seed'])
    overlap=sorted(seen.intersection(SEEDS))
    if overlap:
        raise ValueError('Selected fresh seeds have resets outside this authorized study: '+str(overlap))
    return {'root':str(root),'event_files_checked':count,'recorded_reset_seeds':sorted(seen),'selected_overlap':overlap,
            'scope':'retained_native_history_not_unreported_or_deleted_runs','own_validated_study_excluded':resume}


def launch_child(item, environment, suite_path):
    output=Path(item['output']);output.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-u','-m','aether_cl.m7_frozen','--seed',str(item['seed']),
             '--system',item['system'],'--offset-clearance-ratio',str(item['ratio']),
             '--output',str(output),'--suite',str(suite_path)]
    with (output/'process.stdout.log').open('x') as stdout,(output/'process.stderr.log').open('x') as stderr:
        process=subprocess.Popen(command,env=environment.copy(),stdout=stdout,stderr=stderr,start_new_session=True)
        try:
            status=process.wait()
        except BaseException:
            try:os.killpg(process.pid,signal.SIGINT)
            except ProcessLookupError:pass
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
            raise
    if status:
        raise RuntimeError(f'Fresh child exit{status}; retain {output}/process.stderr.log and partial evidence')
    paths=list(output.glob('*/result.json'))
    if len(paths)!=1:
        raise ValueError('Expected one isolated fresh episode')
    return paths[0].parent


def assess_pilot(report):
    trials=report['trials'][:18]
    complete=len(trials)==18 and all(t.get('state')=='passed' for t in trials)
    pairs=report.get('pairs',[])
    counts=report['protocol']['pilot_comparison_counts']
    checks={'first18_complete_replayed':complete,'strict_pairs':len(pairs)==sum(counts.values()) and all(p['passed'] for p in pairs)}
    normal=[t['result'] for t in trials if t.get('result') and t['ratio']==0. and t['system']=='baseline']
    checks['at_least_one_healthy_normal_baseline']=any(r['task_success_at_end'] for r in normal)
    injected=[t['result'] for t in trials if t.get('result') and t['ratio']!=0. and t['system'] in ('baseline','v1')]
    checks['precontact_injections']=len(injected)==8 and all(
        r['injection']['applied'] and r['injection']['precondition']
        and np.linalg.norm(r['pre_insert_state']['peg_box_contact_force_world_n'])<=.05
        and r['pre_insert_state']['reference']['depth_m']<=-.04 for r in injected)
    return {'passed':all(checks.values()),'checks':checks,'failed_checks':[k for k,v in checks.items() if not v],
            'interpretation':'commissioning_only_no_v2_success_gate_no_exclusions_or_replacement_pilot_retained'}


def snapshot(output, archive, report):
    if archive.exists():
        raise ValueError('Archive exists; retain it')
    report['saved_archive']=str(archive)
    write_json(output/'suite.json',report)
    write_json(output/'archive_index.json',{'files':file_index(output),'index_excludes_self':True})
    archive.parent.mkdir(parents=True,exist_ok=True)
    with archive.open('xb') as stream,tarfile.open(fileobj=stream,mode='w:gz') as tar:
        tar.add(output,arcname=output.name)
    digest=sha256(archive)
    write_json(Path(str(archive)+'.receipt.json'),{'archive':str(archive),'archive_sha256':digest,'state':report['state']})
    print('Archive:',archive,flush=True);print('Archive SHA-256:',digest,flush=True)
    return digest


def validate_checkpoint(output, report, selected, settings, native, archive):
    if (report['state']!='paused' or report['protocol']!=settings or report['native']!=native
            or report['archive']!=str(archive) or report['run_directory']!=str(output)
            or json.loads((output/'protocol.json').read_text())!=settings):
        raise ValueError('Resume scope/source/software/environment/path or checkpoint state differs')
    if not 18<=len(report['trials'])<len(selected):
        raise ValueError('Resume requires an intact completed pilot and unstarted slots')
    if json.loads((output/'archive_index.json').read_text())['files']!=file_index(output):
        raise ValueError('Checkpoint raw files changed; retain evidence')
    saved=Path(report['saved_archive'])
    receipt=json.loads(Path(str(saved)+'.receipt.json').read_text())
    if receipt['archive_sha256']!=sha256(saved) or receipt['archive']!=str(saved):
        raise ValueError('Checkpoint archive or receipt differs')
    pilot=Path(report['pilot_archive'])
    pilot_receipt=json.loads(Path(str(pilot)+'.receipt.json').read_text())
    if pilot_receipt['archive_sha256']!=sha256(pilot) or pilot_receipt['state']!='paused':
        raise ValueError('Immutable pilot archive differs')
    with tarfile.open(pilot) as tar:
        member=next(m for m in tar.getmembers() if m.name==output.name+'/archive_index.json')
        indexed=json.load(tar.extractfile(member))['files']
        raw_names={e['path'] for e in indexed if e['path'].startswith(('ratio-','source_snapshot/')) or e['path']=='protocol.json'}
        for e in indexed:
            if e['path'] in raw_names:
                p=output/e['path']
                if not p.is_file() or p.stat().st_size!=e['bytes'] or sha256(p)!=e['sha256']:
                    raise ValueError('Immutable pilot raw child/source/protocol bytes differ')
    for item,trial in zip(selected,report['trials']):
        if trial.get('state')!='passed' or any(trial.get(k)!=v for k,v in item.items()):
            raise ValueError('Resume trial order/configuration or completeness differs; no slot reruns')
        result,audit=checked_trial(output/trial['run_directory'],item,native)
        if result!=trial['result'] or audit!=trial['audit']:
            raise ValueError('Resume recorded outcomes differ from replay')
    pairs=suite_pairs(report['trials'],output,include_controls=True)
    if pairs!=report['pairs'] or summarize(report['trials'],SEEDS,RATIOS)!=report['summary']:
        raise ValueError('Resume comparisons or aggregate results differ')
    pilot_report={**report,'trials':report['trials'][:18],
                  'pairs':suite_pairs(report['trials'][:18],output,include_controls=True)}
    if not assess_pilot(pilot_report)['passed']:
        raise ValueError('Retained pilot gate does not pass')
    return {'archive':str(pilot),'archive_sha256':pilot_receipt['archive_sha256'],
            'raw_child_source_protocol_files_retained':len(raw_names)}


def run_sweep(output, archive, commission_report=None, commission_archive=None, resume=False, stop_after=None):
    settings=preflight()
    output,archive=Path(output).resolve(),Path(archive).resolve()
    pilot=archive.with_name(archive.name.removesuffix('.tar.gz')+'-pilot.tar.gz')
    if output==archive or output in archive.parents or archive.exists():
        raise ValueError('Final archive must be new and outside the study directory')
    if stop_after is not None and (type(stop_after) is not int or stop_after<1):
        raise ValueError('stop_after must be positive')
    if not resume and stop_after not in (None,18):
        raise ValueError('Initial fresh execution must stop at the frozen first18 pilot')
    if not resume and (output.exists() or pilot.exists() or Path(str(pilot)+'.receipt.json').exists()):
        raise ValueError('Fresh output/pilot must be new; retain existing evidence')
    environment=child_environment();native=preflight_native()
    native={**native,'startup_environment_sha256':environment_digest(environment)}
    commissioning=None
    if not resume:
        if commission_report is None or commission_archive is None:
            raise ValueError('Fresh entry requires independently reviewed known36 report and archive')
        print('Checking retained known36 commissioning hashes, replays and pairs before any fresh reset.',flush=True)
        commissioning=validate_commission(commission_report,commission_archive)
    if resume and not output.is_dir():
        raise ValueError('Resume output is absent')
    if not resume:output.mkdir(parents=True,exist_ok=False)
    selected=plan(output)
    with (output/'runner.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another M7 runner owns this study') from None
        if resume:
            report=json.loads((output/'suite.json').read_text())
            print('Checking paused checkpoint and immutable pilot before resuming unstarted slots.',flush=True)
            immutable=validate_checkpoint(output,report,selected,settings,native,archive)
            report['immutable_pilot']=immutable
        else:
            report={'scope':SCOPE,'protocol':settings,'native':native,'run_directory':str(output),'archive':str(archive),
                'pilot_archive':str(pilot),'fresh_native':True,'protocol_frozen':True,'model_training':False,
                'commissioning':commissioning,'trials':[],'passed_means':'complete_matched_audited_evidence_not_task_success'}
            write_json(output/'protocol.json',settings)
            source=output/'source_snapshot';source.mkdir()
            for name in SOURCES:(source/name).write_bytes(Path(__file__).with_name(name).read_bytes())
            (source/PROTOCOL_PATH.name).write_bytes(PROTOCOL_PATH.read_bytes())
            for name in ('AETHER_CL_M7_Installed_Inspection.json','AETHER_CL_M7_Candidates_v5_Review.json'):
                (source/name).write_bytes((ROOT/'docs/research/experiments/evidence'/name).read_bytes())
            (source/'m7_task_inspection.py').write_bytes((ROOT/'tools/m7_task_inspection.py').read_bytes())
        history=seed_history(output,resume)
        if not resume:report['fresh_seed_history']=history
        else:report['resume_external_history']=history
        report.update(state='running',runner_pid=os.getpid())
        write_json(output/'suite.json',report)
        limit=18 if not resume else len(selected) if stop_after is None else min(len(selected),len(report['trials'])+stop_after)
        try:
            for item in selected[len(report['trials']):limit]:
                preflight()
                trial={**item,'state':'running'};report['trials'].append(trial)
                write_json(output/'suite.json',report)
                print(f"START {len(report['trials'])}/360 ratio={item['ratio']} seed={item['seed']} {item['system']}",flush=True)
                try:
                    directory=launch_child(item,environment,output/'suite.json')
                    result,audit=checked_trial(directory,item,native)
                    trial.update(state='passed',run_directory=str(directory.relative_to(output)),result=result,audit=audit)
                    print(f"END success={result['task_success_at_end']} legacy_velocity_success={result['final_reference']['legacy_velocity_task_success']} "
                          f"depth_mm={result['final_reference']['depth_m']*1000:.3f} recovery={result['recovery']['state']}",flush=True)
                except BaseException as error:
                    trial.update(state='error',error=f'{type(error).__name__}: {error}')
                    raise
                write_json(output/'suite.json',report)
            report['pairs']=suite_pairs(report['trials'],output,include_controls=True)
            report['summary']=summarize(report['trials'],SEEDS,RATIOS)
            report['state']='passed' if len(report['trials'])==len(selected) else 'paused'
            if not resume:
                report['pilot_gate']=assess_pilot(report)
                if not report['pilot_gate']['passed']:
                    report['state']='failed'
            if report['state']=='passed' and (len(report['pairs'])!=340 or not all(p['passed'] for p in report['pairs'])):
                raise ValueError('Final matched comparisons incomplete')
        except BaseException as error:
            report.update(state='interrupted' if isinstance(error,KeyboardInterrupt) else 'error',error=f'{type(error).__name__}: {error}')
            report['summary']=summarize(report['trials'],SEEDS,RATIOS)
        write_csvs(output,report['summary'])
        saved=pilot if not resume else archive if report['state']=='passed' else archive.with_name(
            archive.name.removesuffix('.tar.gz')+'-partial-'+uuid4().hex[:8]+'.tar.gz')
        digest=snapshot(output,saved,report)
        if report['state']=='paused' and not resume:
            print('M7_FIRST18_READY_FOR_INDEPENDENT_REVIEW',flush=True)
        elif report['state']=='passed':print('M7_FROZEN_EVIDENCE_VALID',flush=True)
        else:print('M7_'+report['state'].upper()+'_RETAIN_EVIDENCE',flush=True)
        return {**report,'archive_sha256':digest}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output',type=Path,required=True);cli.add_argument('--archive',type=Path,required=True)
    cli.add_argument('--commission-report',type=Path);cli.add_argument('--commission-archive',type=Path)
    cli.add_argument('--resume',action='store_true');cli.add_argument('--stop-after',type=int)
    cli.add_argument('--check-pilot',action='store_true')
    args=cli.parse_args()
    if args.check_pilot:
        if args.resume or args.stop_after is not None:cli.error('Read-only pilot check cannot launch trials')
        settings=preflight();output=args.output.resolve();report=json.loads((output/'suite.json').read_text())
        native={**preflight_native(),'startup_environment_sha256':environment_digest(child_environment())}
        validate_checkpoint(output,report,plan(output),settings,native,args.archive.resolve())
        result=assess_pilot(report);print(json.dumps(result,indent=2),flush=True)
        raise SystemExit(0 if result['passed'] else 2)
    report=run_sweep(args.output,args.archive,args.commission_report,args.commission_archive,args.resume,args.stop_after)
    raise SystemExit(0 if report['state'] in ('paused','passed') else 2)


if __name__=='__main__':main()
