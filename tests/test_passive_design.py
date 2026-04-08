"""Tests for the passive design pipeline across diverse missions.

Each mission JSON contains only assumptions + airfoil params.
The pipeline must produce a physically plausible aircraft for every one.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from rc_aircraft_design.passive import run_passive_design, PassiveDesignResult

MISSION_DIR = Path(__file__).resolve().parent.parent / "data" / "examples" / "missions"
MISSION_FILES = sorted(MISSION_DIR.glob("*.json"))

# Also include the original passive_sport_flyer in the top-level examples dir
TOPLEVEL = Path(__file__).resolve().parent.parent / "data" / "examples" / "passive_sport_flyer.json"
if TOPLEVEL.exists():
    MISSION_FILES = [TOPLEVEL] + list(MISSION_FILES)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(params=MISSION_FILES, ids=lambda p: p.stem)
def mission(request) -> dict:
    return _load(request.param)


@pytest.fixture(params=MISSION_FILES, ids=lambda p: p.stem)
def design(request) -> PassiveDesignResult:
    data = _load(request.param)
    return run_passive_design(data["assumptions"], data["airfoil"])


# =====================================================================
# Stage 1 — Aero sanity
# =====================================================================

class TestAeroStage:
    def test_LDmax_positive(self, design: PassiveDesignResult):
        assert design.aero.LDmax > 0

    def test_Clmax_positive(self, design: PassiveDesignResult):
        assert design.aero.Clmax > 0

    def test_Cdmin_positive(self, design: PassiveDesignResult):
        assert design.aero.Cdmin > 0

    def test_Cdmin_less_than_Clmax(self, design: PassiveDesignResult):
        # Drag coefficient should be much smaller than max lift coefficient
        assert design.aero.Cdmin < design.aero.Clmax


# =====================================================================
# Stage 2 — Constraint analysis
# =====================================================================

class TestConstraintStage:
    def test_TW_positive(self, design: PassiveDesignResult):
        assert design.TW_opt > 0

    def test_TW_reasonable(self, design: PassiveDesignResult):
        # T/W should be between 0.05 (efficient glider) and 2.0 (extreme 3D)
        assert 0.05 < design.TW_opt < 2.0

    def test_WS_positive(self, design: PassiveDesignResult):
        assert design.WS_opt > 0

    def test_WS_reasonable(self, design: PassiveDesignResult):
        # W/S for RC planes: roughly 5–150 N/m²
        assert 3 < design.WS_opt < 200

    def test_envelope_all_positive(self, design: PassiveDesignResult):
        assert np.all(design.constraints.envelope > 0)


# =====================================================================
# Stage 3 — Weight & power
# =====================================================================

class TestWeightPowerStage:
    def test_gross_mass_positive(self, design: PassiveDesignResult):
        assert design.m_gross_kg > 0

    def test_wing_area_positive(self, design: PassiveDesignResult):
        assert design.S_wing > 0

    def test_thrust_positive(self, design: PassiveDesignResult):
        assert design.thrust_req_N > 0

    def test_shaft_power_positive(self, design: PassiveDesignResult):
        assert design.shaft_power_W > 0

    def test_powered_has_endurance(self, design: PassiveDesignResult):
        if design.power_system is not None:
            assert design.power_system.endurance_min > 0


# =====================================================================
# Stage 4 — Geometry
# =====================================================================

class TestGeometryStage:
    def test_wing_area_matches_target(self, design: PassiveDesignResult):
        wm = design.concept.wing_main
        assert wm.area == pytest.approx(design.S_wing, rel=0.01)

    def test_wing_span_positive(self, design: PassiveDesignResult):
        assert design.concept.wing_main.span > 0

    def test_wing_AR_matches(self, design: PassiveDesignResult):
        wm = design.concept.wing_main
        assert wm.aspect_ratio == pytest.approx(8.0, rel=0.01)

    def test_tail_areas_positive(self, design: PassiveDesignResult):
        assert design.concept.wing_horiz.area > 0
        assert design.concept.wing_vert.area > 0

    def test_tail_behind_wing(self, design: PassiveDesignResult):
        assert design.concept.wing_horiz.x > design.concept.wing_main.x
        assert design.concept.wing_vert.x > design.concept.wing_main.x

    def test_fuselage_length_positive(self, design: PassiveDesignResult):
        assert design.concept.fuselage_length > 0

    def test_taper_ratio(self, design: PassiveDesignResult):
        wm = design.concept.wing_main
        assert 0 < wm.taper_ratio <= 1.0

    def test_mac_positive(self, design: PassiveDesignResult):
        from rc_aircraft_design.wing.geometry import compute_mac
        mac = compute_mac(design.concept.wing_main)
        assert mac.mac_length > 0
        assert mac.y_mac > 0


# =====================================================================
# Stage 5 — Stability
# =====================================================================

class TestStabilityStage:
    def test_Vh_in_range(self, design: PassiveDesignResult):
        assert design.stability_checks["Vh"], (
            f"Vh={design.stability.Vh:.3f} out of range"
        )

    def test_Vv_in_range(self, design: PassiveDesignResult):
        assert design.stability_checks["Vv"], (
            f"Vv={design.stability.Vv:.4f} out of range"
        )

    def test_SM_in_range(self, design: PassiveDesignResult):
        assert design.stability_checks["SM"], (
            f"SM={design.stability.static_margin:.3f} out of range"
        )

    def test_neutral_point_aft_of_wing_le(self, design: PassiveDesignResult):
        assert design.stability.X_np > design.concept.wing_main.x


# =====================================================================
# End-to-end: pipeline does not crash for any mission
# =====================================================================

class TestPipelineEndToEnd:
    def test_pipeline_completes(self, mission: dict):
        """The pipeline should run to completion without exceptions."""
        result = run_passive_design(mission["assumptions"], mission["airfoil"])
        assert isinstance(result, PassiveDesignResult)

    def test_all_stages_produce_values(self, mission: dict):
        result = run_passive_design(mission["assumptions"], mission["airfoil"])
        # Every numeric output must be finite
        assert np.isfinite(result.TW_opt)
        assert np.isfinite(result.WS_opt)
        assert np.isfinite(result.m_gross_kg)
        assert np.isfinite(result.S_wing)
        assert np.isfinite(result.stability.static_margin)
        assert np.isfinite(result.stability.Vh)
        assert np.isfinite(result.stability.Vv)
