"""Central callback registration — design pipeline execution."""

from __future__ import annotations

import traceback

import dash
import dash_bootstrap_components as dbc
import numpy as np
from dash import Input, Output, State, callback, no_update
from dash_iconify import DashIconify


def register_callbacks(app: dash.Dash):
    """Register all cross-page callbacks on the Dash app."""

    # ── Run design pipeline ─────────────────────────────────────────
    @app.callback(
        Output("store-design-result", "data"),
        Output("run-status", "children"),
        Input("btn-run-design", "n_clicks"),
        [
            State("cfg-payload-kg", "value"),
            State("cfg-payload-frac", "value"),
            State("cfg-cruise-v", "value"),
            State("cfg-endurance", "value"),
            State("cfg-altitude", "value"),
            State("cfg-climb-rate", "value"),
            State("cfg-turn-bank", "value"),
            State("cfg-to-roll", "value"),
            State("cfg-naca-code", "value"),
            State("cfg-cla", "value"),
            State("cfg-alpha0", "value"),
            State("cfg-cd0", "value"),
            State("cfg-cdi-factor", "value"),
            State("cfg-ar", "value"),
            State("cfg-tr", "value"),
            State("cfg-sweep", "value"),
            State("cfg-dihedral", "value"),
            State("cfg-vh", "value"),
            State("cfg-vv", "value"),
            State("cfg-sm", "value"),
            State("cfg-fuse-ld", "value"),
            State("cfg-motor-eff", "value"),
            State("cfg-prop-eff", "value"),
            State("cfg-batt-v", "value"),
            State("cfg-batt-ah", "value"),
        ],
        prevent_initial_call=True,
    )
    def run_design(
        n_clicks,
        payload_kg, payload_frac, cruise_v, endurance, altitude,
        climb_rate, turn_bank, to_roll,
        naca_code, cla, alpha0, cd0, cdi_factor,
        ar, tr, sweep, dihedral, vh, vv, sm, fuse_ld,
        motor_eff, prop_eff, batt_v, batt_ah,
    ):
        if not n_clicks:
            return no_update, no_update

        try:
            from rc_aircraft_design.passive import run_passive_design
            from rc_aircraft_design.wing.geometry import compute_mac
            from rc_aircraft_design.wing.loads import (
                compute_span_loads, elliptic_Cl, trapezoid_chord,
            )
            from rc_aircraft_design.utils.math_helpers import density_isa, dynamic_pressure

            assumptions = {
                "payload_kg": float(payload_kg),
                "payload_fraction": float(payload_frac),
                "cruise_speed_ms": float(cruise_v),
                "endurance_s": float(endurance),
                "altitude_m": float(altitude),
                "climb_rate_ms": float(climb_rate),
                "turn_bank_deg": float(turn_bank),
                "takeoff_ground_roll_m": float(to_roll),
            }
            airfoil_params = {
                "code": str(naca_code),
                "Cla": float(cla),
                "alpha0_deg": float(alpha0),
                "Cd0": float(cd0),
                "Cdi_factor": float(cdi_factor),
            }

            result = run_passive_design(
                assumptions,
                airfoil_params,
                AR_main=float(ar),
                TR_main=float(tr),
                Vh_target=float(vh),
                Vv_target=float(vv),
                motor_eff=float(motor_eff),
                prop_eff=float(prop_eff),
                battery_voltage=float(batt_v),
            )

            # Serialize to JSON-friendly dict
            data = _serialize_result(result, naca_code, batt_ah, cruise_v)

            # Compute span loads
            wm = result.concept.wing_main
            half_span = wm.span / 2
            n_pts = 60
            y = np.linspace(0, half_span, n_pts)
            chord = trapezoid_chord(y, half_span, wm.chord_root, wm.chord_tip)
            rho = density_isa(float(altitude))
            q_inf = dynamic_pressure(float(cruise_v), rho)
            CL_cruise = 0.45
            Cl_dist = elliptic_Cl(y, half_span, CL_cruise, wm.aspect_ratio)
            sl = compute_span_loads(y, chord, Cl_dist, q_inf)
            data["span_loads"] = {
                "y": sl.y.tolist(),
                "lift_per_span": sl.lift_per_span.tolist(),
                "shear": sl.shear.tolist(),
                "bending": sl.bending.tolist(),
                "total_lift": float(sl.total_lift),
            }

            ok_msg = dbc.Alert(
                [DashIconify(icon="mdi:check-circle", width=16), "  Design pipeline completed successfully!"],
                color="success", duration=5000,
            )
            return data, ok_msg

        except Exception as e:
            tb = traceback.format_exc()
            err_msg = dbc.Alert(
                [DashIconify(icon="mdi:alert-circle", width=16), f"  Error: {e}"],
                color="danger",
            )
            return no_update, err_msg

    # ── Auto-populate from preset ────────────────────────────────────
    @app.callback(
        [
            Output("cfg-payload-kg", "value"),
            Output("cfg-payload-frac", "value"),
            Output("cfg-cruise-v", "value"),
            Output("cfg-endurance", "value"),
            Output("cfg-altitude", "value"),
            Output("cfg-climb-rate", "value"),
            Output("cfg-turn-bank", "value"),
            Output("cfg-to-roll", "value"),
            Output("cfg-naca-code", "value"),
            Output("cfg-cla", "value"),
            Output("cfg-alpha0", "value"),
            Output("cfg-cd0", "value"),
            Output("cfg-cdi-factor", "value"),
        ],
        Input("store-aircraft-config", "data"),
        prevent_initial_call=True,
    )
    def populate_from_preset(config):
        if not config:
            return [no_update] * 13

        a = config.get("assumptions", {})
        af = config.get("airfoil", {})

        return [
            a.get("payload_kg", 0.25),
            a.get("payload_fraction", 0.25),
            a.get("cruise_speed_ms", 18.0),
            a.get("endurance_s", 600),
            a.get("altitude_m", 200),
            a.get("climb_rate_ms", 5.0),
            a.get("turn_bank_deg", 45),
            a.get("takeoff_ground_roll_m", 20.0),
            af.get("code", "2412"),
            af.get("Cla", 0.1),
            af.get("alpha0_deg", -5.0),
            af.get("Cd0", 0.02),
            af.get("Cdi_factor", 0.0398),
        ]

    # ── Sidebar active-link highlight ────────────────────────────────
    nav_ids = [
        "nav-dashboard", "nav-config", "nav-aero", "nav-constraints",
        "nav-geometry", "nav-stability", "nav-power", "nav-loads",
        "nav-workbench", "nav-manufacturing", "nav-export",
    ]
    nav_paths = [
        "/", "/config", "/aero", "/constraints",
        "/geometry", "/stability", "/power", "/loads",
        "/workbench", "/manufacturing", "/export",
    ]

    @app.callback(
        [Output(nid, "className") for nid in nav_ids],
        Input("url", "pathname"),
    )
    def highlight_nav(pathname):
        classes = []
        for p in nav_paths:
            if pathname == p:
                classes.append("nav-link-sidebar active")
            else:
                classes.append("nav-link-sidebar")
        return classes


