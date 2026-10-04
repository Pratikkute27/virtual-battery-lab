"""Unit tests for single-cell physics."""
import numpy as np
import pytest

from model import cell
from model.parameters import CellParams

P = CellParams()


def test_voltage_at_zero_current_equals_ocv():
    for soc in (0.1, 0.5, 0.9):
        assert cell.terminal_voltage(soc, 0.0, 0.0, 25.0, P) == pytest.approx(float(cell.ocv(soc, P)))


def test_ocv_monotonic_and_bounded():
    v = cell.ocv(np.linspace(0, 1, 200), P)
    assert np.all(np.diff(v) >= 0)
    assert v[0] == pytest.approx(P.v_cut) and v[-1] == pytest.approx(P.v_max)


def test_arrhenius_is_one_at_reference_and_grows_when_cold():
    assert cell.arrhenius_factor(25.0, P) == pytest.approx(1.0)
    assert cell.arrhenius_factor(0.0, P) > 1.5
    assert cell.arrhenius_factor(-20.0, P) > cell.arrhenius_factor(0.0, P)


def test_dc_iv_slope_equals_r0_plus_r1():
    i = np.array([0.0, 10.0])
    v = cell.dc_voltage(i, 0.5, 25.0, P)
    assert (v[0] - v[1]) / 10.0 == pytest.approx(P.r0_ref + P.r1_ref)