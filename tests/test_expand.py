"""Tests for rc_aircraft_design.expand (surface unfolding)."""

import numpy as np
import pytest

from rc_aircraft_design.expand import (
    expand_quad, expand_triangle, expand_strip, unfold_wing_surface,
)
from rc_aircraft_design.utils import euclidean


# -- expand_quad ------------------------------------------------------------

class TestExpandQuad:
    def test_flat_quad_preserves_lengths(self):
        # Flat unit square lying in XY plane
        bl, br = [0, 0, 0], [1, 0, 0]
        tl, tr = [0, 1, 0], [1, 1, 0]
        result = expand_quad(bl, br, tl, tr)
        p_left = np.array(result["p_left"])
        p_right = np.array(result["p_right"])
        # Top edge should have length ~1
        assert np.linalg.norm(p_right - p_left) == pytest.approx(1.0, abs=0.05)

    def test_returns_expected_keys(self):
        result = expand_quad([0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0])
        assert "p_left" in result
        assert "p_right" in result
        assert "angle_new_left" in result
        assert "angle_new_right" in result


# -- expand_triangle --------------------------------------------------------

class TestExpandTriangle:
    def test_right_triangle(self):
        bl, br, top = [0, 0, 0], [3, 0, 0], [0, 4, 0]
        result = expand_triangle(bl, br, top)
        p_top = np.array(result["p_top"])
        # Distance from bl projection to p_top should preserve original length
        d = np.linalg.norm(p_top - np.array([0.0, 0.0]))
        assert d == pytest.approx(4.0, abs=0.05)


# -- expand_strip -----------------------------------------------------------

class TestExpandStrip:
    def test_two_row_strip(self):
        left = [[0, 0, 0], [0, 1, 0]]
        right = [[1, 0, 0], [1, 1, 0]]
        pl, pr = expand_strip(left, right)
        assert len(pl) == 2
        assert len(pr) == 2

    def test_multi_row_strip(self):
        n = 5
        left = [[0, i, 0] for i in range(n)]
        right = [[1, i, 0.1 * i] for i in range(n)]  # slightly curved
        pl, pr = expand_strip(left, right)
        assert len(pl) == n
        assert len(pr) == n

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            expand_strip([[0, 0, 0]], [[1, 0, 0], [1, 1, 0]])

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError):
            expand_strip([[0, 0, 0]], [[1, 0, 0]])


# -- unfold_wing_surface ----------------------------------------------------

class TestUnfoldWingSurface:
    def test_returns_two_lists(self):
        ax = np.linspace(0, 1, 10)
        ay = 0.06 * np.sin(np.pi * ax)  # simple bump
        pl, pr = unfold_wing_surface(ax, ay, chord_root=0.3, chord_tip=0.2, span=0.5, n_span=3)
        assert len(pl) > 0
        assert len(pr) > 0

    def test_lower_surface(self):
        ax = np.linspace(0, 1, 10)
        ay = 0.06 * np.sin(np.pi * ax)
        pl, pr = unfold_wing_surface(ax, ay, chord_root=0.3, chord_tip=0.2, span=0.5, n_span=3, upper=False)
        assert len(pl) > 0

    def test_with_naca_airfoil(self):
        from rc_aircraft_design.aero import naca4
        x, yu, yl = naca4("2412", n_points=20)
        pl, pr = unfold_wing_surface(x, yu, chord_root=0.3, chord_tip=0.2, span=0.5, n_span=3)
        assert len(pl) == 20
        assert len(pr) == 20
