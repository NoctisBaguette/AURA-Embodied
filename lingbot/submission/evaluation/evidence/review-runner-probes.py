"""Independent synthetic CPU probes of the frozen runner snapshot; not policy evidence."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[4]
snapshot = (ROOT / 'review-runner-snapshot.txt').read_text(encoding='utf-8-sig')

def source(name):
    return snapshot.split('FILE ' + name + '\n', 1)[1].split('\nFILE ', 1)[0]

ledger = types.ModuleType('ledger')
exec(compile(source('lingbot\\submission\\evaluation\\ledger.py'), 'frozen_ledger', 'exec'), ledger.__dict__)
sys.modules['ledger'] = ledger
runner = types.ModuleType('frozen_runner')
runner.__file__ = str(ROOT / 'lingbot/submission/evaluation/evaluate.py')
exec(compile(source('lingbot\\submission\\evaluation\\evaluate.py'), 'frozen_runner', 'exec'), runner.__dict__)
template = ROOT / 'lingbot/official/results-template.json'
tasks = runner.load_tasks(template)

def new_runner(folder, command, budget=1):
    plan = runner.build_plan(tasks=tasks, selected_tasks=['lift_pot'], setting='clean',
        episodes=1, max_candidates=budget, seed_start=100000,
        manifest_sha256='a'*64, stage='baseline', output_dir=folder)
    return runner.SerialEvaluator(plan=plan, output_dir=folder,
        policy_package='TEST_FIXTURE_ONLY', backend_command=command,
        episode_timeout_seconds=2, cell_timeout_seconds=10,
        stage_timeout_seconds=20, test_only_fixture=True)

with tempfile.TemporaryDirectory(prefix='lingbot-review-cpu-') as tmp:
    temp = Path(tmp)
    fake = temp / 'fixture.py'
    fake.write_text(source('lingbot\\submission\\evaluation\\tests\\fake_backend.py'), encoding='utf-8')
    command = [sys.executable, str(fake), 'typed_then_success', str(temp/'counter.txt')]
    run = new_runner(temp/'budget', command)
    report = run.run(resume=False)
    terminal = run.ledger.terminal_records()[0]
    print('BUDGET', json.dumps({k: report[k] for k in ('status','remaining_episodes','errors','completed_episodes')}))
    print('REJECTION_MISSING_FIELDS', [k for k in ('wall_seconds','actions_started','log_path','video_path') if k not in terminal])

    expired = new_runner(temp/'expired', command)
    expired._elapsed = lambda started: 21
    report = expired.run(resume=False)
    print('STAGE_EXPIRED', json.dumps({k: report[k] for k in ('status','remaining_episodes','errors','completed_episodes')}))

    fail_command = [sys.executable, '-c', "import sys; print('stdout-evidence'); print('stderr-evidence',file=sys.stderr); sys.exit(9)"]
    fail = new_runner(temp/'failure', fail_command)
    report = fail.run(resume=False)
    term = fail.ledger.terminal_records()[0]
    print('FAILURE_MISSING_FIELDS', [k for k in ('wall_seconds','actions_started','log_path','video_path') if k not in term])
    print('FAILURE_STDOUT_RETAINED', 'stdout-evidence' in json.dumps(term) or 'stdout-evidence' in json.dumps(report))
    print('FAILURE_LOG_FILES', [p.name for p in (temp/'failure').rglob('*.log')])
    package = temp/'package'
    package.mkdir()
    (package/'manifest.json').write_text('{}',encoding='utf-8')
    argv = ['--policy-package',str(package),'--tasks-file',str(template),'--setting','clean',
            '--task','lift_pot','--episodes','1','--max-candidates','1','--output',str(temp/'cli'),
            '--backend-executable',sys.executable,'--backend-arg=-c',
            '--backend-arg=import sys; sys.exit(9)']
    print('FATAL_CLI_EXIT',runner.main(argv))

    # Direct ledger API mismatch: immutable fixture start must not become a real-policy terminal.
    identity = run._identity(run.plan['cells'][0],run.plan['cells'][0]['candidates'][0])
    completed = dict(identity, status='COMPLETE',task_success=True,task_predicate=True,
        actions_started=25,step_limit=50,official_step_limit=50,chunks=1,wall_seconds=.25,
        log_path='fixture.log',video_path=None,video_review_status='NOT_REVIEWED',
        requests=[dict(request_id=identity['request_id_prefix']+'-chunk-0001',chunk_index=1,noise_seed=777)])
    changed = dict(completed, evidence_kind='real_policy')
    l = ledger.EvaluationLedger(temp/'launder',{'evidence_kind':'fixture'})
    l.initialize(resume=False)
    l.begin(identity)
    l.finish(identity['episode_id'],dict(identity,evidence_kind='real_policy',terminal_status='COMPLETE_POLICY',episode=changed))
    records = l.started_records()+l.terminal_records()
    print('FIXTURE_TERMINAL_EVIDENCE_KIND',records[-1]['evidence_kind'])
    aggregate_path=ROOT/'lingbot/submission/evaluation/aggregate_results.py'
    aggregate_code=aggregate_path.read_bytes()
    a=types.ModuleType('review_live_aggregate')
    exec(compile(aggregate_code,str(aggregate_path),'exec'),a.__dict__)
    print('LIVE_AGGREGATOR_SHA256',hashlib.sha256(aggregate_code).hexdigest())
    official,audit=a.aggregate_records(records,json.loads(template.read_text()),'a'*64,'review-fixture')
    print('FIXTURE_LAUNDER_COUNT',audit['real_policy_episodes'])

    malformed=dict(completed,requests=[dict(completed['requests'][0],chunk_index=True)])
    runner.SerialEvaluator._validate_episode(malformed,identity)
    print('BOOLEAN_CHUNK_INDEX_RUNNER','accepted')
    try:
        a.aggregate_records([dict(malformed,evidence_kind='real_policy')],json.loads(template.read_text()),'a'*64,'review-fixture')
        print('BOOLEAN_CHUNK_INDEX_AGGREGATOR','accepted')
    except ValueError as exc:
        print('BOOLEAN_CHUNK_INDEX_AGGREGATOR',str(exc))

    # Only bounded CPU dummy children. Child exits itself after 1.2 s.
    child_code="import time; time.sleep(1.2)"
    parent_code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"]); time.sleep(5)"
    backend=runner.SubprocessBackend([sys.executable,'-c',parent_code])
    start=time.monotonic()
    try:
        backend.evaluate({},.15)
    except TimeoutError:
        print('DESCENDANT_PIPE_TIMEOUT_SECONDS',round(time.monotonic()-start,3),'requested=0.15')
