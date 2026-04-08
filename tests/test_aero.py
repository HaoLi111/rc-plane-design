"""Tests for rc_aircraft_design.aero (analysis + airfoil)."""

import numpy as np
import pytest

from rc_aircraft_design.aero import (
    Cl_thin, Cd_induced, k_factor, oswald_efficiency, aspect_ratio,
    Cp_prandtl_glauert, Cp_karman_tsien, Cl_alpha_corrected,
    form_factor_wing, form_factor_body, form_factor_nacelle,
    LinearAirfoil, AlphaAnalysis,
    climb_analysis, ClimbAnalysis,
    load_analysis, LoadAnalysis,
    naca4, naca4_camber, naca6_thickness,
)


# -- Fundamental coefficients -----------------------------------------------

class TestFundamentals:
    def test_Cl_thin_zero(self):
        assert Cl_thin(0.0) == pytest.approx(0.0)

    def test_Cl_thin_linear(self):
        assert Cl_thin(np.radians(5)) == pytest.approx(2 * np.pi * np.radians(5))

    def test_Cd_induced_zero_lift(self):
        assert Cd_induced(0.0, 8.0) == pytest.approx(0.0)

    def test_Cd_induced_positive(self):
        cdi = Cd_induced(1.0, 8.0, 0.85)
        assert cdi > 0
        assert cdi == pytest.approx(1.0 / (np.pi * 8.0 * 0.85))

    def test_k_factor(self):
        assert k_factor(10.0, 0.8) == pytest.approx(1.0 / (np.pi * 10 * 0.8))

    def test_oswald_efficiency_range(self):
        e = oswald_efficiency(8.0)
        assert 0.5 < e < 1.0

    def test_aspect_ratio(self):
        assert aspect_ratio(2.0, 0.5) == pytest.approx(8.0)


# -- Compressibility corrections -------------------------------------------

class TestCompressibility:
    def test_prandtl_glauert_low_mach(self):
        cp = Cp_prandtl_glauert(-1.0, 0.3)
        assert cp < -1.0  # correction increases magnitude

    def test_karman_tsien(self):
        cp = Cp_karman_tsien(-1.0, 0.3)
        assert cp < -1.0

    def test_Cl_alpha_corrected_subsonic(self):
        cla = Cl_alpha_corrected(8.0, 0.0, 0.2)
        assert 2.0 < cla < 2 * np.pi  # less than 2D thin airfoil


# -- Form factors -----------------------------------------------------------

class TestFormFactors:
    def test_form_factor_wing(self):
        ff = form_factor_wing(0.12)
        assert ff > 1.0

    def test_form_factor_body(self):
        ff = form_factor_body(8.0)
        assert ff > 1.0

    def test_form_factor_nacelle(self):
        ff = form_factor_nacelle(3.0)
        assert ff > 1.0


# -- LinearAirfoil ---------------------------------------------------------

class TestLinearAirfoil:
    def test_default_zero_lift_angle(self):
        af = LinearAirfoil()
        cl = af.Cl(af.alpha0_deg)
        assert cl == pytest.approx(0.0, abs=1e-12)

    def test_positive_lift_above_alpha0(self):
        af = LinearAirfoil(Cla=0.1, alpha0_deg=-2.0)
        assert float(af.Cl(5.0)) > 0

    def test_drag_at_zero_alpha(self):
        af = LinearAirfoil(Cd0=0.02, Cdi_factor=0.04, alpha0_deg=-5.0)
        cd = float(af.Cd(0.0))
        assert cd > 0.02  # parasite + induced at non-zero Cl

    def test_L_over_D_finite(self):
        af = LinearAirfoil()
        ld = af.L_over_D(5.0)
        assert np.isfinite(ld)

    def test_analyze_returns_alpha_analysis(self):
        af = LinearAirfoil()
        result = af.analyze()
        assert isinstance(result, AlphaAnalysis)
        assert len(result.alpha) > 0
        assert result.Clmax > 0
        assert result.LDmax > 0

    def test_analyze_custom_range(self):
        af = LinearAirfoil()
        result = af.analyze(alpha_range=np.arange(0, 10, 1))
        assert len(result.alpha) == 10

    def test_from_plane_json(self, sport_trainer):
        af_data = sport_trainer["airfoil"]
        af = LinearAirfoil(
            Cla=af_data["Cla"],
            alpha0_deg=af_data["alpha0_deg"],
            Cd0=af_data["Cd0"],
            Cdi_factor=af_data["Cdi_factor"],
        )
        result = af.analyze()
        assert result.LDmax > 5


# -- Climb analysis ---------------------------------------------------------

class TestClimbAnalysis:
    def test_basic_climb(self):
        result = climb_analysis(Cl=0.5, Cd=0.05, rho=1.225, S=0.3, W=10.0)
        assert isinstance(result, ClimbAnalysis)
        assert len(result.theta_deg) > 0
        assert result.v[0] > 0  # level flight speed

    def test_zero_angle_is_level(self):
        result = climb_analysis(Cl=0.5, Cd=0.05, rho=1.225, S=0.3, W=10.0)
        assert result.vy[0] == pytest.approx(0.0, abs=1e-10)


# -- Load analysis ----------------------------------------------------------

class TestLoadAnalysis:
    def test_basic_vn(self):
        result = load_analysis(Clmax_pos=1.5, Clmax_neg=-0.8, W_over_S=50.0, rho=1.225)
        assert isinstance(result, LoadAnalysis)
        assert result.n_pos[0] == pytest.approx(0.0, abs=0.01)  # v=0 → n=0
        assert max(result.n_pos) == pytest.approx(3.8)  # hits limit

    def test_neg_load_factor(self):
        result = load_analysis(Clmax_pos=1.5, Clmax_neg=-0.8, W_over_S=50.0, rho=1.225)
        assert min(result.n_neg) == pytest.approx(-1.5)


# -- NACA airfoil generation ------------------------------------------------

class TestNACA:
    def test_naca4_symmetric(self):
        x, yu, yl = naca4("0012")
        assert len(x) == 100
        np.testing.assert_allclose(yu, -yl, atol=1e-12)
        assert max(yu - yl) == pytest.approx(0.12, abs=0.005)

    def test_naca4_cambered(self):
        x, yu, yl = naca4("2412")
        assert len(x) == 100
        assert max(yu) > max(-yl)  # upper surface higher due to camber

    def test_naca4_endpoints(self):
        x, yu, yl = naca4("0012")
        assert x[0] == pytest.approx(0.0, abs=1e-12)
        assert x[-1] == pytest.approx(1.0, abs=1e-12)

    def test_naca4_invalid_code(self):
        with pytest.raises(ValueError):
            naca4("abc")
        with pytest.raises(ValueError):
            naca4("12345")

    def test_naca4_custom_points(self):
        x, yu, yl = naca4("2412", n_points=50, cosine_spacing=False)
        assert len(x) == 50

    def test_naca4_camber_line(self):
        x, yc = naca4_camber("2412")
        assert max(yc) > 0  # has camber
        assert yc[0] == pytest.approx(0.0, abs=1e-12)  # starts at 0

    def test_naca4_camber_symmetric(self):
        x, yc = naca4_camber("0012")
        np.testing.assert_allclose(yc, 0.0, atol=1e-12)

    def test_naca6_thickness(self):
        x, yt = naca6_thickness(0.12)
        assert len(x) == 100
        assert max(yt) > 0
