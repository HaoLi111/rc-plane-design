"""Stage executors — each pipeline stage as a standalone JSON→JSON function.

Every stage function takes a plain dict (JSON-deserializable) and returns
a plain dict (JSON-serializable).  This replaces the .RData workflow
from rAviExp with portable JSON at every boundary.

Stages
------
1. aero       — airfoil params → alpha analysis + Cl/Cd curves
2. constraints— Cd_min, k, mission params → T/W vs W/S envelope
3. weight     — payload, fraction, cruise → mass & power sizing
4. geometry   — wing area, AR, TR, Vh, Vv → ConventionalConcept
5. stability  — concept + CG → Vh, Vv, SM, B
6. loads      — wing geometry + flight cond → span loads
7. climb      — Cl, Cd, rho, S, W → climb performance
8. vn_diagram — Clmax, W/S, rho → V-n envelope
9. speed_lift — airfoil + wing → speed vs lift contour

Each can be called independently from the Workbench page or chained
in the full pipeline.  JSON files exported from any stage can be
re-imported into another session (replaces .RData).
"""

from __future__ import annotations

import numpy as np


# ── Helpers ──────────────────────────────────────────────────────────────

def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── Stage 1: Aero ───────────────────────────────────────────────────────

STAGE_AERO_SCHEMA = {
    "Cla": 0.1,
    "alpha0_deg": -5.0,
    "Cd0": 0.02,
    "Cdi_factor": 0.0398,
    "alpha_min": -5.0,
    "alpha_max": 20.0,
    "alpha_step": 0.5,
}


def run_stage_aero(params: dict) -> dict:
    """Stage 1 — Airfoil alpha sweep.

    Input JSON: {Cla, alpha0_deg, Cd0, Cdi_factor, alpha_min, alpha_max, alpha_step}
    Output JSON: {alpha[], Cl[], Cd[], L_over_D[], Clmax, Cdmin, LDmax, ...}
    """
    from rc_aircraft_design.aero.analysis import LinearAirfoil

    af = LinearAirfoil(
        Cla=_float(params.get("Cla", 0.1)),
        alpha0_deg=_float(params.get("alpha0_deg", -5.0)),
        Cd0=_float(params.get("Cd0", 0.02)),
        Cdi_factor=_float(params.get("Cdi_factor", 0.0398)),
    )
    alpha_range = np.arange(
        _float(params.get("alpha_min", -5)),
        _float(params.get("alpha_max", 20)) + 0.01,
        _float(params.get("alpha_step", 0.5)),
    )
    aero = af.analyze(alpha_range)

    return {
        "_stage": "aero",
        "input": params,
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
        "Cd_min": _float(params.get("Cd0", 0.02)),
        "k": _float(params.get("Cdi_factor", 0.0398)),
    }


# ── Stage 2: Constraints ───────────────────────────────────────────────

STAGE_CONSTRAINTS_SCHEMA = {
    "Cd_min": 0.02,
    "k": 0.04,
    "rho": 1.225,
    "cruise_v": 18.0,
    "climb_rate": 5.0,
    "climb_v": 12.6,
    "turn_v": 18.0,
    "turn_bank_deg": 45,
    "ceiling_h": 400,
    "to_Sg": 20.0,
    "WS_min": 5,
    "WS_max": 120,
    "WS_step": 0.5,
}


def run_stage_constraints(params: dict) -> dict:
    """Stage 2 — T/W vs W/S constraint envelope.

    Input JSON: {Cd_min, k, rho, cruise_v, climb_rate, climb_v,
                  turn_v, turn_bank_deg, ceiling_h, to_Sg, WS_min/max/step}
    Output JSON: {W_S[], turn[], climb[], cruise[], ceiling[], takeoff[],
                  envelope[], TW_opt, WS_opt}
    """
    from rc_aircraft_design.constraints.analysis import ConstraintParams, analyze_constraints

    bank_deg = _float(params.get("turn_bank_deg", 45))
    turn_n = 1.0 / np.cos(np.radians(bank_deg))

    cp = ConstraintParams(
        Cd_min=_float(params.get("Cd_min", 0.02)),
        k=_float(params.get("k", 0.04)),
        rho=_float(params.get("rho", 1.225)),
        W_S=np.arange(
            _float(params.get("WS_min", 5)),
            _float(params.get("WS_max", 120)) + 0.01,
            _float(params.get("WS_step", 0.5)),
        ),
        turn_v=_float(params.get("turn_v", 18)),
        turn_n=turn_n,
        climb_vv=_float(params.get("climb_rate", 5)),
        climb_v=_float(params.get("climb_v", 12.6)),
        cruise_v=_float(params.get("cruise_v", 18)),
        ceiling_h=_float(params.get("ceiling_h", 400)),
        to_Sg=_float(params.get("to_Sg", 20)),
    )
    c = analyze_constraints(cp)

    envelope = c.envelope
    idx = int(np.argmin(envelope))

    return {
        "_stage": "constraints",
        "input": params,
        "W_S": c.W_S.tolist(),
        "turn": c.turn.tolist(),
        "climb": c.climb.tolist(),
        "cruise": c.cruise.tolist(),
        "ceiling": c.ceiling.tolist(),
        "takeoff": c.takeoff.tolist(),
        "envelope": envelope.tolist(),
        "TW_opt": float(envelope[idx]),
        "WS_opt": float(c.W_S[idx]),
    }


