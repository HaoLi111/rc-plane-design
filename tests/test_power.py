"""Tests for rc_aircraft_design.power (propulsion)."""

import numpy as np
import pytest

from rc_aircraft_design.power import (
    Propeller, design_propeller_russell, thrust_russell,
    rubber_breaking_turns_millman, rubber_torque,
    rubber_breaking_turns_sherman, rubber_torque_sherman,
    ElectricPowerSystem, WeightEstimate,
)


# -- Propeller design (Russell) --------------------------------------------

class TestPropellerRussell:
    def test_design_returns_propeller(self):
        prop = design_propeller_russell(RPM=8000, speed_ms=15.0)
        assert isinstance(prop, Propeller)
        assert prop.diameter > 0
        assert prop.radius == pytest.approx(prop.diameter / 2)
        assert prop.pitch > 0

    def test_thrust_positive(self):
        prop = design_propeller_russell(RPM=8000, speed_ms=15.0)
        T = thrust_russell(prop.radius, prop.pitch, 8000)
        assert T > 0

    def test_thrust_wood_vs_metal(self):
        prop = design_propeller_russell(RPM=8000, speed_ms=15.0)
        T_wood = thrust_russell(prop.radius, prop.pitch, 8000, material="wood")
        T_metal = thrust_russell(prop.radius, prop.pitch, 8000, material="metal")
        assert T_metal > T_wood  # metal has higher mu

    def test_higher_rpm_more_thrust(self):
        prop = design_propeller_russell(RPM=8000, speed_ms=15.0)
        T1 = thrust_russell(prop.radius, prop.pitch, 6000)
        T2 = thrust_russell(prop.radius, prop.pitch, 10000)
        assert T2 > T1


# -- Rubber motor -----------------------------------------------------------

class TestRubberMotor:
    def test_breaking_turns_millman(self):
        turns = rubber_breaking_turns_millman(0.1, K=50.0)
        assert turns > 0

    def test_torque_positive(self):
        tau = rubber_torque(0.1, C=5.0)
        assert tau > 0

    def test_breaking_turns_sherman(self):
        turns = rubber_breaking_turns_sherman(N=8, W=0.05)
        assert turns > 0

    def test_torque_sherman(self):
        tau = rubber_torque_sherman(N=8, W=0.05)
        assert tau > 0


# -- Electric power system ---------------------------------------------------

class TestElectricPowerSystem:
    def test_basic_properties(self):
        eps = ElectricPowerSystem(
            motor_power_W=150, motor_efficiency=0.8,
            prop_efficiency=0.65,
            battery_voltage=11.1, battery_capacity_Ah=2.2,
        )
        assert eps.input_power_W == pytest.approx(150 / 0.8)
        assert eps.current_A == pytest.approx(eps.input_power_W / 11.1)
        assert eps.endurance_min > 0
        assert eps.thrust_N > 0

    def test_from_plane_json(self, sport_trainer):
        p = sport_trainer["power"]
        eps = ElectricPowerSystem(
            motor_power_W=p["motor_power_W"],
            motor_efficiency=p["motor_efficiency"],
            prop_efficiency=p["prop_efficiency"],
            battery_voltage=p["battery_voltage"],
            battery_capacity_Ah=p["battery_capacity_Ah"],
        )
        assert eps.endurance_min > 0
        assert eps.thrust_N > 0


# -- Weight estimation ------------------------------------------------------

class TestWeightEstimate:
    def test_gross_weight(self):
        we = WeightEstimate(m_payload_kg=0.2, f_payload=0.25)
        assert we.m_gross_kg == pytest.approx(0.2 / 0.25)
        assert we.W_gross_N == pytest.approx(we.m_gross_kg * 9.80665)

    def test_from_plane_json(self, sport_trainer):
        wd = sport_trainer["weight"]
        we = WeightEstimate(
            m_payload_kg=wd["m_payload_kg"],
            f_payload=wd["f_payload"],
            v_cruise_ms=wd["v_cruise_ms"],
            endurance_s=wd["endurance_s"],
        )
        assert we.m_gross_kg > 0
