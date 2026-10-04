"""Test that CSV export writes a readable file."""
import csv

from export.io_utils import export_csv
from model import CellParams, PackConfig, compute_metrics, run_discharge


def test_csv_has_header_and_one_row_per_sample(tmp_path):
    p, k = CellParams(), PackConfig(4, 2)
    res = run_discharge(p, k, 0.0, 1.0, "current", 20.0)
    metrics = compute_metrics(p, k, res, "current", 20.0)
    out = tmp_path / "result.csv"
    export_csv(out, res, metrics, p, k, "current", 20.0)

    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    rows = list(csv.reader(lines))
    assert rows[0][0] == "time_s"
    assert len(rows) - 1 == res.t.size