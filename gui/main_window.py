"""Main application window: controls, live plots, results readout and export."""
from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QMainWindow,
                             QProgressBar, QPushButton, QSlider, QSpinBox,
                             QTabWidget, QVBoxLayout, QWidget)

from export.io_utils import export_csv
from gui.plot_canvas import DischargeCanvas, IVCanvas
from gui.worker import SimWorker
from model import CellParams, Metrics, PackConfig, SimResult, cell


class MainWindow(QMainWindow):
    """Virtual Battery Lab: simulate a Li-ion pack at different temperatures and loads."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Virtual Battery Lab - cold-weather Li-ion pack simulator")
        self.resize(1250, 780)

        self.last_result: Optional[SimResult] = None
        self.last_metrics: Optional[Metrics] = None
        self.last_settings: Optional[tuple] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[SimWorker] = None
        self._anim_n = 0
        self._anim_step = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._build_ui()
        self._update_iv()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        left = QVBoxLayout()
        left.addWidget(self._build_load_group())
        left.addWidget(self._build_env_group())
        left.addWidget(self._build_pack_group())

        self.run_btn = QPushButton("Run simulation")
        self.run_btn.clicked.connect(self._start)
        self.progress = QProgressBar()
        left.addWidget(self.run_btn)
        left.addWidget(self.progress)

        self.csv_btn = QPushButton("Export CSV")
        self.png_btn = QPushButton("Save plots as PNG")
        self.csv_btn.setEnabled(False)
        self.png_btn.setEnabled(False)
        self.csv_btn.clicked.connect(self._export_csv)
        self.png_btn.clicked.connect(self._save_png)
        left.addWidget(self.csv_btn)
        left.addWidget(self.png_btn)

        left.addWidget(self._build_results_group())
        left.addStretch(1)

        self.tabs = QTabWidget()
        self.discharge_canvas = DischargeCanvas()
        self.iv_canvas = IVCanvas()
        self.tabs.addTab(self.discharge_canvas, "Discharge")
        self.tabs.addTab(self.iv_canvas, "I-V sweep")

        root.addLayout(left, 0)
        root.addWidget(self.tabs, 1)

    def _build_load_group(self) -> QGroupBox:
        box, form = QGroupBox("Load"), QFormLayout()
        self.mode_box = QComboBox()
        self.mode_box.addItems(["Constant current", "Constant power"])
        self.load_spin = QDoubleSpinBox()
        self.load_spin.setDecimals(1)
        self._set_load_range(0)
        self.mode_box.currentIndexChanged.connect(self._set_load_range)
        form.addRow("Mode", self.mode_box)
        form.addRow("Value", self.load_spin)
        box.setLayout(form)
        return box

    def _build_env_group(self) -> QGroupBox:
        box, form = QGroupBox("Environment"), QFormLayout()
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(-20, 40)
        self.temp_slider.setValue(0)
        self.temp_label = QLabel("0 °C")
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        self.soc_spin = QSpinBox()
        self.soc_spin.setRange(5, 100)
        self.soc_spin.setValue(100)
        self.soc_spin.setSuffix(" %")
        self.soc_spin.valueChanged.connect(lambda _: self._update_iv())
        form.addRow("Temperature", self.temp_slider)
        form.addRow("", self.temp_label)
        form.addRow("Initial SoC", self.soc_spin)
        box.setLayout(form)
        return box

    def _build_pack_group(self) -> QGroupBox:
        box, form = QGroupBox("Cell and pack"), QFormLayout()
        self.cap_spin = QDoubleSpinBox()
        self.cap_spin.setRange(1.0, 10.0)
        self.cap_spin.setValue(5.0)
        self.cap_spin.setSuffix(" Ah")
        self.ns_spin = QSpinBox()
        self.ns_spin.setRange(1, 200)
        self.ns_spin.setValue(96)
        self.np_spin = QSpinBox()
        self.np_spin.setRange(1, 20)
        self.np_spin.setValue(3)
        for spin in (self.cap_spin, self.ns_spin, self.np_spin):
            spin.valueChanged.connect(lambda _: self._update_iv())
        form.addRow("Cell capacity", self.cap_spin)
        form.addRow("Series cells", self.ns_spin)
        form.addRow("Parallel cells", self.np_spin)
        box.setLayout(form)
        return box

    def _build_results_group(self) -> QGroupBox:
        box, form = QGroupBox("Results"), QFormLayout()
        self.res_labels = {name: QLabel("-") for name in
                           ("Voltage sag", "Usable energy", "Peak power (pulse)",
                            "Energy loss vs 25 °C", "Power loss vs 25 °C", "Stopped by")}
        for name, label in self.res_labels.items():
            form.addRow(name, label)
        box.setLayout(form)
        return box

    # -------------------------------------------------------------- helpers
    def _set_load_range(self, index: int) -> None:
        """Switch the load box between amps and kilowatts."""
        if index == 0:
            self.load_spin.setRange(0.1, 1000.0)
            self.load_spin.setValue(30.0)
            self.load_spin.setSuffix(" A")
        else:
            self.load_spin.setRange(0.1, 500.0)
            self.load_spin.setValue(10.0)
            self.load_spin.setSuffix(" kW")

    def _on_temp_changed(self, value: int) -> None:
        self.temp_label.setText(f"{value} °C")
        self._update_iv()

    def _settings(self) -> tuple[CellParams, PackConfig, float, float, str, float]:
        """Read all controls and return the simulation arguments."""
        params = CellParams(capacity_ah=self.cap_spin.value())
        pack = PackConfig(self.ns_spin.value(), self.np_spin.value())
        temp_c = float(self.temp_slider.value())
        soc0 = self.soc_spin.value() / 100.0
        if self.mode_box.currentIndex() == 0:
            return params, pack, temp_c, soc0, "current", self.load_spin.value()
        return params, pack, temp_c, soc0, "power", self.load_spin.value() * 1000.0

    # ----------------------------------------------------------- I-V sweep
    def _update_iv(self) -> None:
        """Recompute the steady-state I-V and power curves (fast, no thread needed)."""
        params, pack, temp_c, soc0, _, _ = self._settings()
        r_ref = cell.r0(params.t_ref_c, params) + cell.r1(params.t_ref_c, params)
        i_cut_ref = (float(cell.ocv(soc0, params)) - params.v_cut) / r_ref
        i_cell = np.linspace(0.0, 1.3 * i_cut_ref, 200)
        v_now = np.maximum(cell.dc_voltage(i_cell, soc0, temp_c, params), 0.0) * pack.n_series
        v_ref = np.maximum(cell.dc_voltage(i_cell, soc0, params.t_ref_c, params), 0.0) * pack.n_series
        i_pack = i_cell * pack.n_parallel
        i_pack = i_cell * pack.n_parallel
        v_cut_pack = params.v_cut * pack.n_series
        p_usable = np.where(v_now >= v_cut_pack, v_now * i_pack, np.nan)
        self.iv_canvas.plot_iv(i_pack, v_now, v_ref, p_usable, temp_c,
                               params.t_ref_c, v_cut_pack)

    # ------------------------------------------------- threaded simulation
    def _start(self) -> None:
        """Start the simulation in a background QThread."""
        if self._thread is not None:
            return
        self.run_btn.setEnabled(False)
        self.progress.setValue(0)
        self._timer.stop()

        self.last_settings = self._settings()
        self._thread = QThread()
        self._worker = SimWorker(*self.last_settings)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread_done)
        self._thread.start()

    def _thread_done(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        if self._worker is not None:
            self._worker.deleteLater()
        self._thread, self._worker = None, None
        self.run_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self.res_labels["Stopped by"].setText(f"Error: {message}")

    def _on_finished(self, res: SimResult, metrics: Metrics) -> None:
        """Receive results from the worker, animate the plot, fill the readout."""
        self.last_result, self.last_metrics = res, metrics
        self.discharge_canvas.set_result(res)
        self.discharge_canvas.show_upto(0)
        self._anim_n, self._anim_step = 0, max(1, res.t.size // 80)
        self._timer.start(25)
        self._show_metrics(res, metrics)
        self.csv_btn.setEnabled(True)
        self.png_btn.setEnabled(True)

    def _tick(self) -> None:
        """Reveal the discharge curves step by step for a live effect."""
        assert self.last_result is not None
        self._anim_n += self._anim_step
        self.discharge_canvas.show_upto(self._anim_n)
        if self._anim_n >= self.last_result.t.size:
            self._timer.stop()

    def _show_metrics(self, res: SimResult, m: Metrics) -> None:
        lab = self.res_labels
        if res.t.size == 0:
            for name in list(lab)[:5]:
                lab[name].setText("-")
            lab["Stopped by"].setText(f"{m.stop_reason}: load cannot be delivered")
            return
        lab["Voltage sag"].setText(f"{m.voltage_sag_v:.1f} V")
        lab["Usable energy"].setText(f"{m.usable_energy_wh / 1000:.2f} kWh "
                                     f"(25 °C: {m.energy_ref_wh / 1000:.2f} kWh)")
        lab["Peak power (pulse)"].setText(f"{m.max_power_w / 1000:.1f} kW")
        lab["Energy loss vs 25 °C"].setText(f"{m.energy_loss_pct:.1f} %")
        lab["Power loss vs 25 °C"].setText(f"{m.power_loss_pct:.1f} %")
        lab["Stopped by"].setText(m.stop_reason)

    # -------------------------------------------------------------- export
    def _export_csv(self) -> None:
        """Ask for a file name and write the last result to CSV."""
        if self.last_result is None or self.last_metrics is None or self.last_settings is None:
            return
        params, pack, temp_c, _, mode, value = self.last_settings
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"battery_{temp_c:.0f}C.csv", "CSV file (*.csv)")
        if path:
            export_csv(path, self.last_result, self.last_metrics, params, pack, mode, value)
            self.statusBar().showMessage(f"Saved {path}", 5000)

    def _save_png(self) -> None:
        """Save the discharge plot and the I-V plot as two PNG files."""
        if self.last_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save plots as PNG", "battery_plots.png", "PNG image (*.png)")
        if not path:
            return
        base = path[:-4] if path.lower().endswith(".png") else path
        self.discharge_canvas.show_upto(self.last_result.t.size)
        self.discharge_canvas.figure.savefig(f"{base}_discharge.png", dpi=150)
        self.iv_canvas.figure.savefig(f"{base}_iv.png", dpi=150)
        self.statusBar().showMessage(f"Saved {base}_discharge.png and {base}_iv.png", 5000)