def _serialize_result(result, naca_code, batt_ah, cruise_v):
    """Convert PassiveDesignResult to a JSON-serializable dict."""
    from rc_aircraft_design.wing.geometry import compute_mac

    aero = result.aero
    c = result.constraints
    stab = result.stability
    concept = result.concept
    ps = result.power_system

    # MAC for all surfaces
    mac_main = compute_mac(concept.wing_main)
    mac_htail = compute_mac(concept.wing_horiz)
    mac_vtail = compute_mac(concept.wing_vert)

    def _mac_dict(m):
        return {
            "mac_length": float(m.mac_length),
            "x_sweep": float(m.x_sweep),
            "y_mac": float(m.y_mac),
            "x_aero_focus": float(m.x_aero_focus),
            "chord_at_mac": float(m.chord_at_mac),
        }

    def _wing_dict(w):
        return {
            "chord_root": float(w.chord_root),
            "chord_tip": float(w.chord_tip),
            "span": float(w.span),
            "sweep_deg": float(w.sweep_deg),
            "dihedral_deg": float(w.dihedral_deg),
            "foil": w.foil,
            "type_": w.type_,
            "x": float(w.x),
            "y": float(w.y),
            "z": float(w.z),
            "area": float(w.area),
            "taper_ratio": float(w.taper_ratio),
            "aspect_ratio": float(w.aspect_ratio),
        }

    data = {
        "naca_code": str(naca_code),
        "preset_name": "Custom Design",

        # Aero
        "aero": {
            "alpha": aero.alpha.tolist(),
            "Cl": aero.Cl.tolist(),
            "Cd": aero.Cd.tolist(),
            "L_over_D": aero.L_over_D.tolist(),
            "alpha_Clmax": float(aero.alpha_Clmax),
            "Clmax": float(aero.Clmax),
            "alpha_Cdmin": float(aero.alpha_Cdmin),
            "Cdmin": float(aero.Cdmin),
            "alpha_LDmax": float(aero.alpha_LDmax),
            "LDmax": float(aero.LDmax),
        },
        "Cd_min": float(result.Cd_min),
        "k": float(result.k),
        "Cla": float(cla),
        "alpha0_deg": float(alpha0),
        "LDmax": float(aero.LDmax),

        # Constraints
        "constraints": {
            "W_S": c.W_S.tolist(),
            "turn": c.turn.tolist(),
            "climb": c.climb.tolist(),
            "cruise": c.cruise.tolist(),
            "ceiling": c.ceiling.tolist(),
            "takeoff": c.takeoff.tolist(),
            "envelope": c.envelope.tolist(),
        },
        "TW_opt": float(result.TW_opt),
        "WS_opt": float(result.WS_opt),

        # Weight & Power
        "m_gross_kg": float(result.m_gross_kg),
        "W_gross_N": float(result.W_gross_N),
        "S_wing": float(result.S_wing),
        "span_m": float(concept.wing_main.span),
        "thrust_req_N": float(result.thrust_req_N),
        "shaft_power_W": float(result.shaft_power_W),

        # Geometry
        "concept": {
            "wing_main": _wing_dict(concept.wing_main),
            "wing_horiz": _wing_dict(concept.wing_horiz),
            "wing_vert": _wing_dict(concept.wing_vert),
            "fuselage_length": float(concept.fuselage_length),
            "fuselage_stations": [float(x) for x in concept.fuselage_stations] if concept.fuselage_stations else None,
            "fuselage_radii": [float(x) for x in concept.fuselage_radii] if concept.fuselage_radii else None,
        },

        # MAC
        "mac_main": _mac_dict(mac_main),
        "mac_htail": _mac_dict(mac_htail),
        "mac_vtail": _mac_dict(mac_vtail),

        # Stability
        "stability": {
            "Vh": float(stab.Vh),
            "Vv": float(stab.Vv),
            "static_margin": float(stab.static_margin),
            "X_np": float(stab.X_np),
            "X_cg": float(stab.X_cg),
            "M_de": float(stab.M_de),
            "B": float(stab.B),
            "VvB": float(stab.VvB),
        },
        "X_cg": float(stab.X_cg),
        "X_np": float(stab.X_np),
        "static_margin": float(stab.static_margin),
        "Vh": float(stab.Vh),
        "Vv": float(stab.Vv),
        "stability_checks": result.stability_checks,
    }

    # Power system
    if ps:
        data["power_system"] = {
            "motor_power_W": float(ps.motor_power_W),
            "motor_efficiency": float(ps.motor_efficiency),
            "prop_efficiency": float(ps.prop_efficiency),
            "battery_voltage": float(ps.battery_voltage),
            "battery_capacity_Ah": float(ps.battery_capacity_Ah),
            "input_power_W": float(ps.input_power_W),
            "current_A": float(ps.current_A),
            "endurance_min": float(ps.endurance_min),
            "thrust_N": float(ps.thrust_N),
        }
        data["thrust_N"] = float(ps.thrust_N)
        data["endurance_min"] = float(ps.endurance_min)
    else:
        data["power_system"] = None
        data["thrust_N"] = 0
        data["endurance_min"] = 0

    return data
