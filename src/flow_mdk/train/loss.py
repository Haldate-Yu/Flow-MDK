"""Recursive multistep loss, aligned with the official SWE-GNN training.

Per rollout step (official ``loss_WD``):

    mask   = nodes where prediction or truth is non-zero   (only_where_water)
    RMSE_o = sqrt(mean_nodes(diff_o^2))  over the masked nodes
    loss_t = sum_o  gamma_o * RMSE_o                        (weighted SUM)

and the multistep loss is the mean of ``loss_t`` over the H recursive steps
(the model's own predictions are fed back as inputs). ``gamma = (1, 3)``:
water depth, then discharge/unit-discharge.

The feedback state goes through the same output masking as the model
(``_mask_small_WD``: sub-threshold depths and discharge on dry nodes zeroed),
so training sees exactly the states that an autoregressive rollout sees.
"""

from __future__ import annotations

import torch

from flow_mdk.models.base import apply_small_depth_mask

__all__ = ["multistep_rollout_loss"]


def _step_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    weights: torch.Tensor,
    only_where_water: bool,
) -> torch.Tensor:
    diff = pred - target
    if only_where_water:
        mask = (pred != 0).any(dim=-1) | (target != 0).any(dim=-1)
        if mask.any():
            diff = diff[mask]
        # all-dry window: fall back to all nodes (loss is zero there anyway)
    rmse = torch.sqrt((diff**2).mean(dim=0))
    return torch.dot(rmse, weights)


def multistep_rollout_loss(
    model,  # flow_mdk.models.base.AutoregressiveSurrogate
    batch,  # flow_mdk.data.dataset.FlowBatch
    horizon: int,
    var_weights: tuple[float, ...] = (1.0, 3.0),
    only_where_water: bool = True,
) -> tuple[torch.Tensor, int]:
    """Recursive multistep loss over a flattened batch.

    Returns (loss, steps_actually_taken) — the horizon may exceed the
    available targets only if callers misconfigure, which we guard against.
    """
    b, n = len(batch.node_static_list), batch.num_nodes_per_item
    o = model.cfg.num_dynamic_vars
    weights = torch.tensor(var_weights, device=batch.targets.device, dtype=torch.float32)

    static = batch.node_static
    dyn_flat = batch.dyn_flat
    p1 = dyn_flat.size(1) // o

    targets = batch.targets[:, :horizon]  # [B, H, N, O]
    steps = targets.size(1)
    total = torch.zeros((), device=static.device)
    for tau in range(steps):
        delta = model.forward(static, dyn_flat, batch.edge_index, batch.edge_attr)
        new_state = delta.view(b, n, o) + dyn_flat.view(b, n, p1, o)[:, :, -1, :]
        flat_state = new_state.reshape(b * n, o)
        if getattr(model.cfg, "mask_small_depth", False) and model.output_mask_enabled:
            flat_state = apply_small_depth_mask(flat_state, model.cfg.small_depth_epsilon)
        if getattr(model.cfg, "clamp_depth", False):
            flat_state = torch.cat(
                [flat_state[:, :1].clamp_min(0.0), flat_state[:, 1:]], dim=1
            )
        new_state = flat_state.view(b, n, o)
        total = total + _step_loss(
            new_state, targets[:, tau], weights, only_where_water
        )

        # feedback: shift the window, refresh the water-level static channel
        window = dyn_flat.view(b, n, p1, o)
        dyn_flat = torch.cat([window[:, :, 1:, :], new_state[:, :, None, :]], dim=2)
        dyn_flat = dyn_flat.reshape(b * n, p1 * o).contiguous()
        w_new = static[:, model.cfg.elevation_feature_idx] + new_state[..., 0].reshape(b * n)
        static = static.clone()
        static[:, model.cfg.water_level_feature_idx] = w_new

    return total / max(steps, 1), steps
