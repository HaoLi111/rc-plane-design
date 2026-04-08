"""Tests for rc_aircraft_design.stability."""

import pytest

from rc_aircraft_design.wing.geometry import Wing, ConventionalConcept
from rc_aircraft_design.stability import (
    StabilityResult,
    horizontal_tail_volume, vertical_tail_volume,
    spiral_stability, neutral_point,
    analyze_stability, check_design_ranges, DESIGN_RANGES,
)


# -- Helper functions -------------------------------------------------------

class TestVolumeCoefficients:
    def test_horizontal_tail_volume(self):
        Vh = horizontal_tail_volume(Sh=0.06, Lh=0.8, Sw=0.3, mac_w=0.25)
        assert Vh == pytest.approx(0.06 * 0.8 / (0.3 * 0.25))

    def test_vertical_tail_volume(self):
        Vv = vertical_tail_volume(Sv=0.02, Lv=0.8, Sw=0.3, bw=1.5)
        assert Vv == pytest.approx(0.02 * 0.8 / (0.3 * 1.5))


class TestSpiralStability:
    def test_basic(self):
        B = spiral_stability(lv=0.8, b=1.5, dihedral_deg=5.0, Cl=0.5)
        assert B == pytest.approx((0.8 / 1.5) * (5.0 / 0.5))


class TestNeutralPoint:
    def test_neutral_point_ahead_of_ac(self):
        # With positive Vh, NP should be aft of AC
        X_np = neutral_point(Xac_w=0.3, AR_w=8.0, AR_h=5.0, Vh=0.5)
        assert X_np > 0.3


# -- Full stability analysis ------------------------------------------------

def _make_concept():
    wm = Wing(chord_root=0.3, chord_tip=0.2, span=1.5, dihedral_deg=5.0, x=0.25, type_=0)
    wh = Wing(chord_root=0.15, chord_tip=0.10, span=0.5, x=0.95, type_=0)
    wv = Wing(chord_root=0.15, chord_tip=0.08, span=0.18, sweep_deg=25.0, x=0.92, type_=2)
    return ConventionalConcept(wing_main=wm, wing_horiz=wh, wing_vert=wv, fuselage_length=1.1)


class TestAnalyzeStability:
    def test_returns_stability_result(self):
        concept = _make_concept()
        result = analyze_stability(concept, X_cg=0.37)
        assert isinstance(result, StabilityResult)
        assert result.X_cg == pytest.approx(0.37)

    def test_volume_coefficients_positive(self):
        concept = _make_concept()
        result = analyze_stability(concept, X_cg=0.37)
        assert result.Vh > 0
        assert result.Vv > 0

    def test_neutral_point_reasonable(self):
        concept = _make_concept()
        result = analyze_stability(concept, X_cg=0.37)
        assert 0.1 < result.X_np < 1.5

    def test_check_design_ranges(self):
        concept = _make_concept()
        result = analyze_stability(concept, X_cg=0.37)
        checks = check_design_ranges(result)
        assert isinstance(checks, dict)
        assert set(checks.keys()) == {"Vh", "Vv", "SM", "B"}

    def test_from_plane_json(self, sport_trainer):
        wm_d = sport_trainer["wing_main"]
        wh_d = sport_trainer["wing_horiz"]
        wv_d = sport_trainer["wing_vert"]
        fus = sport_trainer["fuselage"]

        wm = Wing(**{k: v for k, v in wm_d.items()})
        wh = Wing(**{k: v for k, v in wh_d.items()})
        wv = Wing(**{k: v for k, v in wv_d.items()})
        concept = ConventionalConcept(
            wing_main=wm, wing_horiz=wh, wing_vert=wv,
            fuselage_length=fus["length"],
            fuselage_stations=fus["stations"],
            fuselage_radii=fus["radii"],
        )
        result = analyze_stability(concept, X_cg=sport_trainer["cg_x"])
        assert result.Vh > 0
        assert isinstance(result.static_margin, float)
