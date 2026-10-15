"""All-dry reference: predicted depth and discharge are identically zero.

The second no-skill reference of the forecast-verification protocol (besides
``persistence``): "predict nothing is flooded". Zero trainable parameters.
In the residual harness (``new_state = dyn_seq[-1] + delta``) it is the
delta-arm ``delta = -U_t``, so the rollout emits an all-zero field at every
step regardless of the input window.

Why it matters (Card 1): on sparse inundation fields the all-dry RMSE equals
``sqrt(E[h^2])`` over all cells and frames, which on the large domain
(0.84% wet fraction) can sit BELOW the persistence floor — i.e. the binding
no-skill floor is domain-dependent and must be reported, not assumed.
Like ``PersistenceSurrogate`` it opts out of the small-depth output mask so
the reference stays a pure, unmasked floor.
"""

from __future__ import annotations

import torch

from flow_mdk.config import ModelConfig
from flow_mdk.models.base import AutoregressiveSurrogate

__all__ = ["AlldrySurrogate"]


class AlldrySurrogate(AutoregressiveSurrogate):
    """All-dry reference: predicts an identically zero state at every step.

    In the residual harness (``new_state = dyn_seq[-1] + delta``) that is the
    delta-arm ``delta = -U_t``. Zero trainable parameters; opts out of the
    small-depth output mask so the reference stays a pure, unmasked floor
    (same convention as ``PersistenceSurrogate``).
    """

    output_mask_enabled = False  # pure reference: no output masking

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
        """Return the delta that zeroes the last frame: ``delta = -U_t``."""
        o = self.cfg.num_dynamic_vars
        return -dyn_flat[:, -o:]
