"""Flow-MDK: hydraulics-directed Markov Diffusion Kernel GNN surrogates for shallow-water solvers.

The architecture follows SWE-GNN (Bentivoglio et al., HESS 2023):
encoder -> processor (difference-based "Riemann" messages) -> decoder with residual
increment prediction. The propagation is extended with a flow-directed Markov
Diffusion Kernel (MDK, after S2GC, Zhang et al., ICLR 2021) combined through
advection-diffusion operator splitting.
"""

__version__ = "0.1.0"
