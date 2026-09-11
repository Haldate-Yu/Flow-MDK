"""Configuration dataclasses and YAML loading.

Every experiment is described by a :class:`ExperimentConfig`. Model-side options
carry the ablation switches required by the evaluation protocol:

- ``mdk.use`` off  -> pure SWE-GNN (ablation ``-MDK``);
- ``mdk.directed=False`` -> symmetric MDK = SSGC (ablation ``-定向性``);
- ``mdk.mixing == "diffusive-only"`` -> single-branch MDK (ablation ``-分裂``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class MDKConfig:
    """Flow-directed Markov Diffusion Kernel branch (S2GC / MDK propagation)."""

    use: bool = True
    # Number of Neumann/series truncation terms K. Should be matched to the
    # physical diffusion length sqrt(2*D*dt) over the mean edge length
    # (see flow_mdk.layers.mdk.suggest_num_steps).
    num_steps: int = 2
    # "geometric": w_m = lambda0 * (1 - lambda0)**m  (S2GC MDK, lambda0 = teleport);
    # "uniform":   w_m = 1 / (K + 1)                (plain truncated Neumann series).
    weighting: Literal["geometric", "uniform"] = "geometric"
    # lambda0 * I identity term coefficient: over-smoothing cap. In "geometric"
    # mode it doubles as the teleport probability.
    lambda0: float = 0.3
    learn_lambda: bool = True
    # Directed transition matrix (upstream -> downstream, discharge weighted) or
    # symmetric normalization (SSGC ablation).
    directed: bool = True
    # Which nodes may relay diffusion: "source" gates edges whose source node is
    # dry (dry nodes never transmit), "both" requires both endpoints wet.
    wet_gate: Literal["source", "both"] = "source"
    # Operator splitting mixing: "learned" gate alpha per channel, "fixed" uses
    # `alpha_value`, "diffusive-only" forces pure MDK branch (-分裂 ablation).
    mixing: Literal["learned", "fixed", "diffusive-only"] = "learned"
    alpha_value: float = 0.5
    # Edge weight source for the directed transition matrix: |q| of the endpoint
    # nodes ("discharge"), Froude-gated, or a constant ("uniform").
    edge_weight: Literal["discharge", "uniform"] = "discharge"
    # Temperature of the sigmoid direction gate built from the water-surface
    # gradient (see flow_mdk.layers.mdk.direction_gates).
    direction_beta: float = 1.0


@dataclass
class ModelConfig:
    # Architecture selector (see flow_mdk.models.factory): "flow_mdk" or a
    # "baseline_*" comparison model.
    arch: str = "flow_mdk"
    hidden_dim: int = 64
    num_message_passing_layers: int = 6  # L, matched to CFL receptive field
    # Message-passing hops *inside* each processor layer. The official
    # SWE-GNN code runs K=8 hops per layer with a per-hop weight matrix
    # (config.yaml: "K: 8") on top of 2 outer layers.
    hops_per_layer: int = 1
    # Activation between processor layers ("prelu" per the paper text; the
    # official code applies the final activation, Tanh, after every layer).
    hidden_activation: str = "prelu"
    num_previous_steps: int = 1  # p: dynamic window length is p + 1 frames
    num_dynamic_vars: int = 2  # O: (h, |q|) in 2D, (h, Q) in 1D
    # Index of the water-level channel inside the static feature vector and the
    # elevation channel it must be updated against during rollouts.
    water_level_feature_idx: int = -1
    elevation_feature_idx: int = 1
    # Depth above which a node counts as wet for the diffusion gating.
    wet_depth_threshold: float = 1e-3
    # Official SWE-GNN output masking (their _mask_small_WD): zero depths
    # below the epsilon and zero discharge wherever depth is exactly zero.
    mask_small_depth: bool = True
    small_depth_epsilon: float = 1e-3
    # Clamp predicted depth to >= 0 at every rollout step (extra safety not
    # present in the official code; off by default to stay faithful).
    clamp_depth: bool = False
    mdk: MDKConfig = field(default_factory=MDKConfig)


@dataclass
class TrainConfig:
    horizon_max: int = 8
    curriculum_steps: int = 15
    var_weights: tuple[float, ...] = (1.0, 3.0)  # gamma_o: depth, then discharge
    # Loss restricted to nodes where prediction or truth is non-zero
    # (official option only_where_water=True).
    only_where_water: bool = True
    # Official code values: lr 0.007 (paper text says 0.005), RMSE loss with
    # per-variable weights, gradient VALUE clipping at 0.5.
    lr: float = 0.007
    lr_decay: float = 0.9
    lr_step_epochs: int = 7
    max_epochs: int = 150
    early_stop_patience: int = 30
    batch_size: int = 8
    grad_clip_value: float = 0.5


@dataclass
class DataConfig:
    name: str = "1d_chain"
    root: str = "data/scenarios_1d"  # directory of scenario .npz files
    split: dict[str, list[str]] = field(default_factory=dict)  # explicit file stems
    train_frac: float = 0.6
    val_frac: float = 0.2
    seed: int = 0


@dataclass
class ExperimentConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    data: DataConfig = field(default_factory=DataConfig)
    seed: int = 0
    device: str = "auto"
    out_dir: str = "runs/default"


def _assign(obj: Any, payload: dict[str, Any]) -> Any:
    """Recursively merge a plain dict into a dataclass instance."""
    for key, value in payload.items():
        if not hasattr(obj, key):
            raise KeyError(f"Unknown config key '{key}' for {type(obj).__name__}")
        current = getattr(obj, key)
        if is_dataclass(current) and isinstance(value, dict):
            setattr(obj, key, _assign(current, value))
        elif is_dataclass(current) and isinstance(value, str):
            setattr(obj, key, _assign(type(current)(), yaml.safe_load(value)))
        else:
            current_field = {f.name: f for f in fields(obj)}[key]
            if current_field.type.startswith("tuple") and isinstance(value, list):
                value = tuple(value)
            setattr(obj, key, value)
    return obj


def load_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment config from YAML, merged over the defaults."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return _assign(ExperimentConfig(), raw)


def dump_config(config: ExperimentConfig, path: str | Path) -> None:
    """Serialize a config back to YAML (used to stamp run directories)."""

    def _to_dict(obj: Any) -> Any:
        if is_dataclass(obj):
            return {k: _to_dict(v) for k, v in vars(obj).items()}
        if isinstance(obj, tuple):
            return list(obj)
        if isinstance(obj, Path):
            return str(obj)
        return obj

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        yaml.safe_dump(_to_dict(config), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
