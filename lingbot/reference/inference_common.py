import hashlib
import json
import math
import os
import gc
from types import SimpleNamespace
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np
import torch
import yaml
from safetensors import safe_open
from safetensors.torch import save_file, load_file
from peft import LoraConfig, inject_adapter_in_model, get_peft_model_state_dict, set_peft_model_state_dict
from transformers import AutoConfig, AutoProcessor
from transformers.modeling_utils import no_init_weights
ROOT = Path('/path/to/lingbot-workspace')
REPO = ROOT / 'lingbot-vla-v2'
sys.path.insert(0, str(REPO))
from lingbotvla.models.module_utils import init_empty_weights, load_model_weights
from lingbotvla.models.vla.vision_models.module_utils import build_depth_model, build_video_model, get_depth_target, get_video_target
from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy
from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
from lingbotvla.models.vla.lingbot_vla.qwen2_action_expert import apply_lingbot_qwen2_patch
PIN = 'be969b8fd117fb70550c5d4bf4bc328211b5b1b6'
BASE = ROOT / 'models/lingbot-vla-v2-6b-base'
QWEN = ROOT / 'models/Qwen3-VL-4B-Instruct-assets'
INPUT = ROOT / 'data-preparation/clean50-conversion'
DATA_PIN = '981c92aa34d8f94d4cff47e0d5bc2f7d4e0af042'
ARM = list(range(6)) + list(range(7, 13))
GRIP = [6, 13]
ACTIVE = list(range(12)) + [28, 29]
OUT = Path(os.environ['LINGBOT_PROBE_OUT'])
REPORT = OUT / 'report.json'
SOURCE = REPO / 'lingbotvla/models/vla/lingbot_vla/modeling_lingbot_vla_v2.py'

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def to_cpu(value):
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: to_cpu(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_cpu(v) for v in value]
    if isinstance(value, tuple):
        return tuple((to_cpu(v) for v in value))
    return value

def equal_tree(left, right):
    if torch.is_tensor(left):
        return torch.equal(left, right)
    if isinstance(left, dict):
        return left.keys() == right.keys() and all((equal_tree(left[k], right[k]) for k in left))
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all((equal_tree(a, b) for a, b in zip(left, right)))
    return left == right

def resolve_numbers(value):
    if isinstance(value, dict):
        return {k: resolve_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_numbers(v) for v in value]
    if isinstance(value, str) and re.fullmatch('[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)[eE][+-]?\\d+', value):
        result = float(value)
        check(math.isfinite(result), 'Nonfinite numeric configuration')
        return result
    return value

