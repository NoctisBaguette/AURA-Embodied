"""CPU stand-ins test runtime guard and real loader construction order, not CUDA."""
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import load_policy

class PrecisionContract(unittest.TestCase):
    def test_highest_is_applied_after_builder_and_final_cache_reset(self):
        tree=ast.parse(Path(load_policy.__file__).read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PortablePolicy')
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        calls=[n for n in ast.walk(init) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        precision=[n for n in calls if n.func.attr=='set_float32_matmul_precision']
        self.assertEqual(len(precision),1)
        self.assertEqual(ast.literal_eval(precision[0].args[0]),'highest')
        for name in ('build_inference_policy','clear_visual_cache'):
            self.assertLess(max(n.lineno for n in calls if n.func.attr==name),precision[0].lineno)
        self.assertIsInstance(init.body[-1],ast.Assign)
        self.assertEqual(init.body[-1].value.func.id,'require_inference_precision')

    def test_runtime_drift_is_rejected_before_input_decode(self):
        torch=types.ModuleType('torch')
        torch.backends=types.SimpleNamespace(cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=True)),cudnn=types.SimpleNamespace(allow_tf32=True))
        torch.get_float32_matmul_precision=lambda:'high'
        with patch.dict(sys.modules,torch=torch):
            policy=load_policy.PortablePolicy.__new__(load_policy.PortablePolicy)
            with self.assertRaisesRegex(ValueError,'Inference precision changed'):
                policy.predict(b'invalid packet must not be decoded',noise=None)
            torch.get_float32_matmul_precision=lambda:'highest'
            with self.assertRaisesRegex(ValueError,'Inference precision changed'):
                load_policy.require_inference_precision()
            torch.backends.cuda.matmul.allow_tf32=False
            self.assertTrue(load_policy.require_inference_precision()['cudnn_allow_tf32'])

if __name__=='__main__':unittest.main(verbosity=2)
