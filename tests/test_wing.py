"""Tests for rc_aircraft_design.wing (geometry + loads)."""

import numpy as np
import pytest

from rc_aircraft_design.wing import (
    Wing, MACResult, compute_mac, size_wing,
    ConventionalConcept, size_conventional, planform_coords,
)
from rc_aircraft_design.wing.loads import (
    SpanLoadResult,
    trapezoid_chord, elliptic_Cl,
    compute_span_loads, compute_span_loads_simple,
)


# -- Wing dataclass ---------------------------------------------------------

class TestWing:
    def test_rectangular_wing(self):
        w = Wing(chord_root=0.3, chord_tip=0.3, span=1.5)
        assert w.area == pytest.approx(0.3 * 1.5)
        assert w.taper_ratio == pytest.approx(1.0)
        assert w.aspect_ratio == pytest.approx(1.5**2 / (0.3 * 1.5))

    def test_tapered_wing(self):
        w = Wing(chord_root=0.5, chord_tip=0.3, span=1.6)
        assert w.taper_ratio == pytest.approx(0.6)
        assert w.area == pytest.approx((0.5 + 0.3) * 1.6 / 2)

    def test_mac_property_returns_mac_result(self):
        w = Wing(chord_root=0.5, chord_tip=0.3, span=1.6)
        m = w.mac
        assert isinstance(m, MACResult)
        assert m.mac_length > 0

    def test_mac_property_matches_compute_mac(self):
        w = Wing(chord_root=0.5, chord_tip=0.3, span=1.6, sweep_deg=10)
        m1 = w.mac
        m2 = compute_mac(w)
        assert m1.mac_length == pytest.approx(m2.mac_length)
        assert m1.x_aero_focus == pytest.approx(m2.x_aero_focus)
        assert m1.y_mac == pytest.approx(m2.y_mac)


# -- MAC computations -------------------------------------------------------

class TestMAC:
    def test_rectangular_mac_equals_chord(self):
        w = Wing(chord_root=0.3, chord_tip=0.3, span=1.5)
        mac = compute_mac(w)
        assert mac.mac_length == pytest.approx(0.3)

    def test_tapered_mac_between_chords(self):
        w = Wing(chord_root=0.5, chord_tip=0.3, span=1.6)
        mac = compute_mac(w)
        assert 0.3 < mac.mac_length < 0.5

    def test_half_wing_type(self):
        w = Wing(chord_root=0.5, chord_tip=0.3, span=0.8, type_=1)
        mac = compute_mac(w)
        assert mac.y_mac < 0.8  # within half span

    def test_sweep_offsets_aero_focus(self):
        w_no_sweep = Wing(chord_root=0.3, chord_tip=0.2, span=1.0, sweep_deg=0.0)
        w_swept = Wing(chord_root=0.3, chord_tip=0.2, span=1.0, sweep_deg=20.0)
        mac_ns = compute_mac(w_no_sweep)
        mac_sw = compute_mac(w_swept)
        assert mac_sw.x_aero_focus > mac_ns.x_aero_focus

    def test_mac_from_plane_json(self, sport_trainer):
        wdata = sport_trainer["wing_main"]
        w = Wing(**{k: v for k, v in wdata.items()})
        mac = compute_mac(w)
        assert mac.mac_length > 0
        assert mac.y_mac > 0


# -- Sizing helpers ----------------------------------------------------------

class TestSizing:
    def test_size_wing_rectangular(self):
        span, cr, ct = size_wing(S=1.0, AR=10.0, taper_ratio=1.0)
        assert span == pytest.approx(np.sqrt(10.0))
        assert cr == pytest.approx(ct)
        assert cr * span == pytest.approx(1.0)

    def test_size_wing_tapered(self):
        span, cr, ct = size_wing(S=0.3, AR=8.0, taper_ratio=0.6)
        assert ct == pytest.approx(0.6 * cr)
        assert (cr + ct) * span / 2 == pytest.approx(0.3)

    def test_size_conventional(self):
        concept = size_conventional()
        assert isinstance(concept, ConventionalConcept)
        assert concept.wing_main.type_ == 0
        assert concept.wing_vert.type_ == 2
        assert len(concept.fuselage_radii) > 0


# -- Planform coords --------------------------------------------------------