def prepare_dataset():
    from lingbotvla.data import build_vla_dataset, VLADataCollatorWithPacking
    from lingbotvla.data.vla_data.multi_vla_dataset import MultiVLADataset
    corpus_file = INPUT / 'corpus-report.json'
    corpus = json.loads(corpus_file.read_text())
    loader_report = json.loads((ROOT / 'data-preparation/clean50-loader-check/report.json').read_text())
    check(corpus['status'] == loader_report['status'] == 'PASS', 'Completed corpus or loader check did not pass')
    check(corpus['source_revision'] == DATA_PIN and corpus['task_count'] == 50 and (corpus['episodes'] == 2500) and (corpus['training_pairs'] == 549787) and (not corpus['randomized_training_data']), 'Clean50 corpus scope mismatch')
    check(sha(corpus_file) == loader_report['corpus_report_sha256'], 'Corpus report changed since loader QA')
    manifest, norm, robot_path = map(Path, (corpus['training_manifest'], corpus['norm_stats'], corpus['robot_config']))
    check(sha(manifest) == corpus['training_manifest_sha256'] == loader_report['training_manifest_sha256'], 'Training manifest changed')
    check(sha(norm) == corpus['norm_stats_sha256'] == loader_report['norm_stats_sha256'], 'Full-corpus normalization changed')
    check(Path(yaml.safe_load(robot_path.read_text())['norm_stats']) == norm, 'Robot config uses wrong normalization')
    stats_payload = json.loads(norm.read_text())
    check(stats_payload['count'] == 549787 and stats_payload['source_revision'] == DATA_PIN, 'Normalization scope mismatch')
    stats = stats_payload['norm_stats']
    template = yaml.safe_load((REPO / 'configs/vla/robotwin/robotwin.yaml').read_text())
    settings = resolve_numbers({**template['model'], **template['train']})
    teacher_dir = ROOT / 'data-preparation/teacher-target-check'
    teacher_report = json.loads((teacher_dir / 'report.json').read_text())
    align = json.loads((teacher_dir / 'teacher-config.json').read_text())
    check(teacher_report['status'] == 'PASS' and align == teacher_report['teacher_config'], 'Validated teacher configuration changed')
    reference = json.loads(json.dumps(template['train']['align_params']))
    for section, key in (('depth', 'moge_path'), ('depth', 'morgbd_path'), ('video', 'ckpt_path'), ('video', 'config_path')):
        reference[section][key] = align[section][key]
        check(Path(align[section][key]).is_file(), 'Missing teacher file: ' + align[section][key])
    check(reference == align, 'Teacher recipe differs beyond local paths')
    settings['align_params'] = align
    settings.update(moe_implementation='fused', tokenizer_path=str(QWEN), use_compile=False, return_image_grid_thw=True, use_cache=False, enable_gradient_checkpointing=False, attention_implementation='eager')
    data_settings = dict(template['data'])
    for key in ('joints', 'norm_type'):
        data_settings[key] = [v if isinstance(v, str) else repr(v) for v in data_settings[key]]
    data_settings.update(data_name='multi', train_path=str(manifest), robot_config_root=str(robot_path.parent), chunk_size=50, prompt_type='task', img_size=256, image_augment=False, use_future_image=True, num_workers=0)
    config = LingbotVLAV2Config(**settings)
    for key, value in settings.items():
        if not hasattr(config, key):
            setattr(config, key, value)
    processor = AutoProcessor.from_pretrained(str(QWEN), padding_side='right', local_files_only=True)
    print('Building actual 50-task MultiVLADataset with full-corpus normalization ...', flush=True)
    training = build_vla_dataset(dataset_config=SimpleNamespace(**data_settings), model_config=SimpleNamespace(tokenizer_path=str(QWEN)), config=config, processor=processor, do_nomalize=True, return_item=False, disabled_image_features=False, use_depth_align=True)
    check(isinstance(training, MultiVLADataset) and len(training._datasets) == 50 and (len(training) == 549787) and (training.num_episodes == 2500), 'Actual loader count mismatch')
    check(training.data_names == ['robotwin'] * 50 and list(training.repo_ids) == [v['dataset'] for v in corpus['tasks']], 'Manifest order or embodiment changed')
    collator = VLADataCollatorWithPacking()
    expected_mask = torch.zeros(55, dtype=torch.bool)
    expected_mask[ACTIVE] = True
    for entry in corpus['tasks']:
        check(sha(Path(entry['dataset']) / 'conversion-report.json') == entry['report_sha256'], 'Conversion provenance changed: ' + entry['task'])
    check(all((not any(child.feature_transform.action_subtract_state.values()) for child in training._datasets)), 'Expected absolute-action mapping')
    print('All 50 converted tasks / 2500 episodes / full clean50 normalization: PASS', flush=True)
    return (settings, training, align, corpus, manifest, norm, data_settings)

def validate_target(name, value, batch_size):
    check(torch.is_tensor(value) and value.shape == (batch_size, 256, 1024), 'Wrong teacher target shape: ' + name)
    check(value.dtype == torch.bfloat16 and (not value.requires_grad) and torch.isfinite(value).all().item(), 'Invalid teacher target: ' + name)
    return value.detach()

def teacher_targets(batch, moge, depth, video, align, device):
    current = batch['pil_images'].to(device)
    future = batch['future_pil_images'].to(device)
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        now, _ = get_depth_target('MoRGBD', (moge, depth), current)
        later, _ = get_depth_target('MoRGBD', (moge, depth), future)
        bundle = get_video_target(video, current, future, align['video'])
    check(isinstance(bundle, dict) and bundle.get('cls') is None, 'Unexpected video teacher bundle')
    values = {'depth_targets': now, 'future_depth_targets': later, 'future_video_targets': bundle['patch'], 'future_video_current_patch': bundle['current_patch']}
    return {key: validate_target(key, value, batch['pil_images'].shape[0]) for key, value in values.items()}

