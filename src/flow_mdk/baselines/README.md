# Baselines / 对比方法

Comparison architectures for the evaluation protocol (plan M5). All models
share the **same autoregressive harness** ([`flow_mdk/models/base.py`](../src/flow_mdk/models/base.py)):
encoder → processor → bias-free decoder with residual increment prediction
`U_{t+1} = U_t + Φ(·)`, identical datasets, losses, curriculum and metrics.
Only the **processor / propagation rule** differs — mirroring how the
SWE-GNN paper itself compared against GCN/GAT/CNN (its App. A).

| arch (`ModelConfig.arch`) | processor | dry-node guarantee | notes |
|---|---|---|---|
| `flow_mdk` | SWE-GNN difference messages + directed MDK operator splitting | yes | ours |
| `baseline_gcn` | `GCNConv` (symmetric normalization + self-loops), stacked input `X=(Xd, Xs)` | no | paper App. A1 protocol |
| `baseline_gat` | `GATConv` with edge features in attention | no | paper App. A2 protocol |
| `baseline_persistence` | none (`U_{t+1} = U_t`) | trivially | metric floor / harness sanity |
| U-Net (grid CNN) | conv encoder-decoder | no | **planned M5** (needs regular-grid reshaping, only for the 2D family) |

Configs: `configs/1d_baseline_gcn.yaml`, `configs/1d_baseline_gat.yaml`,
`configs/1d_baseline_persistence.yaml`. Train exactly like the main model:

```bash
python scripts/train.py --config configs/1d_baseline_gcn.yaml
python scripts/evaluate.py --config runs/1d_baseline_gcn/config.yaml \
    --checkpoint runs/1d_baseline_gcn/best.pt
```

The GCN/GAT node encoders carry bias (standard practice), so water can be
invented at dry cells — that is a *finding* the comparison quantifies, not a
bug. Flow-MDK keeps the bias-free dynamic path and the wet-gated diffusion
sub-graph.

## Official SWE-GNN repository comparison checklist

Official repo (from the paper's Code availability section):
<https://github.com/RBTV1/SWE-GNN-paper-repository-> (Zenodo:
10.5281/zenodo.10214840); raw datasets: 10.5281/zenodo.7764418.
**Verified against the local clone — full findings in
[`docs/swe_gnn_official_comparison.md`](../../../docs/swe_gnn_official_comparison.md):**

- [x] ψ message input composition (hs_i, hs_j, hd_i, hd_j, ε') and hidden widths (2G);
- [x] ψ output normalization (L2 along embedding dim; their NaN-fill ≈ our eps);
- [x] linear combine W placement (aggregate-then-linear) — and the key structural
      fact that the official layer runs **K=8 hops internally** with a per-hop
      weight matrix, on top of 2 outer layers (now supported via `hops_per_layer`);
- [x] activation after every layer (official code) vs Tanh only at the L-th layer
      (paper text) — both available via `hidden_activation`;
- [x] encoder/decoder bias handling (dynamic path bias-free) — plus the official
      trailing PReLU in every MLP (now matched by `make_mlp(activate_output=True)`);
- [x] GCN baseline propagation: the official repo contains **no GCN baseline code**
      (only ChebConv/TAGConv/GAT branches); the paper's `I − D^-1/2 A D^-1/2`
      formula stays unverifiable — our `baseline_gcn` uses standard Kipf normalization;
- [x] training recipe: Adam lr **0.007** in code (paper says 0.005), ×0.9 every 7
      epochs, 150 epochs, H=8, curriculum 15, γ=(1,3), previous_t=2 frames,
      gradient **value** clipping 0.5, RMSE loss on wet nodes only;
- [x] dataset generation: `nx.grid_2d_graph` DiGraph, edge features (length,
      normal), Delft3D-FM 30-min outputs subsampled, dry-bed padding, |q| = |v|·h;
- [x] static features (DEM + slopes + water level; area off in their config) and
      the water level recomputed inside the forward from DEM + latest depth.

Fixes applied to our implementation after the comparison: `hops_per_layer`,
inter-layer activation, trailing MLP activation, RMSE wet-only weighted loss,
official `_mask_small_WD` output masking, training hyper-parameters.
