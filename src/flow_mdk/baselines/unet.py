"""U-Net baseline (structured 2D grid domains): CNN processor in the shared
autoregressive residual harness.

SWE-GNN paper baseline set: a standard U-Net (Ronneberger et al., 2015) on
the structured cell grid replaces the message-passing processor while the
comparison protocol keeps everything else fixed — same inputs (stacked
dynamic window + static features), same increment output, same small-depth
output masking, same recursive multistep loss.

The graph pipeline feeds flat node tensors ``[B*N, C]``; this model reshapes
them to images ``[B, C, nx, ny]`` via the row-major grid layout
(node id = i * ny + j, ``data/graph_2d.build_2d_grid_graph``). ``edge_index``
/ ``edge_attr`` are ignored (connectivity is implicit in the convolution).

Harness parity note: the model-side static indices copy the values the 2D
control runs actually used (``elevation_feature_idx=0`` — inherited from the
pre-2026-09-22 1D base configs and kept verbatim in every 2d_*.yaml on this
branch, ``water_level_feature_idx=-1``), so the comparison stays
apples-to-apples with E4/E5 — even though the 2D layout keeps bed elevation
at column 1 and the refreshed water-level channel therefore carries
``area + h`` (a per-run constant offset of h on the uniform synthetic family)
from the second step on. All 2D arms share this behaviour; changing it here
would break comparability with every trained checkpoint.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from flow_mdk.config import ModelConfig
from flow_mdk.models.base import AutoregressiveSurrogate

__all__ = ["UNetSurrogate"]


def _conv_block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(8, cout),
        nn.PReLU(),
        nn.Conv2d(cout, cout, kernel_size=3, padding=1, bias=False),
        nn.GroupNorm(8, cout),
        nn.PReLU(),
    )


class UNetSurrogate(AutoregressiveSurrogate):
    """Channel-scaled U-Net: base width = ``cfg.hidden_dim``, two pool levels
    (64x64 -> 32x32 -> 16x16) with mirrored decoder and skip connections."""

    def __init__(self, cfg: ModelConfig, num_static_features: int, num_edge_features: int):
        super().__init__()
        self.cfg = cfg
        g = cfg.hidden_dim
        p1 = cfg.num_previous_steps + 1
        cin = cfg.num_dynamic_vars * p1 + num_static_features

        self.inc = _conv_block(cin, g)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), _conv_block(g, 2 * g))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), _conv_block(2 * g, 4 * g))
        self.up1_up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.up1_conv = _conv_block(4 * g + 2 * g, 2 * g)
        self.up2_up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.up2_conv = _conv_block(2 * g + g, g)
        self.outc = nn.Conv2d(g, cfg.num_dynamic_vars, kernel_size=1)

    def forward(
        self,
        node_static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        nx = self.cfg.unet_grid_nx
        ny = self.cfg.unet_grid_ny
        n = nx * ny
        if node_static.size(0) % n:
            raise ValueError(
                f"U-Net needs a multiple of the {nx}x{ny} grid ({n} nodes); "
                f"got {node_static.size(0)} — 2D grid domains only"
            )
        b = node_static.size(0) // n

        x = torch.cat([dyn_flat, node_static], dim=-1)
        x = x.view(b, nx, ny, -1).permute(0, 3, 1, 2)

        s1 = self.inc(x)          # [B, g, 64, 64]
        s2 = self.down1(s1)       # [B, 2g, 32, 32]
        x = self.down2(s2)        # [B, 4g, 16, 16]
        x = self.up1_conv(torch.cat([self.up1_up(x), s2], dim=1))
        x = self.up2_conv(torch.cat([self.up2_up(x), s1], dim=1))
        delta = self.outc(x)      # [B, O, 64, 64]

        return delta.permute(0, 2, 3, 1).reshape(b * n, -1)
