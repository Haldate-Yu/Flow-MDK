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

__all__ = ["multistep_rollout_loss", "interface_flux_penalty"]

# absolute floor (m3/s) in the relative-residual normalisation so all-dry
# interface steps contribute ~0 instead of blowing up
CONS_EPS = 1.0


def interface_flux_penalty(state: torch.Tensor, iface: dict) -> torch.Tensor:
    """Relative flux-continuity residual across chain->mesh interfaces.

    ``state`` is a post-mask rollout state [B, N, O] (channel 1 = Q on 1D
    nodes, |q| on 2D nodes). The iface node indices are LOCAL per item, and
    indexing ``state[:, idx, ...]`` already resolves them per batch item, so
    no node-offset bookkeeping is needed here. The penalty ties the model's
    own 1D-side discharge to its own 2D-side flux field,

        pen = mean |Q_a - sum_v |q|_v * ell| / (|Q_a + flux| / 2 + eps),

    a self-consistency constraint (predictions on both sides, not truth):
    ell is only calibrated from the truth so the constraint does not bias
    the model off the truth manifold.
    """
    a_idx, a_mask = iface["a_idx"], iface["a_mask"]
    b_idx, b_mask, ell = iface["b_idx"], iface["b_mask"], iface["ell"]
    q_a = (state[:, a_idx, 1] * a_mask).sum(dim=-1)  # [B, K]
    flux = (state[:, b_idx, 1].abs() * b_mask * ell[None, :, None]).sum(dim=-1)
    scale = 0.5 * (q_a.abs() + flux) + CONS_EPS
    return ((q_a - flux).abs() / scale).mean()


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
    iface: dict | None = None,
    iface_weight: float = 0.0,
) -> tuple[torch.Tensor, int]:
    """Recursive multistep loss over a flattened batch.

    With ``iface_weight > 0`` and a coupled batch (``iface`` bookkeeping from
    FlowDataset), the interface flux-continuity penalty is added to every
    rollout step's data loss before averaging.

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
    iface_total = torch.zeros((), device=static.device)
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
        if iface is not None and iface_weight:
            iface_total = iface_total + interface_flux_penalty(new_state, iface)
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

    loss = (total + iface_weight * iface_total) / max(steps, 1)
    return loss, steps
