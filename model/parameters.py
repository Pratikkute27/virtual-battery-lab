"""Cell and pack parameters.

ALL VALUES ARE ILLUSTRATIVE, typical of a generic NMC 21700-style cell.
They are not measured data and not tied to any manufacturer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Illustrative NMC open-circuit voltage curve (SoC fraction -> volts)
SOC_TABLE = np.array([0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0])
OCV_TABLE = np.array([3.00, 3.30, 3.45, 3.56, 3.63, 3.69, 3.76, 3.85, 3.95, 4.05, 4.13, 4.20])


@dataclass(frozen=True)
class CellParams:
    """First-order Thevenin cell parameters (illustrative NMC values)."""

    capacity_ah: float = 5.0        # nominal capacity [Ah]
    r0_ref: float = 0.015           # ohmic resistance at T_ref [ohm]
    r1_ref: float = 0.010           # polarisation resistance at T_ref [ohm]
    tau_s: float = 30.0             # RC time constant [s], kept constant over T
    ea_over_r: float = 2500.0       # Arrhenius activation temperature Ea/R [K]
    t_ref_c: float = 25.0           # reference temperature [deg C]
    v_cut: float = 3.0              # discharge cutoff voltage [V]
    v_max: float = 4.2              # full-charge voltage [V]
    soc_table: np.ndarray = field(default_factory=lambda: SOC_TABLE.copy(), compare=False)
    ocv_table: np.ndarray = field(default_factory=lambda: OCV_TABLE.copy(), compare=False)


@dataclass(frozen=True)
class PackConfig:
    """Series/parallel pack layout."""

    n_series: int = 96
    n_parallel: int = 3

    @property
    def n_cells(self) -> int:
        return self.n_series * self.n_parallel