# ── Stage 3: Weight & Power ────────────────────────────────────────────

STAGE_WEIGHT_SCHEMA = {
    "payload_kg": 0.25,
    "payload_fraction": 0.25,
    "cruise_speed_ms": 18.0,
    "endurance_s": 600,
    "TW_opt": 0.12,
    "WS_opt": 50.0,
    "motor_eff": 0.80,
    "prop_eff": 0.65,
    "battery_voltage": 11.1,
}


def run_stage_weight(params: dict) -> dict:
    """Stage 3 — Weight estimate & electric power sizing.

    Input JSON: {payload_kg, payload_fraction, cruise_speed_ms, endurance_s,
                  TW_opt, WS_opt, motor_eff, prop_eff, battery_voltage}
    Output JSON: {m_gross_kg, W_gross_N, S_wing, thrust_req_N, shaft_power_W,
                  power_system: {...}}
    """
    from rc_aircraft_design.power.propulsion import WeightEstimate, ElectricPowerSystem

    payload_kg = _float(params.get("payload_kg", 0.25))
    payload_frac = _float(params.get("payload_fraction", 0.25))
    cruise_v = _float(params.get("cruise_speed_ms", 18))
    endurance_s = _float(params.get("endurance_s", 600))
    TW_opt = _float(params.get("TW_opt", 0.12))
    WS_opt = _float(params.get("WS_opt", 50))
    motor_eff = _float(params.get("motor_eff", 0.80))
    prop_eff = _float(params.get("prop_eff", 0.65))
    batt_v = _float(params.get("battery_voltage", 11.1))

    w = WeightEstimate(
        m_payload_kg=payload_kg,
        f_payload=payload_frac,
        v_cruise_ms=cruise_v,
        endurance_s=endurance_s,
    )
    m_gross = w.m_gross_kg
    W_gross = w.W_gross_N
    S_wing = W_gross / WS_opt
    thrust_req = TW_opt * W_gross
    shaft_power = thrust_req * cruise_v / prop_eff

    eps = ElectricPowerSystem(
        motor_power_W=shaft_power,
        motor_efficiency=motor_eff,
        prop_efficiency=prop_eff,
        battery_voltage=batt_v,
        battery_capacity_Ah=max(shaft_power / motor_eff / batt_v * (endurance_s / 3600), 0.5),
    )

    return {
        "_stage": "weight",
        "input": params,
        "m_gross_kg": float(m_gross),
        "W_gross_N": float(W_gross),
        "S_wing": float(S_wing),
        "thrust_req_N": float(thrust_req),
        "shaft_power_W": float(shaft_power),
        "power_system": {
            "motor_power_W": float(eps.motor_power_W),
            "motor_efficiency": float(eps.motor_efficiency),
            "prop_efficiency": float(eps.prop_efficiency),
            "battery_voltage": float(eps.battery_voltage),
            "battery_capacity_Ah": float(eps.battery_capacity_Ah),
            "input_power_W": float(eps.input_power_W),
            "current_A": float(eps.current_A),
            "endurance_min": float(eps.endurance_min),
            "thrust_N": float(eps.thrust_N),
        },
    }


# ── Stage 4: Geometry ──────────────────────────────────────────────────

