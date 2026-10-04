"""Time-domain discharge simulation (constant current or constant power)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

import numpy as np

from . import cell
from .parameters import CellParams, PackConfig

Mode = Literal["current", "power"]


@dataclass
class SimResult:
    """Pack-level time series and summary of one discharge run."""

    t: np.ndarray            # time [s]
    v_pack: np.ndarray       # pack terminal voltage [V]
    i_pack: np.ndarray       # pack current [A]
    p_pack: np.ndarray       # pack power [W]
    soc: np.ndarray          # state of charge [0..1]
    v1: np.ndarray           # RC voltage per cell [V]
    energy_wh: float         # delivered energy until stop [Wh]
    stop_reason: str         # "cutoff voltage" | "SoC empty" | "power limit" | "time limit"
    soc0: float
    temp_c: float


def run_discharge(
    params: CellParams,
    pack: PackConfig,
    temp_c: float,
    soc0: float,
    mode: Mode,
    value: float,
    dt: float = 1.0,
    t_max: float = 4 * 3600.0,
    progress: Optional[Callable[[float], None]] = None,
) -> SimResult:
    """Simulate a discharge until cutoff voltage, empty cell, power limit or t_max.

    Args:
        mode: "current" (value = pack current [A]) or "power" (value = pack power [W]).
        dt: fixed time step [s]; the RC update is exact, so any dt is stable.
        progress: optional callback receiving a 0..1 fraction (keeps model Qt-free).
    """
    if mode not in ("current", "power"):
        raise ValueError("mode must be 'current' or 'power'")
    if not 0.0 <= soc0 <= 1.0:
        raise ValueError("soc0 must be within 0..1")

    ns, npar = pack.n_series, pack.n_parallel
    q_as = params.capacity_ah * 3600.0
    r0_t, r1_t = cell.r0(temp_c, params), cell.r1(temp_c, params)
    decay = np.exp(-dt / params.tau_s)

    soc, v1, energy_ws, reason = soc0, 0.0, 0.0, "time limit"
    rec: list[tuple[float, float, float, float, float, float]] = []
    n_steps = int(t_max / dt)

    for k in range(n_steps):
        v_eq = float(cell.ocv(soc, params)) - v1
        if mode == "current":
            i_cell = value / npar
        else:
            p_cell = value / pack.n_cells
            disc = v_eq**2 - 4.0 * r0_t * p_cell
            if disc < 0.0:
                reason = "power limit"
                break
            i_cell = (v_eq - np.sqrt(disc)) / (2.0 * r0_t)

        v_cell = v_eq - i_cell * r0_t
        if v_cell <= params.v_cut:
            reason = "cutoff voltage"
            break

        i_pack, v_pack = i_cell * npar, v_cell * ns
        rec.append((k * dt, v_pack, i_pack, v_pack * i_pack, soc, v1))
        energy_ws += v_pack * i_pack * dt

        v1 = v1 * decay + r1_t * i_cell * (1.0 - decay)
        soc -= i_cell * dt / q_as
        if soc <= 0.0:
            reason = "SoC empty"
            break
        if progress is not None and k % 50 == 0:
            progress(k / n_steps)

    arr = np.array(rec) if rec else np.empty((0, 6))
    return SimResult(
        t=arr[:, 0], v_pack=arr[:, 1], i_pack=arr[:, 2], p_pack=arr[:, 3],
        soc=arr[:, 4], v1=arr[:, 5], energy_wh=energy_ws / 3600.0,
        stop_reason=reason, soc0=soc0, temp_c=temp_c,
    )