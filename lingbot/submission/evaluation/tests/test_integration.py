"""CPU cross-boundary tests; no genuine model, GPU, or simulator execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from support import EVALUATION, TEMPLATE_PATH
import evaluate
from evaluate import SerialEvaluator, SubprocessBackend, build_plan


class IntegrationTests(unittest.TestCase):
    def test_canonical_manifest_identity_and_ambiguous_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value = dict(format='lingbot-portable-v2', files={'test-only': {'bytes': 1, 'sha256': 'a' * 64}})
            payload = (json.dumps(value) + '\n').encode()
            (root / 'package-manifest.json').write_bytes(payload)
            self.assertEqual(evaluate._manifest_sha(root), hashlib.sha256(payload).hexdigest())
            # Identity is not completeness: production verifier must reject this fake package.
            with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                evaluate._portable_contract().verify_package(root)
            (root / 'manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                evaluate._manifest_sha(root)

    def test_portable_validator_blocks_backend_before_run_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root / 'package'; package.mkdir()
            (package / 'package-manifest.json').write_text(json.dumps(dict(format='lingbot-portable-v2', files={'missing': {'bytes':1,'sha256':'a'*64}})))
            plan = build_plan(tasks=evaluate.load_tasks(TEMPLATE_PATH), selected_tasks=['lift_pot'], setting='clean', episodes=1, max_candidates=1, seed_start=100000, manifest_sha256=evaluate._manifest_sha(package), stage='candidate', output_dir=root/'run')
            runner = SerialEvaluator(plan=plan, output_dir=root/'run', policy_package=str(package), backend_command=['never-run'], episode_timeout_seconds=10,cell_timeout_seconds=20,stage_timeout_seconds=30)
            with patch.object(runner.backend, 'evaluate') as backend:
                with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                    runner.run(resume=False)
                backend.assert_not_called()
            self.assertFalse((root/'run'/'run-config.json').exists())

    def test_invalid_empty_and_duplicate_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for payload in ('{}','{"format":"lingbot-portable-v2","files":{}}','{"format":"lingbot-portable-v2","files":{},"files":{"x":{}}}'):
                with self.subTest(payload=payload):
                    (root/'package-manifest.json').write_text(payload)
                    with self.assertRaises(ValueError): evaluate._manifest_sha(root)

    def test_completed_actions_cannot_be_setup_rejection(self):
        valid=dict(rejection_category='EXPERT_UNSOLVED',rejection_evidence=dict(plan_success=False,init_scene=True))
        self.assertEqual(SerialEvaluator._valid_rejection(valid)[0],'EXPERT_UNSOLVED')
        for values in ({'actions_started':1},{'chunks':1},{'actions_started':False},{'requests':[{'chunk_index':1}]},{'task_success':False}):
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError,'setup rejection contains'):
                    SerialEvaluator._valid_rejection(dict(valid,**values))

    def test_runner_wall_is_independent_of_backend_episode_wall(self):
        result=SerialEvaluator._execution_evidence(dict(wall_seconds=1.0),123.0,'fixture')
        self.assertEqual((result['wall_seconds'],result['runner_wall_seconds']),(1.0,123.0))

    def test_utf8_transport_under_ascii_locale(self):
        with tempfile.TemporaryDirectory() as tmp:
            child="import sys,json; v=json.loads(sys.stdin.buffer.read().decode('utf-8')); sys.stdout.buffer.write(json.dumps(v,ensure_ascii=False).encode('utf-8'))"
            code="import sys,json; sys.path.insert(0,sys.argv[1]); from evaluate import SubprocessBackend; v=SubprocessBackend([sys.executable,'-c',sys.argv[3]]).evaluate(dict(output_dir=sys.argv[2],label='\\u4e2d\\u6587'),2); assert v['label']=='\\u4e2d\\u6587'; print('UTF8_PASS')"
            env={**os.environ,'PYTHONUTF8':'0','PYTHONCOERCECLOCALE':'0','LC_ALL':'C','LANG':'C'}
            result=subprocess.run([sys.executable,'-B','-c',code,str(EVALUATION),tmp,child],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('UTF8_PASS',result.stdout)

    def test_cli_propagates_backend_failure_after_mocked_cpu_package_gate(self):
        # This isolates CLI failure propagation; it is not a valid real package or GPU test.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package=root/'package';package.mkdir()
            (package/'package-manifest.json').write_text(json.dumps(dict(format='lingbot-portable-v2',files={'fixture':{}})))
            digest=evaluate._manifest_sha(package)
            actual=evaluate._portable_contract()
            with patch.object(actual,'verify_package',return_value=dict(manifest_sha256=digest)), patch.object(evaluate,'_portable_contract',return_value=actual):
                args=['--policy-package',str(package),'--task','lift_pot','--setting','clean','--episodes','1','--max-candidates','1','--output',str(root/'run'),'--backend-executable',sys.executable,'--backend-arg',str(EVALUATION/'tests/fake_backend.py'),'--backend-arg','fatal','--backend-arg',str(root/'count')]
                self.assertEqual(evaluate.main(args),1)
            report=json.loads((root/'run/evaluation-report.json').read_text())
            self.assertEqual(report['errors'][0]['kind'],'PLANNER_ERROR')

if __name__=='__main__': unittest.main(verbosity=2)