STAGE_GEOMETRY_SCHEMA = {
    "S_wing": 0.2,
    "AR_main": 8.0,
    "TR_main": 0.6,
    "sweep_deg": 0.0,
    "dihedral_deg": 5.0,
    "foil": "2412",
    "Vh_target": 0.45,
    "Vv_target": 0.035,
    "AR_horiz": 5.0,
    "TR_horiz": 0.8,
    "AR_vert": 1.5,
    "TR_vert": 0.5,
    "fuse_length_ratio": 0.75,
    "wing_x_ratio": 0.22,
}


def run_stage_geometry(params: dict) -> dict:
    """Stage 4 — Size wing, tails, fuselage from area + design ratios.

    Input JSON: {S_wing, AR_main, TR_main, foil, Vh_target, Vv_target, ...}
    Output JSON: {concept: {wing_main, wing_horiz, wing_vert, fuselage_*},
                  mac_main, mac_htail, mac_vtail}
    """
    from rc_aircraft_design.wing.geometry import Wing, ConventionalConcept, compute_mac, size_wing

    S_wing = _float(params.get("S_wing", 0.2))
    AR = _float(params.get("AR_main", 8))
    TR = _float(params.get("TR_main", 0.6))
    foil = str(params.get("foil", "2412"))
    sweep = _float(params.get("sweep_deg", 0))
    dihedral = _float(params.get("dihedral_deg", 5))
    Vh_target = _float(params.get("Vh_target", 0.45))
    Vv_target = _float(params.get("Vv_target", 0.035))

    b, cr, ct = size_wing(S_wing, AR, TR)
    fuse_len = max(b * _float(params.get("fuse_length_ratio", 0.75)), 0.15)
    tail_lever = max(fuse_len * 0.60, 0.10)

    wm = Wing(cr, ct, b, sweep_deg=sweep, dihedral_deg=dihedral, foil=foil,
              type_=0, x=fuse_len * _float(params.get("wing_x_ratio", 0.22)))
    mac_main = compute_mac(wm)

    S_h = Vh_target * mac_main.mac_length * S_wing / tail_lever
    b_h, cr_h, ct_h = size_wing(S_h, _float(params.get("AR_horiz", 5)), _float(params.get("TR_horiz", 0.8)))
    horiz_x = wm.x + tail_lever

    S_v = Vv_target * b * S_wing / tail_lever
    b_v, cr_v, ct_v = size_wing(S_v, _float(params.get("AR_vert", 1.5)), _float(params.get("TR_vert", 0.5)))

    wh = Wing(cr_h, ct_h, b_h, foil="0009", type_=0, x=horiz_x)
    wv = Wing(cr_v, ct_v, b_v, foil="0009", type_=2, x=horiz_x - 0.02, sweep_deg=25)

    concept = ConventionalConcept(wing_main=wm, wing_horiz=wh, wing_vert=wv, fuselage_length=fuse_len)
    mac_h = compute_mac(wh)
    mac_v = compute_mac(wv)

    def _w(w):
        return {"chord_root": float(w.chord_root), "chord_tip": float(w.chord_tip),
                "span": float(w.span), "sweep_deg": float(w.sweep_deg),
                "dihedral_deg": float(w.dihedral_deg), "foil": w.foil,
                "type_": w.type_, "x": float(w.x), "y": float(w.y), "z": float(w.z),
                "area": float(w.area), "taper_ratio": float(w.taper_ratio),
                "aspect_ratio": float(w.aspect_ratio)}

    def _m(m):
        return {"mac_length": float(m.mac_length), "x_sweep": float(m.x_sweep),
                "y_mac": float(m.y_mac), "x_aero_focus": float(m.x_aero_focus),
                "chord_at_mac": float(m.chord_at_mac)}

    return {
        "_stage": "geometry",
        "input": params,
        "concept": {"wing_main": _w(wm), "wing_horiz": _w(wh), "wing_vert": _w(wv),
                     "fuselage_length": float(fuse_len), "fuselage_stations": None, "fuselage_radii": None},
        "mac_main": _m(mac_main),
        "mac_htail": _m(mac_h),
        "mac_vtail": _m(mac_v),
    }


# ── Stage 5: Stability ─────────────────────────────────────────────────

STAGE_STABILITY_SCHEMA = {
    "_comment": "Requires a 'concept' dict from stage 4 (geometry).",
    "X_cg": 0.30,
    "Cl_operating": 0.45,
    "SM_target": -0.10,
}


