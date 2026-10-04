"""Background worker: runs the simulation in a QThread so the GUI stays responsive."""
from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from model import CellParams, PackConfig, compute_metrics, run_discharge
from model.simulate import Mode


class SimWorker(QObject):
    """Runs one discharge simulation plus its metrics, then reports back via signals.

    Signals:
        progress(int): 0..100 percent while the simulation runs.
        finished(object, object): (SimResult, Metrics) when done.
        failed(str): error message if something goes wrong.
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, params: CellParams, pack: PackConfig, temp_c: float,
                 soc0: float, mode: Mode, value: float) -> None:
        super().__init__()
        self._args = (params, pack, temp_c, soc0, mode, value)

    @pyqtSlot()
    def run(self) -> None:
        """Entry point executed in the worker thread."""
        params, pack, temp_c, soc0, mode, value = self._args
        try:
            res = run_discharge(params, pack, temp_c, soc0, mode, value,
                                progress=lambda f: self.progress.emit(int(f * 100)))
            metrics = compute_metrics(params, pack, res, mode, value)
            self.progress.emit(100)
            self.finished.emit(res, metrics)
        except Exception as exc:  # report any error to the GUI instead of crashing
            self.failed.emit(str(exc))