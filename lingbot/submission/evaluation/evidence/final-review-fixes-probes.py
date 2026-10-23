"""Bounded independent CPU probes of the frozen final repairs; synthetic only."""
from pathlib import Path
import json
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[4]
snapshot = (ROOT/'review-final-fixes-snapshot.txt').read_text(encoding='utf-8-sig')
def source(filename):
    return snapshot.split('FILE lingbot\\submission\\evaluation\\'+filename+'\n',1)[1].split('\nFILE ',1)[0]
def load(name, filename):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT/'lingbot/submission/evaluation'/filename)
    sys.modules[name] = module
    exec(compile(source(filename), module.__file__, 'exec'), module.__dict__)
    return module
ledger = load('ledger','ledger.py')
runner = load('final_runner','evaluate.py')
tasks = runner.load_tasks(ROOT/'lingbot/official/results-template.json')
with tempfile.TemporaryDirectory(prefix='lingbot-final-fixes-cpu-') as temporary:
    root = Path(temporary)
    fake = root/'fake_backend.py'
    fake.write_text((ROOT/'lingbot/submission/evaluation/tests/fake_backend.py').read_text(encoding='utf-8'),encoding='utf-8')
    for mode in ['large_success','always_reject','large_crash','large_invalid_json','sleep','pending_video']:
        output = root/mode
        plan = runner.build_plan(tasks=tasks,selected_tasks=['lift_pot'],setting='clean',episodes=1,max_candidates=1,
            seed_start=100000,manifest_sha256='a'*64,stage='baseline',output_dir=output)
        run = runner.SerialEvaluator(plan=plan,output_dir=output,policy_package='TEST_FIXTURE_ONLY',
            backend_command=[sys.executable,str(fake),mode,str(root/(mode+'.counter'))],
            episode_timeout_seconds=.5 if mode=='sleep' else 3,cell_timeout_seconds=10,stage_timeout_seconds=20,test_only_fixture=True)
        run.run(resume=False)
        terminal = run.ledger.terminal_records()[0]
        stdout = Path(terminal['backend_stdout_path']).read_text(encoding='utf-8')
        stderr = Path(terminal['backend_stderr_path']).read_text(encoding='utf-8')
        assert terminal['execution_evidence']['backend_stdout_path'] == terminal['backend_stdout_path']
        if mode in {'large_success','large_crash','large_invalid_json','sleep'}:
            assert 'OUT_BEGIN_' in stdout and '_OUT_END' in stdout and len(stdout)>6000
            assert 'ERR_BEGIN_' in stderr and '_ERR_END' in stderr and len(stderr)>6000
        if mode=='pending_video':
            assert terminal['terminal_status']=='INFRA_ERROR' and 'video_review_status' in terminal['error']['message']
        print(mode,terminal['terminal_status'],'retained_stream_bytes',len(stdout),len(stderr))
    identity = run._identity(plan['cells'][0],plan['cells'][0]['candidates'][0])
    config = {'evidence_kind':'fixture','plan':{'stage':'baseline','checkpoint_manifest_sha256':'a'*64}}
    for field,value in [('evidence_kind','real_policy'),('stage','candidate'),('checkpoint_manifest_sha256','b'*64)]:
        journal=ledger.EvaluationLedger(root/('ledger-'+field),config)
        journal.initialize(resume=False)
        changed=dict(identity,**{field:value})
        try:
            journal.begin(changed)
        except ValueError as error:
            assert field in str(error)
        else:
            raise AssertionError('write mismatch accepted')
        path=journal.begin(identity)
        record=json.loads(path.read_text(encoding='utf-8'))
        record[field]=value
        record['record_sha256']=journal._record_sha256(record)
        path.write_text(json.dumps(record),encoding='utf-8')
        try:
            journal.terminal_records()
        except ValueError as error:
            assert field in str(error)
        else:
            raise AssertionError('read mismatch accepted')
        print('ledger',field,'write_and_read_rejected')