def run_stage_stability(params: dict) -> dict:
    """Stage 5 — Stability analysis on an existing concept.

    Input JSON: {concept: {...}, X_cg OR SM_target, Cl_operating}
    Output JSON: {Vh, Vv, static_margin, X_np, X_cg, B, M_de, VvB, checks}
    """
    from rc_aircraft_design.wing.geometry import Wing, ConventionalConcept, compute_mac
    from rc_aircraft_design.stability.analysis import analyze_stability, check_design_ranges

    concept_d = params["concept"]

    def _wing(d) -> Wing:
        return Wing(chord_root=d["chord_root"], chord_tip=d["chord_tip"],
                    span=d["span"], sweep_deg=d.get("sweep_deg", 0),
                    dihedral_deg=d.get("dihedral_deg", 0), foil=d.get("foil", "0012"),
                    type_=d.get("type_", 0), x=d.get("x", 0), y=d.get("y", 0), z=d.get("z", 0))

    wm = _wing(concept_d["wing_main"])
    wh = _wing(concept_d["wing_horiz"])
    wv = _wing(concept_d["wing_vert"])
    concept = ConventionalConcept(
        wing_main=wm, wing_horiz=wh, wing_vert=wv,
        fuselage_length=_float(concept_d.get("fuselage_length", 1.0)),
    )

    Cl = _float(params.get("Cl_operating", 0.45))

    # If SM_target given (no explicit X_cg), compute CG for target margin
    if "X_cg" in params and params["X_cg"] is not None:
        X_cg = _float(params["X_cg"])
    else:
        mac_m = compute_mac(wm)
        dummy = analyze_stability(concept, X_cg=0.0, Cl=Cl)
        SM_target = _float(params.get("SM_target", -0.10))
        X_cg = dummy.X_np + SM_target * mac_m.mac_length

    stab = analyze_stability(concept, X_cg=X_cg, Cl=Cl)
    checks = check_design_ranges(stab)

    return {
        "_stage": "stability",
        "input": {k: v for k, v in params.items() if k != "concept"},
        "Vh": float(stab.Vh),
        "Vv": float(stab.Vv),
        "static_margin": float(stab.static_margin),
        "X_np": float(stab.X_np),
        "X_cg": float(stab.X_cg),
        "M_de": float(stab.M_de),
        "B": float(stab.B),
        "VvB": float(stab.VvB),
        "stability_checks": checks,
    }


# ── Stage 6: Span Loads ────────────────────────────────────────────────

STAGE_LOADS_SCHEMA = {
    "half_span": 0.75,
    "chord_root": 0.25,
    "chord_tip": 0.15,
    "CL": 0.45,
    "velocity": 18.0,
    "rho": 1.225,
    "n_stations": 60,
    "wing_mass_kg": 0.0,
}


def run_stage_loads(params: dict) -> dict:
    """Stage 6 — Spanwise lift, shear, bending moment.

    Input JSON: {half_span, chord_root, chord_tip, CL, velocity, rho, ...}
    Output JSON: {y[], chord[], lift_per_span[], shear[], bending[], total_lift}
    """
    from rc_aircraft_design.wing.loads import compute_span_loads_simple

    sl = compute_span_loads_simple(
        half_span=_float(params.get("half_span", 0.75)),
        root_chord=_float(params.get("chord_root", 0.25)),
        tip_chord=_float(params.get("chord_tip", 0.15)),
        CL=_float(params.get("CL", 0.45)),
        velocity=_float(params.get("velocity", 18)),
        rho=_float(params.get("rho", 1.225)),
        n_stations=int(params.get("n_stations", 60)),
        wing_mass_kg=_float(params.get("wing_mass_kg", 0)),
    )

    return {
        "_stage": "loads",
        "input": params,
        "y": sl.y.tolist(),
        "chord": sl.chord.tolist(),
        "lift_per_span": sl.lift_per_span.tolist(),
        "shear": sl.shear.tolist(),
        "bending": sl.bending.tolist(),
        "torsion": sl.torsion.tolist() if sl.torsion is not None else None,
        "total_lift": float(sl.total_lift),
    }


# ── Stage 7: Climb Analysis ────────────────────────────────────────────

STAGE_CLIMB_SCHEMA = {
    "Cl": 0.6,
    "Cd": 0.04,
    "rho": 1.225,
    "S": 0.20,
    "W": 9.81,
    "theta_max": 60,
}


