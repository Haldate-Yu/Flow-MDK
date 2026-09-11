"""FlowMDKNet: the full autoregressive encoder-processor-decoder model.

Data flow for one model step (SWE-GNN Eq. 5 + MDK extension):

    U_{t+1} = U_t + Phi(X_s, U_{t-p:t}, E)

with Phi = decoder(processor(encoder(...))). Hydraulic tensors used by the
MDK diffusion branch are rebuilt at every call from the current state:

    wet_mask    = h > wet_depth_threshold
    edge_weight = discharge_weight (x direction gate from water levels)

so the diffusion sub-graph follows the moving wet/dry front step by step.

Conventions
-----------
- ``dynamic`` variable order: channel 0 = water depth h, channel 1 = |q| (2D)
  or Q (1D). The dynamic window is flattened oldest-to-newest:
  dyn_flat = [N, (p+1) * O].
- Static features end with the water level w = elevation + h (SWE-GNN keeps
  it among the "static" inputs because it is non-zero without water); during
  rollouts the channel ``water_level_feature_idx`` is refreshed as
  static[:, elev_idx] + h.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from flow_mdk.config import ModelConfig
from flow_mdk.layers.mdk import direction_gates, hydraulic_edge_weights
from flow_mdk.layers.splitting import HydraulicState
from flow_mdk.models.base import AutoregressiveSurrogate
from flow_mdk.models.decoder import Decoder
from flow_mdk.models.encoder import DynamicEncoder, EdgeEncoder, StaticEncoder
from flow_mdk.models.processor import HydraulicsProcessor

__all__ = ["FlowMDKNet"]


class FlowMDKNet(AutoregressiveSurrogate):
    def __init__(self, cfg: ModelConfig, num_static_features: int, num_edge_features: int):
        super().__init__()
        self.cfg = cfg
        g = cfg.hidden_dim
        p1 = cfg.num_previous_steps + 1
        self.static_encoder = StaticEncoder(num_static_features, g)
        self.dynamic_encoder = DynamicEncoder(cfg.num_dynamic_vars * p1, g)
        self.edge_encoder = EdgeEncoder(num_edge_features, g)
        self.processor = HydraulicsProcessor(cfg)
        self.decoder = Decoder(g, cfg.num_dynamic_vars)

    # ------------------------------------------------------------------ #
    # hydraulic bookkeeping
    # ------------------------------------------------------------------ #
    def _hydraulic_state(
        self,
        static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> HydraulicState:
        o = self.cfg.num_dynamic_vars
        last = dyn_flat.view(dyn_flat.size(0), -1, o)[:, -1, :]
        h, q = last[:, 0], last[:, 1]
        wet_mask = h > self.cfg.wet_depth_threshold
        weight = hydraulic_edge_weights(
            h, q, edge_index, mode=self.cfg.mdk.edge_weight
        )
        if self.cfg.mdk.directed:
            wse = static[:, self.cfg.elevation_feature_idx] + h
            weight = weight * direction_gates(
                wse, edge_index, beta=self.cfg.mdk.direction_beta
            )
        return HydraulicState(wet_mask=wet_mask, edge_weight=weight)

    # ------------------------------------------------------------------ #
    # one model step
    # ------------------------------------------------------------------ #
    def forward(
        self,
        node_static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        """Predict the hydraulic increment U_{t+1} - U_t for every node.

        Returns a tensor of shape [N, O]; the caller adds it to the last
        dynamic frame (residual prediction, SWE-GNN Eq. 5).
        """
        hyd = self._hydraulic_state(node_static, dyn_flat, edge_index)
        hs = self.static_encoder(node_static)
        hd = self.dynamic_encoder(dyn_flat)
        e_emb = self.edge_encoder(edge_attr)
        hd = self.processor(hs, hd, e_emb, edge_index, hyd)
        return self.decoder(hd)

    # ------------------------------------------------------------------ #
    # diagnostics
    # ------------------------------------------------------------------ #
    def mdk_lambda0(self) -> list[float]:
        """Current lambda0 of every MDK filter (over-smoothing monitoring)."""
        return [
            float(layer.mdk.lambda0.detach())
            for layer in self.processor.layers
            if getattr(layer, "mdk_cfg", None) is not None and layer.mdk_cfg.use
        ]

    def mixing_alpha(self) -> list[list[float]]:
        """Per-layer per-channel learned mixing gate alpha."""
        out = []
        for layer in self.processor.layers:
            if getattr(layer, "alpha_logit", None) is not None and isinstance(
                layer.alpha_logit, nn.Parameter
            ):
                out.append(torch.sigmoid(layer.alpha_logit).detach().tolist())
            else:
                out.append([])
        return out
