"""Builder extracted from retained inference_common.py e87f3036866274b4f5153d7a821059d3c237a288f2d17921a14824022172e5c8.
Only path binding and physical-GPU log label change. Model construction is preserved.
"""
import os
import re
from pathlib import Path
import torch
from safetensors import safe_open
from peft import LoraConfig, inject_adapter_in_model
from transformers import AutoConfig
from transformers.modeling_utils import no_init_weights
from lingbotvla.models.module_utils import init_empty_weights, load_model_weights
from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy
from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
from lingbotvla.models.vla.lingbot_vla.qwen2_action_expert import apply_lingbot_qwen2_patch
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'base'
QWEN=ROOT/'qwen'

def check(condition,message):
    if not condition: raise ValueError(message)

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
    print(f"Selected physical GPU {os.environ['CUDA_VISIBLE_DEVICES']}; currently free {free_bytes / 1024 ** 3:.2f} GiB; allocator cap {cap_bytes / 1024 ** 3:.2f} GiB", flush=True)
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
