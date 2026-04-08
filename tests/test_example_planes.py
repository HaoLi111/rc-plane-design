"""Integration tests using example plane JSON configurations.

Exercises a realistic workflow for each example aircraft:
  1. Load JSON config
  2. Build Wing / ConventionalConcept from it
  3. Run aero analysis
  4. Run stability analysis
  5. Run constraint analysis
  6. Compute span loads
  7. Generate DXF export
  8. Generate fuselage mesh
"""

from __future__ import annotations

import json
import numpy as np
import pytest

from rc_aircraft_design.aero import LinearAirfoil, naca4
from rc_aircraft_design.wing.geometry import Wing, ConventionalConcept, compute_mac, planform_coords
from rc_aircraft_design.wing.loads import compute_span_loads_simple
from rc_aircraft_design.stability import analyze_stability
from rc_aircraft_design.constraints import ConstraintParams, analyze_constraints
from rc_aircraft_design.power import ElectricPowerSystem, WeightEstimate
from rc_aircraft_design.cad import DxfWriter
from rc_aircraft_design.viz import fuselage_mesh


def _build_concept(data: dict) -> ConventionalConcept:
    wm = Wing(**{k: v for k, v in data["wing_main"].items()})
    wh = Wing(**{k: v for k, v in data["wing_horiz"].items()})
    wv = Wing(**{k: v for k, v in data["wing_vert"].items()})
    fus = data["fuselage"]
    return ConventionalConcept(
        wing_main=wm, wing_horiz=wh, wing_vert=wv,
        fuselage_length=fus["length"],
        fuselage_stations=fus["stations"],
        fuselage_radii=fus["radii"],
    )


class TestExamplePlaneWorkflow:
    """Run through the full design workflow for each example plane."""

    def test_aero_analysis(self, plane_data):
        af_d = plane_data["airfoil"]
        af = LinearAirfoil(
            Cla=af_d["Cla"], alpha0_deg=af_d["alpha0_deg"],
            Cd0=af_d["Cd0"], Cdi_factor=af_d["Cdi_factor"],
        )
        result = af.analyze()
        assert result.LDmax > 0
        assert result.Clmax > 0

    def test_airfoil_generation(self, plane_data):
        code = plane_data["airfoil"]["code"]
        x, yu, yl = naca4(code)
        assert len(x) == 100
        assert x[0] == pytest.approx(0.0, abs=1e-12)
        assert x[-1] == pytest.approx(1.0, abs=1e-12)

    def test_wing_geometry(self, plane_data):
        concept = _build_concept(plane_data)
        wm = concept.wing_main

        assert wm.area > 0
        assert wm.aspect_ratio > 0

        mac = compute_mac(wm)
        assert mac.mac_length > 0
        assert mac.y_mac > 0

    def test_planform_coords(self, plane_data):
        concept = _build_concept(plane_data)
        for w in [concept.wing_main, concept.wing_horiz, concept.wing_vert]:
            x, y = planform_coords(w)
            assert len(x) == len(y)
            assert x[0] == pytest.approx(x[-1])  # closed polygon

    def test_stability(self, plane_data):
        concept = _build_concept(plane_data)
        result = analyze_stability(concept, X_cg=plane_data["cg_x"])
        assert isinstance(result.Vh, float)
        assert isinstance(result.static_margin, float)

    def test_constraints(self, plane_data):
        af = plane_data["airfoil"]
        c = plane_data["constraints"]
        bank_rad = np.radians(c["turn_bank_deg"])
        params = ConstraintParams(
            Cd_min=af["Cd0"], k=af["Cdi_factor"],
            turn_v=c["turn_v"], turn_n=1.0 / np.cos(bank_rad),
            climb_vv=c["climb_vv"], climb_v=c["climb_v"],
            cruise_v=c["cruise_v"], ceiling_h=c["ceiling_h"],
            to_Sg=c["to_Sg"],
        )
        result = analyze_constraints(params)
        assert result.envelope.min() > 0

    def test_span_loads(self, plane_data):
        wm = plane_data["wing_main"]
        result = compute_span_loads_simple(
            half_span=wm["span"] / 2,
            root_chord=wm["chord_root"],
            tip_chord=wm["chord_tip"],
            CL=0.5, velocity=plane_data["constraints"]["cruise_v"],
        )
        assert result.total_lift > 0
        assert result.shear[0] > 0
        assert result.bending[0] > 0

    def test_weight_estimate(self, plane_data):
        wd = plane_data["weight"]
        if wd["f_payload"] <= 0:
            pytest.skip("No payload fraction defined")
        we = WeightEstimate(
            m_payload_kg=wd["m_payload_kg"],
            f_payload=wd["f_payload"],
            v_cruise_ms=wd["v_cruise_ms"],
            endurance_s=wd["endurance_s"],
        )
        assert we.m_gross_kg >= 0
        assert we.W_gross_N >= 0

    def test_electric_power(self, plane_data):
        if plane_data["power"] is None:
            pytest.skip("No power system (glider)")
        p = plane_data["power"]
        eps = ElectricPowerSystem(
            motor_power_W=p["motor_power_W"],
            motor_efficiency=p["motor_efficiency"],
            prop_efficiency=p["prop_efficiency"],
            battery_voltage=p["battery_voltage"],
            battery_capacity_Ah=p["battery_capacity_Ah"],
        )
        assert eps.endurance_min > 0
        assert eps.thrust_N > 0

    def test_fuselage_mesh(self, plane_data):
        fus = plane_data["fuselage"]
        mesh = fuselage_mesh(stations=fus["stations"], radii=fus["radii"])
        assert mesh.vertices.shape[0] > 0
        assert mesh.indices.shape[0] > 0

    def test_dxf_export(self, plane_data):
        code = plane_data["airfoil"]["code"]
        x, yu, yl = naca4(code, n_points=30)
        concept = _build_concept(plane_data)
        px, py = planform_coords(concept.wing_main)

        dxf = DxfWriter()
        dxf.add_planform(px, py)
        dxf.add_airfoil(x, yu, yl, chord=concept.wing_main.chord_root)
        content = dxf.to_string()
        assert "AC1009" in content
        assert "PLANFORM" in content
        assert "AIRFOIL" in content
