"""Focused CPU regression review of review-final-snapshot.txt; no policy results."""
from pathlib import Path
import json
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[4]
snapshot = (ROOT / 'review-final-snapshot.txt').read_text(encoding='utf-8-sig')
def load(name, filename):
    code = snapshot.split('FILE lingbot\\submission\\evaluation\\' + filename + '\n', 1)[1].split('\nFILE ', 1)[0]
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / 'lingbot/submission/evaluation' / filename)
    sys.modules[name] = module
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    return module

ledger = load('ledger', 'ledger.py')
runner = load('final_frozen_runner', 'evaluate.py')
aggregate = load('final_frozen_aggregate', 'aggregate_results.py')
template_path = ROOT / 'lingbot/official/results-template.json'
template = json.loads(template_path.read_text(encoding='utf-8'))
with tempfile.TemporaryDirectory(prefix='lingbot-final-cpu-') as tmp:
    root = Path(tmp)
    plan = runner.build_plan(tasks=runner.load_tasks(template_path), selected_tasks=['lift_pot'], setting='clean', episodes=1,
        max_candidates=1, seed_start=100000, manifest_sha256='a'*64, stage='baseline', output_dir=root/'run')
    run = runner.SerialEvaluator(plan=plan, output_dir=root/'run', policy_package='TEST_FIXTURE_ONLY',
        backend_command=[sys.executable, '-c', "import sys; print('LOST_BEGIN_'+'x'*5000); print('ERR_BEGIN_'+'y'*5000,file=sys.stderr);sys.exit(9)"],
        episode_timeout_seconds=3, cell_timeout_seconds=10, stage_timeout_seconds=20, test_only_fixture=True)
    report = run.run(resume=False)
    terminal = run.ledger.terminal_records()[0]
    print('FAILURE_LOG_FILES', [str(p.relative_to(root)) for p in root.rglob('*.log')])
    print('FAILURE_OUTPUT_START_RETAINED', 'LOST_BEGIN_' in json.dumps(terminal), 'ERR_BEGIN_' in json.dumps(terminal))
    print('FAILURE_EVIDENCE', {k: terminal.get(k) for k in ['wall_seconds', 'actions_started', 'log_path', 'video_path']})
    identity = run._identity(plan['cells'][0], plan['cells'][0]['candidates'][0])
    identity['evidence_kind'] = 'real_policy'
    episode = dict(identity, status='COMPLETE', task_success=True, task_predicate=True, actions_started=25, step_limit=50,
        official_step_limit=50, chunks=1, wall_seconds=.25, log_path='fixture.log', video_path='fixture.mp4', video_review_status='PENDING',
        requests=[dict(request_id=identity['request_id_prefix']+'-chunk-0001',chunk_index=1,noise_seed=777)])
    runner.SerialEvaluator._validate_episode(episode, identity)
    print('PENDING_VIDEO_RUNNER', 'accepted')
    try:
        aggregate.aggregate_records([episode], template, 'a'*64, 'fixture-review')
    except ValueError as error:
        print('PENDING_VIDEO_AGGREGATOR', str(error))
    episode['video_review_status'] = 'NOT_REVIEWED'
    journal = ledger.EvaluationLedger(root/'launder', {'evidence_kind':'fixture'})
    journal.initialize(resume=False)
    journal.begin(identity)
    journal.finish(identity['episode_id'], dict(identity, terminal_status='COMPLETE_POLICY', episode=episode))
    _, audit = aggregate.aggregate_records(journal.started_records()+journal.terminal_records(), template, 'a'*64, 'fixture-review')
    print('FIXTURE_RUN_CONFIG_REAL_RECORDS_COUNTED', audit['real_policy_episodes'])
