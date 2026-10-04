"""Single-cell physics: OCV, Arrhenius resistance, terminal voltage."""
from __future__ import annotations

import numpy as np

from .parameters import CellParams

KELVIN = 273.15


def ocv(soc: float | np.ndarray, p: CellParams) -> float | np.ndarray:
    """Open-circuit voltage [V] by linear interpolation; SoC is clipped to 0..1."""
    return np.interp(np.clip(soc, 0.0, 1.0), p.soc_table, p.ocv_table)


def arrhenius_factor(temp_c: float, p: CellParams) -> float:
    """Resistance multiplier vs. the reference temperature (1.0 at T_ref, >1 when colder)."""
    t, t_ref = temp_c + KELVIN, p.t_ref_c + KELVIN
    return float(np.exp(p.ea_over_r * (1.0 / t - 1.0 / t_ref)))


def r0(temp_c: float, p: CellParams) -> float:
    """Ohmic resistance [ohm] at temperature."""
    return p.r0_ref * arrhenius_factor(temp_c, p)


def r1(temp_c: float, p: CellParams) -> float:
    """Polarisation resistance [ohm] at temperature."""
    return p.r1_ref * arrhenius_factor(temp_c, p)


def terminal_voltage(soc: float, v1: float, current: float, temp_c: float, p: CellParams) -> float:
    """Terminal voltage [V]: V = OCV(SoC) - I*R0(T) - V1 (discharge current > 0)."""
    return float(ocv(soc, p)) - current * r0(temp_c, p) - v1


def dc_voltage(current: np.ndarray, soc: float, temp_c: float, p: CellParams) -> np.ndarray:
    """Steady-state I-V curve: V = OCV - I*(R0 + R1), with V1 fully settled."""
    return float(ocv(soc, p)) - np.asarray(current) * (r0(temp_c, p) + r1(temp_c, p))