"""Explicit FP32 inference entry point for zero-padded action slots.

For an unused action whose training endpoint is zero, flow matching has
x(t) = t * initial_noise and velocity = initial_noise. This helper only
replaces that unused velocity; active joint outputs are never clamped.
It leaves installed package source and training forward calls unchanged.
"""
from contextlib import contextmanager

import torch

VERSION = "zero-padding-fp32-v1"


def _check(value, message):
    if not value:
        raise ValueError(message)


@contextmanager
def _velocity_scope(core, initial_noise, active):
    _check(not getattr(core, "_zero_padding_call_active", False),
           "Concurrent or nested zero-padding sampling on the same core is unsupported")
    had_instance = "predict_velocity" in core.__dict__
    previous_instance = core.__dict__.get("predict_velocity")
    original = core.predict_velocity

    def velocity(*args, **kwargs):
        result = original(*args, **kwargs)
        _check(result.shape == initial_noise.shape and result.dtype == torch.float32,
               "Velocity shape or dtype changed")
        return torch.where(active, result, initial_noise)

    core._zero_padding_call_active = True
    core.predict_velocity = velocity
    try:
        yield
    finally:
        if had_instance:
            core.predict_velocity = previous_instance
        else:
            delattr(core, "predict_velocity")
        delattr(core, "_zero_padding_call_active")


def sample_actions(core, observation, *, action_joint_mask, noise):
    """Sample with an explicit active-joint mask and immutable caller noise.

    Scope: eager FP32 inference on zero-padded action coordinates. Compiled
    velocity bypasses are rejected. Supply noise explicitly for reproducible
    comparisons. The caller owns visual-cache scoping.
    """
    _check(not core.training, "The policy core must be in eval mode")
    _check(not getattr(core, "_use_compile_predict_velocity", False),
           "Compiled velocity bypass is unsupported")
    _check("noise" not in observation, "Pass initial noise only through the noise argument")
    state = observation.get("state")
    _check(torch.is_tensor(state) and state.ndim == 2 and state.dtype == torch.float32,
           "Expected batched FP32 state")
    expected = (state.shape[0], core.config.n_action_steps, core.config.max_action_dim)
    _check(torch.is_tensor(noise) and tuple(noise.shape) == expected and
           noise.dtype == torch.float32 and noise.device == state.device,
           "Initial noise has wrong shape, dtype or device")
    _check(torch.isfinite(noise).all().item(), "Initial noise contains nonfinite values")
    _check(torch.is_tensor(action_joint_mask) and action_joint_mask.dtype == torch.bool,
           "Supply an explicit boolean action_joint_mask")
    mask = action_joint_mask.to(state.device)
    if mask.ndim == 1:
        _check(tuple(mask.shape) == (expected[2],), "Action mask width differs")
        mask = mask.unsqueeze(0).expand(expected[0], -1)
    _check(tuple(mask.shape) == (expected[0], expected[2]) and mask.any(-1).all().item(),
           "Action mask has wrong batch shape or an empty active row")
    _check(not getattr(core, "_zero_padding_call_active", False),
           "Concurrent or nested zero-padding sampling on the same core is unsupported")
    # Installed sample_actions updates its x_t/noise argument in place.
    # Keep the analytic velocity constant separate from that mutable buffer.
    initial = noise.detach().clone()
    with torch.inference_mode(), _velocity_scope(core, initial, mask[:, None, :]):
        result = core.sample_actions(**observation, noise=initial.clone())
    _check(tuple(result.shape) == expected and torch.isfinite(result).all().item(),
           "Invalid sampled actions")
    return result