def build_inference_policy(settings, out):
    numeric_fields = ('router_z_loss_coeff', 'sequence_wise_loss_coeff', 'bias_update_speed', 'lr', 'lr_min')
    shapes = {}
    shards = sorted(BASE.glob('model-*.safetensors'))
    check(len(shards) == 6, 'Expected six checkpoint shards')
    for shard in shards:
        with safe_open(str(shard), framework='pt', device='cpu') as handle:
            for key in handle.keys():
                check(key not in shapes, 'Duplicate checkpoint key: ' + key)
                shapes[key] = tuple(handle.get_slice(key).get_shape())
    fused = any((re.search('\\.mlp\\.experts\\.(gate|up|down)_proj$', key) for key in shapes))
    settings.update(tokenizer_path=str(QWEN), attention_implementation='eager', moe_implementation='fused' if fused else 'eager', use_cache=False, use_compile=False, return_image_grid_thw=True, enable_gradient_checkpointing=False)
    config = LingbotVLAV2Config(**settings)
    for key, value in settings.items():
        if not hasattr(config, key):
            setattr(config, key, value)
    config.use_cache = False
    config.use_compile = False
    for key in numeric_fields:
        if key in settings:
            check(isinstance(getattr(config, key), (int, float)), f'Non-numeric model setting: {key}')
    print(f'MoE loss coefficients: router_z={config.router_z_loss_coeff:g}, sequence_wise={config.sequence_wise_loss_coeff:g} (numeric): PASS', flush=True)
    qwen = AutoConfig.from_pretrained(str(QWEN), local_files_only=True)
    config.vocab_size = qwen.text_config.vocab_size
    config.vision_config = qwen.vision_config
    check(config.loss_type in ('fm', 'L1_fm'), 'Unsupported diagnostic loss type')
    apply_lingbot_qwen3_vl_patch()
    apply_lingbot_qwen2_patch()
    with init_empty_weights(), no_init_weights():
        model = LingbotVlaV2Policy(config, eval=True)
    expected = {key: tuple(value.shape) for key, value in model.state_dict().items()}
    missing = sorted(expected.keys() - shapes.keys())
    extra = sorted(shapes.keys() - expected.keys())
    mismatch = [key for key in expected.keys() & shapes.keys() if expected[key] != shapes[key]]
    check(not (missing or extra or mismatch), f'Checkpoint mismatch: {missing[:5]}, {extra[:5]}, {mismatch[:5]}')
    print(f'Checkpoint names/shapes: PASS ({len(shapes)} tensors)', flush=True)
    check(torch.cuda.is_available(), 'CUDA unavailable')
    check(torch.cuda.device_count() == 1, 'Pilot must see only one GPU')
    gpu = 0
    torch.cuda.set_device(gpu)
    free_bytes, total_bytes = torch.cuda.mem_get_info(gpu)
    cap_bytes = min(52 * 1024 ** 3, free_bytes - 8 * 1024 ** 3)
    check(cap_bytes >= 40 * 1024 ** 3, f'Need at least 48 GiB currently free for this conservative FP32 probe; found {free_bytes / 1024 ** 3:.2f} GiB')
    torch.cuda.set_per_process_memory_fraction(cap_bytes / total_bytes, gpu)
    device = torch.device('cuda', gpu)
    print(f"Selected physical GPU {os.environ['LINGBOT_PHYSICAL_GPU']}; currently free {free_bytes / 1024 ** 3:.2f} GiB; allocator cap {cap_bytes / 1024 ** 3:.2f} GiB", flush=True)
    print('Cap is a limit, not a GPU reservation. Existing jobs remain running.', flush=True)
    torch.cuda.reset_peak_memory_stats()
    model = model.float()
    load_model_weights(model, str(BASE), init_device='cuda', post_training=True, adanorm_time=False)
    model.train()
    check(all((p.is_cuda and p.dtype == torch.float32 for p in model.parameters())), 'Wrong parameter placement/dtype')
    target_names = sorted((name for name, layer in model.named_modules() if re.fullmatch('model\\.qwenvl_with_expert\\.qwen_expert\\.model\\.layers\\.\\d+\\.self_attn\\.(q|k|v|o)_proj', name) and isinstance(layer, torch.nn.Linear)))
    check(len(target_names) == 144, f'Expected 36 x 4 attention projections; found {len(target_names)}')
    frozen_objects = list(model.named_parameters())
    frozen_versions = {name: parameter._version for name, parameter in frozen_objects}
    model.requires_grad_(False)
    torch.manual_seed(42)
    lora_config = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, bias='none', target_modules=target_names)
    model = inject_adapter_in_model(lora_config, model)
    model.train()
    trainable = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
    check(len(trainable) == 288 and all(('.lora_A.' in n or '.lora_B.' in n for n in trainable)), 'Unexpected trainable parameter selection')
    check(all((not p.requires_grad for _, p in frozen_objects)), 'Base parameters were unfrozen')
    trainable_count = sum((p.numel() for p in trainable.values()))
    print(f'LoRA: 144 action-attention modules, rank 8 / alpha 16; {trainable_count:,} trainable parameters', flush=True)
    print('Base and auxiliary heads frozen. Online teacher targets and full clean50 normalization.', flush=True)
    model.requires_grad_(False)
    model.eval()
    return (model, config, cap_bytes)
