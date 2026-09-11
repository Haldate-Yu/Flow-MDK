"""Zero-increment persistence baseline: U_{t+1} = U_t.

The cheapest reference for metric calibration (CSI / RMSE floors) and for
sanity-checking the evaluation harness: a trained surrogate must beat it.
Has no trainable parameters.
"""

from __future__ import annotations

import torch

from flow_mdk.config import ModelConfig
from flow_mdk.models.base import AutoregressiveSurrogate

__all__ = ["PersistenceSurrogate"]


class PersistenceSurrogate(AutoregressiveSurrogate):
    output_mask_enabled = False  # pure identity reference: no output masking

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg

    def forward(
        self,
        node_static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        n = dyn_flat.size(0)
        return torch.zeros(
            n, self.cfg.num_dynamic_vars, device=dyn_flat.device, dtype=dyn_flat.dtype
        )
