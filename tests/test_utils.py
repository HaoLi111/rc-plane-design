"""Tests for rc_aircraft_design.utils (math_helpers)."""

import numpy as np
import pytest

from rc_aircraft_design.utils import (
    sind, cosd, tand, asind, acosd, atand,
    temperature_isa, pressure_isa, density_isa, dynamic_pressure,
    reynolds, skin_friction_turbulent,
    interp1d, arc_length, euclidean,
)


# -- Trig helpers -----------------------------------------------------------

class TestTrigDegrees:
    def test_sind_zero(self):
        assert sind(0) == pytest.approx(0.0)

    def test_sind_90(self):
        assert sind(90) == pytest.approx(1.0)

    def test_cosd_0(self):
        assert cosd(0) == pytest.approx(1.0)

    def test_cosd_90(self):
        assert cosd(90) == pytest.approx(0.0, abs=1e-15)

    def test_tand_45(self):
        assert tand(45) == pytest.approx(1.0)

    def test_inverse_round_trip(self):
        assert asind(sind(30)) == pytest.approx(30.0)
        assert acosd(cosd(60)) == pytest.approx(60.0)
        assert atand(tand(45)) == pytest.approx(45.0)

    def test_array_input(self):
        angles = np.array([0, 30, 45, 60, 90])
        result = sind(angles)
        assert result.shape == (5,)
        assert result[-1] == pytest.approx(1.0)


# -- ISA atmosphere ---------------------------------------------------------

class TestISA:
    def test_sea_level_temperature(self):
        assert temperature_isa(0) == pytest.approx(288.15)

    def test_sea_level_pressure(self):
        assert pressure_isa(0) == pytest.approx(101325.0)

    def test_sea_level_density(self):
        assert density_isa(0) == pytest.approx(1.225)

    def test_density_decreases_with_altitude(self):
        assert density_isa(1000) < density_isa(0)
        assert density_isa(5000) < density_isa(1000)

    def test_tropopause_density(self):
        rho = density_isa(10000)
        assert 0.3 < rho < 0.5  # ~0.41 kg/m³


# -- Dynamic pressure & Reynolds -------------------------------------------

class TestFlowQuantities:
    def test_dynamic_pressure_basic(self):
        q = dynamic_pressure(20.0, 1.225)
        assert q == pytest.approx(0.5 * 1.225 * 20**2)

    def test_dynamic_pressure_from_altitude(self):
        q = dynamic_pressure(20.0, h=0.0)
        assert q == pytest.approx(245.0)

    def test_reynolds_number(self):
        Re = reynolds(1.225, 15.0, 0.25, 1.8e-5)
        assert Re == pytest.approx(1.225 * 15 * 0.25 / 1.8e-5)

    def test_skin_friction_positive(self):
        Cf = skin_friction_turbulent(1e6)
        assert 0.001 < Cf < 0.01


# -- Interpolation & geometry helpers ---------------------------------------

class TestInterpolation:
    def test_interp1d_midpoint(self):
        assert interp1d([0, 1], [0, 10], 0.5) == pytest.approx(5.0)

    def test_interp1d_endpoints(self):
        assert interp1d([0, 1, 2], [0, 1, 4], 0.0) == pytest.approx(0.0)
        assert interp1d([0, 1, 2], [0, 1, 4], 2.0) == pytest.approx(4.0)

    def test_arc_length_straight(self):
        x = [0, 1, 2, 3]
        y = [0, 0, 0, 0]
        assert arc_length(x, y) == pytest.approx(3.0)

    def test_arc_length_diagonal(self):
        assert arc_length([0, 1], [0, 1]) == pytest.approx(np.sqrt(2))

    def test_euclidean_2d(self):
        assert euclidean([0, 0], [3, 4]) == pytest.approx(5.0)

    def test_euclidean_3d(self):
        assert euclidean([0, 0, 0], [1, 2, 2]) == pytest.approx(3.0)
