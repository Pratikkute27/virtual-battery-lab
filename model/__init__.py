"""Battery model package (no GUI code)."""
from .parameters import CellParams, PackConfig
from .simulate import SimResult, run_discharge
from .metrics import Metrics, compute_metrics, max_power_pack

__all__ = ["CellParams", "PackConfig", "SimResult", "run_discharge",
           "Metrics", "compute_metrics", "max_power_pack"]