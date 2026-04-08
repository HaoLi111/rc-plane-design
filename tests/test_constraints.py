"""Tests for rc_aircraft_design.constraints."""

import numpy as np
import pytest

from rc_aircraft_design.constraints import (
    ConstraintParams, ConstraintResult,
    constraint_turn, constraint_climb, constraint_cruise,
    constraint_service_ceiling, constraint_takeoff, constraint_energy_level,
    analyze_constraints,
)


# -- Individual constraints -------------------------------------------------

class TestConstraintFunctions:
    @pytest.fixture()
    def params(self):
        return ConstraintParams()

    def test_turn_positive(self, params):
        tw = constraint_turn(params)
        assert np.all(tw > 0)

    def test_climb_positive(self, params):
        tw = constraint_climb(params)
        assert np.all(tw > 0)

    def test_cruise_positive(self, params):
        tw = constraint_cruise(params)
        assert np.all(tw > 0)

    def test_ceiling_positive(self, params):
        tw = constraint_service_ceiling(params)
        assert np.all(tw > 0)

    def test_takeoff_positive(self, params):
        tw = constraint_takeoff(params)
        assert np.all(tw > 0)

    def test_energy_level(self, params):
        tw = constraint_energy_level(params, v=20.0, Ps=5.0)
        assert np.all(tw > 0)


# -- Full analysis ----------------------------------------------------------

class TestAnalyzeConstraints:
    def test_default_returns_result(self):
        result = analyze_constraints()
        assert isinstance(result, ConstraintResult)
        assert len(result.W_S) > 0
        assert len(result.turn) == len(result.W_S)

    def test_envelope_is_max_of_all(self):
        result = analyze_constraints()
        envelope = result.envelope
        assert np.all(envelope >= result.turn - 1e-12)
        assert np.all(envelope >= result.climb - 1e-12)
        assert np.all(envelope >= result.cruise - 1e-12)

    def test_custom_params(self):
        params = ConstraintParams(
            Cd_min=0.025, k=0.04,
            turn_v=15.0, turn_n=2.0,
            climb_vv=3.0, climb_v=12.0,
            cruise_v=15.0,
            to_Sg=20.0,
        )
        result = analyze_constraints(params)
        assert result.envelope.min() > 0

    def test_from_plane_json(self, sport_trainer):
        af = sport_trainer["airfoil"]
        c = sport_trainer["constraints"]
        bank_rad = np.radians(c["turn_bank_deg"])
        params = ConstraintParams(
            Cd_min=af["Cd0"],
            k=af["Cdi_factor"],
            turn_v=c["turn_v"],
            turn_n=1.0 / np.cos(bank_rad),
            climb_vv=c["climb_vv"],
            climb_v=c["climb_v"],
            cruise_v=c["cruise_v"],
            ceiling_h=c["ceiling_h"],
            to_Sg=c["to_Sg"],
        )
        result = analyze_constraints(params)
        assert result.envelope.min() > 0
        assert result.envelope.min() < 5.0  # reasonable T/W
