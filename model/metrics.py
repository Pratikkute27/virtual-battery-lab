"""Key result metrics: voltage sag, usable energy, max power, loss vs 25 deg C."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import cell
from .parameters import CellParams, PackConfig
from .simulate import Mode, SimResult, run_discharge


@dataclass
class Metrics:
    """Headline numbers shown in the GUI and exported to CSV."""

    voltage_sag_v: float      # max (OCV - terminal) over the run, pack level [V]
    usable_energy_wh: float   # pack energy until stop [Wh]
    max_power_w: float        # max available pack power at initial SoC [W]
    energy_ref_wh: float      # same run at the reference temperature [Wh]
    energy_loss_pct: float    # usable-energy loss vs reference [%]
    power_loss_pct: float     # max-power loss vs reference [%]
    stop_reason: str


def max_power_pack(params: CellParams, pack: PackConfig, temp_c: float, soc: float) -> float:
    """Maximum pack power [W] at the given SoC, respecting the cutoff voltage.

    P(I) = I*(V_eq - I*R0) peaks at I* = V_eq/(2*R0); current is also limited so
    the cell voltage never drops below v_cut.
    """
    v_eq, r = float(cell.ocv(soc, params)), cell.r0(temp_c, params)
    i_lim = max((v_eq - params.v_cut) / r, 0.0)
    i = min(v_eq / (2.0 * r), i_lim)
    return i * (v_eq - i * r) * pack.n_cells


def _sag(res: SimResult, params: CellParams, pack: PackConfig) -> float:
    if res.t.size == 0:
        return 0.0
    return float(np.max(cell.ocv(res.soc, params) * pack.n_series - res.v_pack))


def compute_metrics(
    params: CellParams, pack: PackConfig, res: SimResult, mode: Mode, value: float,
    dt: float = 1.0,
) -> Metrics:
    """Compute metrics for `res` and compare with a 25 deg C run of the same load."""
    ref = run_discharge(params, pack, params.t_ref_c, res.soc0, mode, value, dt=dt)
    p_now = max_power_pack(params, pack, res.temp_c, res.soc0)
    p_ref = max_power_pack(params, pack, params.t_ref_c, res.soc0)
    e_loss = 100.0 * (1.0 - res.energy_wh / ref.energy_wh) if ref.energy_wh > 0 else float("nan")
    return Metrics(
        voltage_sag_v=_sag(res, params, pack),
        usable_energy_wh=res.energy_wh,
        max_power_w=p_now,
        energy_ref_wh=ref.energy_wh,
        energy_loss_pct=e_loss,
        power_loss_pct=100.0 * (1.0 - p_now / p_ref),
        stop_reason=res.stop_reason,
    )