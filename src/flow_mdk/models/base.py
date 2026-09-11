"""Autoregressive surrogate base class shared by Flow-MDK and all baselines.

The comparison protocol (SWE-GNN paper, App. A) keeps the encoder-decoder
structure and the autoregressive residual harness fixed, swapping only the
processor. This base class owns the shared harness:

- ``forward(node_static, dyn_flat, edge_index, edge_attr) -> delta [N, O]``
  (implemented by each architecture);
- ``step`` / ``rollout``: autoregressive prediction with the official
  small-depth output masking and optional depth clamping;
- the water level is refreshed as elevation + depth at every step.
"""

from __future__ import annotations

import torch
import torch.nn as nn

__all__ = ["AutoregressiveSurrogate", "apply_small_depth_mask"]


def apply_small_depth_mask(state: torch.Tensor, epsilon: float = 1e-3) -> torch.Tensor:
    """Official SWE-GNN ``_mask_small_WD``: zero sub-threshold depths and
    zero the discharge variables wherever the depth is exactly zero."""
    state = state.clone()
    depth = state[:, 0]
    state[:, 0][depth.abs() < epsilon] = 0
    state[:, 1:][state[:, 0] == 0] = 0
    return state


class AutoregressiveSurrogate(nn.Module):
    """Subclasses must set ``self.cfg`` and implement :meth:`forward`.

    Set the class attribute ``output_mask_enabled = False`` to opt out of
    the small-depth masking (the persistence reference does).
    """

    cfg: object  # ModelConfig-compatible
    output_mask_enabled = True

    def forward(
        self,
        node_static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    def _postprocess_state(self, new_state: torch.Tensor) -> torch.Tensor:
        cfg = self.cfg
        if getattr(cfg, "mask_small_depth", False) and self.output_mask_enabled:
            new_state = apply_small_depth_mask(new_state, cfg.small_depth_epsilon)
        if getattr(cfg, "clamp_depth", False):
            new_state = torch.cat(
                [new_state[:, :1].clamp_min(0.0), new_state[:, 1:]], dim=1
            )
        return new_state

    def step(
        self,
        node_static: torch.Tensor,
        dyn_seq: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        """One autoregressive step from a window [p+1, N, O]; returns [N, O]."""
        o = self.cfg.num_dynamic_vars
        p1 = dyn_seq.size(0)
        dyn_flat = dyn_seq.permute(1, 0, 2).reshape(dyn_seq.size(1), p1 * o)
        delta = self.forward(node_static, dyn_flat, edge_index, edge_attr)
        new_state = dyn_seq[-1] + delta
        return self._postprocess_state(new_state)

    def _refresh_static(
        self, node_static: torch.Tensor, new_state: torch.Tensor
    ) -> torch.Tensor:
        """Water-level static channel update: w = elevation + h."""
        static = node_static.clone()
        static[:, self.cfg.water_level_feature_idx] = (
            static[:, self.cfg.elevation_feature_idx] + new_state[:, 0]
        )
        return static

    def rollout(
        self,
        node_static: torch.Tensor,
        dyn_seq: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        n_steps: int,
    ) -> torch.Tensor:
        """Autoregressive multi-step prediction; returns [n_steps, N, O]."""
        window = dyn_seq.clone()
        static = node_static
        preds = []
        for _ in range(n_steps):
            new_state = self.step(static, window, edge_index, edge_attr)
            preds.append(new_state)
            static = self._refresh_static(static, new_state)
            window = torch.cat([window[1:], new_state.unsqueeze(0)], dim=0)
        return torch.stack(preds, dim=0)

    # diagnostics hook: only the Flow-MDK model reports MDK coefficients
    def mdk_lambda0(self) -> list[float]:
        return []