def run_stage_climb(params: dict) -> dict:
    """Stage 7 — Climb performance across flight-path angles.

    Input JSON: {Cl, Cd, rho, S, W, theta_max}
    Output JSON: {theta_deg[], v[], vx[], vy[], thrust[], power[]}
    """
    from rc_aircraft_design.aero.analysis import climb_analysis

    theta_range = np.arange(0, _float(params.get("theta_max", 60)) + 0.5, 1.0)
    ca = climb_analysis(
        Cl=_float(params.get("Cl", 0.6)),
        Cd=_float(params.get("Cd", 0.04)),
        rho=_float(params.get("rho", 1.225)),
        S=_float(params.get("S", 0.20)),
        W=_float(params.get("W", 9.81)),
        theta_range_deg=theta_range,
    )

    return {
        "_stage": "climb",
        "input": params,
        "theta_deg": ca.theta_deg.tolist(),
        "v": ca.v.tolist(),
        "vx": ca.vx.tolist(),
        "vy": ca.vy.tolist(),
        "thrust": ca.thrust.tolist(),
        "power": ca.power.tolist(),
    }


# ── Stage 8: V-n Diagram ──────────────────────────────────────────────

STAGE_VN_SCHEMA = {
    "Clmax_pos": 1.5,
    "Clmax_neg": -0.8,
    "W_over_S": 50.0,
    "rho": 1.225,
    "n_limit_pos": 3.8,
    "n_limit_neg": -1.5,
    "v_max": 60.0,
}


def run_stage_vn(params: dict) -> dict:
    """Stage 8 — V-n (gust/maneuver) envelope.

    Input JSON: {Clmax_pos, Clmax_neg, W_over_S, rho, n_limit_pos, n_limit_neg, v_max}
    Output JSON: {v[], n_pos[], n_neg[], n_limit_pos, n_limit_neg}
    """
    from rc_aircraft_design.aero.analysis import load_analysis

    v_range = np.linspace(0, _float(params.get("v_max", 60)), 500)
    la = load_analysis(
        Clmax_pos=_float(params.get("Clmax_pos", 1.5)),
        Clmax_neg=_float(params.get("Clmax_neg", -0.8)),
        W_over_S=_float(params.get("W_over_S", 50)),
        rho=_float(params.get("rho", 1.225)),
        n_limit_pos=_float(params.get("n_limit_pos", 3.8)),
        n_limit_neg=_float(params.get("n_limit_neg", -1.5)),
        v_range=v_range,
    )

    return {
        "_stage": "vn_diagram",
        "input": params,
        "v": la.v.tolist(),
        "n_pos": la.n_pos.tolist(),
        "n_neg": la.n_neg.tolist(),
        "n_limit_pos": float(la.n_limit_pos),
        "n_limit_neg": float(la.n_limit_neg),
    }


# ── Stage 9: Speed–Lift Contour ────────────────────────────────────────

STAGE_SPEED_LIFT_SCHEMA = {
    "Cla": 0.1,
    "alpha0_deg": -5.0,
    "Cd0": 0.02,
    "Cdi_factor": 0.0398,
    "stall_alpha_deg": 15.0,
    "rho": 1.225,
    "S": 0.20,
    "W": 9.81,
    "v_min": 3.0,
    "v_max": 40.0,
    "alpha_min": -2.0,
    "alpha_max": 15.0,
}


