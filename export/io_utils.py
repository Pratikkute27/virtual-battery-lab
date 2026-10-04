"""CSV export of simulation results (no GUI code)."""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Union

from model import CellParams, Metrics, PackConfig, SimResult


def export_csv(path: Union[str, Path], res: SimResult, metrics: Metrics,
               params: CellParams, pack: PackConfig, mode: str, value: float) -> None:
    """Write settings and metrics as '#' comment lines, then the time series.

    Read it back with pandas: ``pd.read_csv(path, comment="#")``.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write("# Virtual Battery Lab export (illustrative NMC parameters)\n")
        f.write(f"# temperature_C={res.temp_c}, initial_SoC={res.soc0}, "
                f"mode={mode}, load_value={value} ({'A' if mode == 'current' else 'W'})\n")
        f.write(f"# series={pack.n_series}, parallel={pack.n_parallel}, "
                f"cell_capacity_Ah={params.capacity_ah}\n")
        for key, val in asdict(metrics).items():
            f.write(f"# {key}={val if isinstance(val, str) else round(val, 4)}\n")
        writer = csv.writer(f)
        writer.writerow(["time_s", "pack_voltage_V", "pack_current_A",
                         "pack_power_W", "soc", "v_rc_cell_V"])
        for row in zip(res.t, res.v_pack, res.i_pack, res.p_pack, res.soc, res.v1):
            writer.writerow([f"{x:.6g}" for x in row])