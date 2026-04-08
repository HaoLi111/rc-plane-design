"""Passive design pipeline — derive a full aircraft from mission assumptions.

Implements the rAviExp forward-pass design methodology:
  Airfoil → Constraints (T/W vs W/S) → Weight/Power → Geometry → Stability

Each stage is pure-functional: outputs feed analytically into the next
with no iteration loops.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .aero.analysis import LinearAirfoil, AlphaAnalysis
from .constraints.analysis import ConstraintParams, ConstraintResult, analyze_constraints
from .power.propulsion import ElectricPowerSystem, WeightEstimate
from .stability.analysis import StabilityResult, analyze_stability, check_design_ranges
from .utils.math_helpers import density_isa
from .wing.geometry import Wing, ConventionalConcept, compute_mac, size_wing


@dataclass
class PassiveDesignResult:
    """Complete output of the passive design pipeline."""

    # Stage 1 — Aero
    aero: AlphaAnalysis
    Cd_min: float
    k: float

    # Stage 2 — Constraints
    constraints: ConstraintResult
    TW_opt: float
    WS_opt: float

    # Stage 3 — Weight & power
    m_gross_kg: float
    W_gross_N: float
    S_wing: float
    thrust_req_N: float
    shaft_power_W: float
    power_system: ElectricPowerSystem | None

    # Stage 4 — Geometry
    concept: ConventionalConcept

    # Stage 5 — Stability
    stability: StabilityResult
    stability_checks: dict[str, bool]


def run_passive_design(
    assumptions: dict,
    airfoil_params: dict,
    *,
    AR_main: float = 8.0,
    TR_main: float = 0.6,
    Vh_target: float = 0.45,
    Vv_target: float = 0.035,
    AR_horiz: float = 5.0,
    TR_horiz: float = 0.8,
    AR_vert: float = 1.5,
    TR_vert: float = 0.5,
    motor_eff: float = 0.80,
    prop_eff: float = 0.65,
    battery_voltage: float = 11.1,
) -> PassiveDesignResult:
    """Run the full passive design pipeline.

    Parameters
    ----------
    assumptions : dict with keys matching the "assumptions" block in mission JSON
    airfoil_params : dict with keys: code, Cla, alpha0_deg, Cd0, Cdi_factor
    AR_main, TR_main : main wing aspect ratio and taper ratio
    Vh_target, Vv_target : target tail volume coefficients
    motor_eff, prop_eff : efficiencies for power sizing
    battery_voltage : nominal battery voltage [V]
    """
    A = assumptions
    AF = airfoil_params

    # ── Stage 1: Aero ────────────────────────────────────────────────
    airfoil = LinearAirfoil(
        Cla=AF["Cla"],
        alpha0_deg=AF["alpha0_deg"],
        Cd0=AF["Cd0"],
        Cdi_factor=AF["Cdi_factor"],
    )
    aero = airfoil.analyze()
    Cd_min = AF["Cd0"]
    k = AF["Cdi_factor"]

    # ── Stage 2: Constraints ─────────────────────────────────────────
    bank_rad = np.radians(A["turn_bank_deg"])
    rho = density_isa(A["altitude_m"])

    params = ConstraintParams(
        Cd_min=Cd_min,
        k=k,
        rho=rho,
        W_S=np.arange(5, 120.1, 0.5),
        turn_v=A["cruise_speed_ms"],
        turn_n=1.0 / np.cos(bank_rad),
        climb_vv=A["climb_rate_ms"],
        climb_v=A["cruise_speed_ms"] * 0.7,
        cruise_v=A["cruise_speed_ms"],
        ceiling_h=A["altitude_m"] * 2,
        to_Sg=A["takeoff_ground_roll_m"],
    )
    constraints = analyze_constraints(params)

    envelope = constraints.envelope
    idx_opt = int(np.argmin(envelope))
    TW_opt = float(envelope[idx_opt])
    WS_opt = float(params.W_S[idx_opt])

    # ── Stage 3: Weight & Power ──────────────────────────────────────
    weight = WeightEstimate(
        m_payload_kg=A["payload_kg"],
        f_payload=A["payload_fraction"],
        v_cruise_ms=A["cruise_speed_ms"],
        endurance_s=A["endurance_s"],
    )
    m_gross = weight.m_gross_kg
    W_gross = weight.W_gross_N
    S_wing = W_gross / WS_opt

    thrust_req = TW_opt * W_gross
    power_req = thrust_req * A["cruise_speed_ms"]
    shaft_power = power_req / prop_eff

    # Power system (skip for gliders with zero payload fraction effectively no motor)
    is_glider = A["payload_kg"] == 0 and A["payload_fraction"] <= 0.1
    if not is_glider:
        electrical_power = shaft_power / motor_eff
        flight_time_hr = A["endurance_s"] / 3600
        battery_capacity = electrical_power / battery_voltage * flight_time_hr
        eps = ElectricPowerSystem(
            motor_power_W=shaft_power,
            motor_efficiency=motor_eff,
            prop_efficiency=prop_eff,
            battery_voltage=battery_voltage,
            battery_capacity_Ah=max(battery_capacity, 0.5),
        )
    else:
        eps = None

    # ── Stage 4: Geometry ────────────────────────────────────────────
    b_main, cr_main, ct_main = size_wing(S_wing, AR_main, TR_main)
    fuse_length = max(b_main * 0.75, 0.15)  # floor for very small aircraft

    # Tail lever arm scales with fuselage (floor avoids zero-division)
    tail_lever = max(fuse_length * 0.60, 0.10)

    wm = Wing(
        cr_main, ct_main, b_main,
        dihedral_deg=5.0, foil=AF["code"],
        type_=0, x=fuse_length * 0.22,
    )
    mac_main = compute_mac(wm)

    S_horiz = Vh_target * mac_main.mac_length * S_wing / tail_lever
    b_h, cr_h, ct_h = size_wing(S_horiz, AR_horiz, TR_horiz)

    S_vert = Vv_target * b_main * S_wing / tail_lever
    b_v, cr_v, ct_v = size_wing(S_vert, AR_vert, TR_vert)

    horiz_x = wm.x + tail_lever
    vert_x = horiz_x - 0.02

    wh = Wing(cr_h, ct_h, b_h, foil="0009", type_=0, x=horiz_x)
    wv = Wing(cr_v, ct_v, b_v, foil="0009", type_=2, x=vert_x, sweep_deg=25.0)

    concept = ConventionalConcept(
        wing_main=wm, wing_horiz=wh, wing_vert=wv,
        fuselage_length=fuse_length,
    )

    # ── Stage 5: Stability ───────────────────────────────────────────
    # Place CG for a target static margin of −0.10 (10% MAC ahead of NP).
    # First, get the neutral point from a dummy CG, then position CG properly.
    dummy_stab = analyze_stability(concept, X_cg=0.0)
    X_np = dummy_stab.X_np
    target_SM = -0.10  # negative = CG ahead of NP = stable
    X_cg = X_np + target_SM * mac_main.mac_length
    stability = analyze_stability(concept, X_cg=X_cg)
    checks = check_design_ranges(stability)

    return PassiveDesignResult(
        aero=aero,
        Cd_min=Cd_min,
        k=k,
        constraints=constraints,
        TW_opt=TW_opt,
        WS_opt=WS_opt,
        m_gross_kg=m_gross,
        W_gross_N=W_gross,
        S_wing=S_wing,
        thrust_req_N=thrust_req,
        shaft_power_W=shaft_power,
        power_system=eps,
        concept=concept,
        stability=stability,
        stability_checks=checks,
    )
