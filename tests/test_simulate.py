"""Integration tests for the discharge simulation and metrics."""
import numpy as np
import pytest

from model import CellParams, PackConfig, compute_metrics, max_power_pack, run_discharge

P, PACK = CellParams(), PackConfig(n_series=4, n_parallel=2)


def test_soc_decreases_monotonically():
    r = run_discharge(P, PACK, 25.0, 1.0, "current", 10.0)
    assert np.all(np.diff(r.soc) < 0)


def test_cold_delivers_less_energy_at_high_load():
    warm = run_discharge(P, PACK, 25.0, 1.0, "current", 60.0)
    cold = run_discharge(P, PACK, -10.0, 1.0, "current", 60.0)
    assert cold.energy_wh < warm.energy_wh
    assert cold.stop_reason == "cutoff voltage"


def test_low_current_energy_close_to_nominal():
    r = run_discharge(P, PACK, 25.0, 1.0, "current", 5.0)  # ~0.25C per cell
    nominal = P.capacity_ah * PACK.n_parallel * 3.7 * PACK.n_series
    assert 0.85 * nominal < r.energy_wh < 1.1 * nominal


def test_constant_power_infeasible_reports_power_limit():
    r = run_discharge(P, PACK, -20.0, 0.2, "power", 1e6)
    assert r.stop_reason == "power limit" and r.t.size == 0


def test_max_power_drops_when_cold():
    assert max_power_pack(P, PACK, -10.0, 0.8) < max_power_pack(P, PACK, 25.0, 0.8)


def test_metrics_zero_loss_at_reference_temperature():
    r = run_discharge(P, PACK, 25.0, 1.0, "current", 20.0)
    m = compute_metrics(P, PACK, r, "current", 20.0)
    assert m.energy_loss_pct == pytest.approx(0.0, abs=1e-9)