def run_stage_speed_lift(params: dict) -> dict:
    """Stage 9 — Speed vs alpha contour: Lift force, stall boundary, L=W line.

    Computes a 2D grid of (speed, alpha) → Lift [N] and marks where
    the aircraft stalls (alpha > alpha_stall) and where L = W.

    Input JSON: {Cla, alpha0_deg, Cd0, Cdi_factor, stall_alpha_deg,
                  rho, S, W, v_min, v_max, alpha_min, alpha_max}
    Output JSON: {v[], alpha[], Lift_grid[][], stall_alpha, stall_speed_at_1g,
                  level_flight_alpha[]}
    """
    from rc_aircraft_design.aero.analysis import LinearAirfoil

    Cla = _float(params.get("Cla", 0.1))
    alpha0 = _float(params.get("alpha0_deg", -5.0))
    Cd0 = _float(params.get("Cd0", 0.02))
    k = _float(params.get("Cdi_factor", 0.0398))
    stall_alpha = _float(params.get("stall_alpha_deg", 15.0))
    rho = _float(params.get("rho", 1.225))
    S = _float(params.get("S", 0.20))
    W = _float(params.get("W", 9.81))

    v_arr = np.linspace(_float(params.get("v_min", 3)), _float(params.get("v_max", 40)), 80)
    alpha_arr = np.linspace(_float(params.get("alpha_min", -2)), _float(params.get("alpha_max", 15)), 70)

    af = LinearAirfoil(Cla=Cla, alpha0_deg=alpha0, Cd0=Cd0, Cdi_factor=k)

    # 2D grid: Lift = q * S * Cl(alpha)
    V, A = np.meshgrid(v_arr, alpha_arr)
    q = 0.5 * rho * V ** 2
    Cl = af.Cl(A)
    Lift = q * S * Cl
    Drag = q * S * af.Cd(A)

    # Stall speed at 1g: V_stall = sqrt(2W / (rho * S * Cl_stall))
    Cl_stall = af.Cl(stall_alpha)
    v_stall_1g = float(np.sqrt(2 * W / (rho * S * Cl_stall))) if Cl_stall > 0 else 0

    # Level-flight alpha for each speed: Cl_req = W / (q * S) → alpha = alpha0 + Cl/Cla
    q_1d = 0.5 * rho * v_arr ** 2
    Cl_req = W / (q_1d * S)
    alpha_level = alpha0 + Cl_req / Cla  # level-flight alpha for each speed

    return {
        "_stage": "speed_lift",
        "input": params,
        "v": v_arr.tolist(),
        "alpha": alpha_arr.tolist(),
        "Lift_grid": Lift.tolist(),
        "Drag_grid": Drag.tolist(),
        "stall_alpha_deg": stall_alpha,
        "stall_speed_1g_ms": v_stall_1g,
        "level_flight_alpha": alpha_level.tolist(),
        "Cl_stall": float(Cl_stall),
    }


# ── Registry ────────────────────────────────────────────────────────────

STAGES = {
    "aero": {
        "name": "Aerodynamic Analysis",
        "desc": "Airfoil alpha sweep → Cl, Cd, L/D curves",
        "icon": "mdi:airplane",
        "fn": run_stage_aero,
        "schema": STAGE_AERO_SCHEMA,
    },
    "constraints": {
        "name": "Constraint Analysis",
        "desc": "T/W vs W/S feasibility envelope from mission requirements",
        "icon": "mdi:chart-scatter-plot",
        "fn": run_stage_constraints,
        "schema": STAGE_CONSTRAINTS_SCHEMA,
    },
    "weight": {
        "name": "Weight & Power",
        "desc": "Mass budget, electric system sizing, endurance",
        "icon": "mdi:battery-charging",
        "fn": run_stage_weight,
        "schema": STAGE_WEIGHT_SCHEMA,
    },
    "geometry": {
        "name": "Geometry Sizing",
        "desc": "Wing, tail, fuselage from area, AR, taper, tail volumes",
        "icon": "mdi:cube-outline",
        "fn": run_stage_geometry,
        "schema": STAGE_GEOMETRY_SCHEMA,
    },
    "stability": {
        "name": "Stability & Control",
        "desc": "CG, neutral point, static margin, spiral stability",
        "icon": "mdi:scale-balance",
        "fn": run_stage_stability,
        "schema": STAGE_STABILITY_SCHEMA,
    },
    "loads": {
        "name": "Span Loads",
        "desc": "Spanwise lift, shear force, bending moment distribution",
        "icon": "mdi:chart-bell-curve-cumulative",
        "fn": run_stage_loads,
        "schema": STAGE_LOADS_SCHEMA,
    },
    "climb": {
        "name": "Climb Analysis",
        "desc": "Speed, thrust, power across flight-path angles θ",
        "icon": "mdi:trending-up",
        "fn": run_stage_climb,
        "schema": STAGE_CLIMB_SCHEMA,
    },
    "vn_diagram": {
        "name": "V-n Diagram",
        "desc": "Maneuver & gust load envelope (V-G diagram)",
        "icon": "mdi:chart-line-variant",
        "fn": run_stage_vn,
        "schema": STAGE_VN_SCHEMA,
    },
    "speed_lift": {
        "name": "Speed–Lift Contour",
        "desc": "Lift force contour over (speed × alpha), stall boundary, L=W",
        "icon": "mdi:chart-areaspline",
        "fn": run_stage_speed_lift,
        "schema": STAGE_SPEED_LIFT_SCHEMA,
    },
}
