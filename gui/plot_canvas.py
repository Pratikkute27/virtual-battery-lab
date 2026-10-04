"""Matplotlib canvases embedded in the PyQt5 window."""
from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt5.QtWidgets import QWidget  # import first so matplotlib picks PyQt5
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from model.simulate import SimResult


class DischargeCanvas(FigureCanvasQTAgg):
    """Three stacked live plots: pack voltage, SoC and pack power versus time."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        fig = Figure(figsize=(6, 6), tight_layout=True)
        super().__init__(fig)
        self.setParent(parent)
        self.ax_v, self.ax_soc, self.ax_p = fig.subplots(3, 1, sharex=True)
        (self.line_v,) = self.ax_v.plot([], [], color="tab:blue")
        (self.line_soc,) = self.ax_soc.plot([], [], color="tab:green")
        (self.line_p,) = self.ax_p.plot([], [], color="tab:red")
        self.ax_v.set_ylabel("Pack voltage [V]")
        self.ax_soc.set_ylabel("SoC [%]")
        self.ax_p.set_ylabel("Power [kW]")
        self.ax_p.set_xlabel("Time [min]")
        for ax in (self.ax_v, self.ax_soc, self.ax_p):
            ax.grid(True, alpha=0.3)
        self._t = self._v = self._soc = self._p = np.empty(0)

    def set_result(self, res: SimResult) -> None:
        """Store a finished simulation and fix the axis limits to its full range."""
        self._t = res.t / 60.0
        self._v, self._soc, self._p = res.v_pack, res.soc * 100.0, res.p_pack / 1000.0
        if self._t.size == 0:
            self.clear()
            return
        self.ax_v.set_xlim(0, max(self._t[-1], 1e-3))
        for ax, y in ((self.ax_v, self._v), (self.ax_soc, self._soc), (self.ax_p, self._p)):
            lo, hi = float(np.min(y)), float(np.max(y))
            pad = 0.05 * (hi - lo) or 1.0
            ax.set_ylim(lo - pad, hi + pad)
        self.show_upto(self._t.size)

    def show_upto(self, n: int) -> None:
        """Draw only the first n samples (used for the live animation)."""
        n = max(0, min(n, self._t.size))
        self.line_v.set_data(self._t[:n], self._v[:n])
        self.line_soc.set_data(self._t[:n], self._soc[:n])
        self.line_p.set_data(self._t[:n], self._p[:n])
        self.draw_idle()

    def clear(self) -> None:
        """Remove all curves."""
        for line in (self.line_v, self.line_soc, self.line_p):
            line.set_data([], [])
        self.draw_idle()


class IVCanvas(FigureCanvasQTAgg):
    """Voltage-current sweep plus power curve, compared with 25 deg C."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(Figure(figsize=(6, 4), tight_layout=True))
        self.setParent(parent)

    def plot_iv(self, i_pack: np.ndarray, v_now: np.ndarray, v_ref: np.ndarray,
                p_now: np.ndarray, temp_c: float, ref_c: float, v_cut_pack: float) -> None:
        """Plot V-I at temp_c (solid), V-I at ref_c (dashed), power and cutoff voltage."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax2 = ax.twinx()
        ax.plot(i_pack, v_ref, "--", color="gray", label=f"V at {ref_c:.0f} °C")
        ax.plot(i_pack, v_now, color="tab:blue", label=f"V at {temp_c:.0f} °C")
        ax.axhline(v_cut_pack, color="k", linestyle=":", label="Cutoff voltage")
        ax.axhspan(0, v_cut_pack, color="gray", alpha=0.12)
        ax2.plot(i_pack, p_now / 1000.0, color="tab:red", label=f"Power at {temp_c:.0f} °C")
        ax.set_xlabel("Pack current [A]")
        ax.set_ylabel("Terminal voltage [V]")
        ax2.set_ylabel("Power [kW]", color="tab:red")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
        ax.set_title("I-V sweep (steady state)")
        self.draw_idle()