class TestPlanformCoords:
    def test_full_wing_closed_polygon(self):
        w = Wing(chord_root=0.3, chord_tip=0.2, span=1.5)
        x, y = planform_coords(w)
        # First and last points should match (closed)
        assert x[0] == pytest.approx(x[-1])
        assert y[0] == pytest.approx(y[-1])

    def test_full_wing_symmetric_y(self):
        w = Wing(chord_root=0.3, chord_tip=0.2, span=1.5)
        x, y = planform_coords(w)
        assert max(y) == pytest.approx(0.75)
        assert min(y) == pytest.approx(-0.75)

    def test_half_wing_y_range(self):
        w = Wing(chord_root=0.3, chord_tip=0.2, span=0.75, type_=1)
        x, y = planform_coords(w)
        assert min(y) >= 0  # no negative y for half wing

    def test_vertical_tail(self):
        w = Wing(chord_root=0.15, chord_tip=0.08, span=0.18, type_=2, sweep_deg=25)
        x, y = planform_coords(w)
        assert len(x) == len(y)
        assert x[0] == pytest.approx(x[-1])

    def test_swept_wing_x_offset(self):
        w = Wing(chord_root=0.3, chord_tip=0.2, span=1.5, sweep_deg=20)
        x, y = planform_coords(w)
        # Tips should be aft of root LE
        tip_x = x[y == max(y)]
        assert all(tx >= w.x for tx in tip_x)


# -- Span loads (loads.py) --------------------------------------------------

class TestTrapezoidChord:
    def test_root(self):
        c = trapezoid_chord(0.0, 0.8, 0.5, 0.3)
        assert float(c) == pytest.approx(0.5)

    def test_tip(self):
        c = trapezoid_chord(0.8, 0.8, 0.5, 0.3)
        assert float(c) == pytest.approx(0.3)

    def test_midspan(self):
        c = trapezoid_chord(0.4, 0.8, 0.5, 0.3)
        assert float(c) == pytest.approx(0.4)


class TestEllipticCl:
    def test_root_max(self):
        cl = elliptic_Cl(0.0, 0.8, 0.5, 8.0)
        assert float(cl) == pytest.approx(0.5)

    def test_tip_zero(self):
        cl = elliptic_Cl(0.8, 0.8, 0.5, 8.0)
        assert float(cl) == pytest.approx(0.0, abs=1e-10)


class TestSpanLoads:
    def test_simple_loads_basic(self):
        result = compute_span_loads_simple(
            half_span=0.75, root_chord=0.3, tip_chord=0.2,
            CL=0.5, velocity=15.0, rho=1.225,
        )
        assert isinstance(result, SpanLoadResult)
        assert result.total_lift > 0
        assert result.shear[0] > 0  # root shear positive (upward)
        assert result.bending[0] > 0  # root bending positive

    def test_tip_loads_zero(self):
        result = compute_span_loads_simple(
            half_span=0.75, root_chord=0.3, tip_chord=0.2,
            CL=0.5, velocity=15.0,
        )
        assert result.shear[-1] == pytest.approx(0.0, abs=1e-6)
        assert result.bending[-1] == pytest.approx(0.0, abs=1e-6)

    def test_weight_relief_reduces_loads(self):
        r1 = compute_span_loads_simple(
            half_span=0.75, root_chord=0.3, tip_chord=0.2,
            CL=0.5, velocity=15.0, wing_mass_kg=0.0,
        )
        r2 = compute_span_loads_simple(
            half_span=0.75, root_chord=0.3, tip_chord=0.2,
            CL=0.5, velocity=15.0, wing_mass_kg=0.3,
        )
        assert r2.shear[0] < r1.shear[0]  # weight relief

    def test_compute_span_loads_with_torsion(self):
        n = 20
        y = np.linspace(0, 0.75, n)
        chord = np.linspace(0.3, 0.2, n)
        Cl = np.ones(n) * 0.5
        Cm = np.ones(n) * -0.05
        result = compute_span_loads(y, chord, Cl, q_inf=137.8, Cm=Cm)
        assert result.torsion is not None
        assert result.torsion[-1] == pytest.approx(0.0, abs=1e-6)

    def test_from_plane_json(self, sport_trainer):
        wm = sport_trainer["wing_main"]
        result = compute_span_loads_simple(
            half_span=wm["span"] / 2,
            root_chord=wm["chord_root"],
            tip_chord=wm["chord_tip"],
            CL=0.5, velocity=15.0,
        )
        assert result.total_lift > 0
