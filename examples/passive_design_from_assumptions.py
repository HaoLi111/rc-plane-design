"""Passive design from assumptions — full aircraft from ~10 parameters.

Demonstrates the rAviExp "passive design" pipeline where a complete RC aircraft
is derived from a handful of mission assumptions with NO iteration loops.
Each stage feeds forward analytically into the next:

  Airfoil assumptions → Constraint analysis (T/W vs W/S)
       → Weight & power sizing → Wing geometry → Stability check

Run with:  uv run python examples/passive_design_from_assumptions.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rc_aircraft_design.aero.analysis import LinearAirfoil, k_factor, oswald_efficiency
from rc_aircraft_design.constraints.analysis import (
    ConstraintParams,
    analyze_constraints,
)
from rc_aircraft_design.power.propulsion import ElectricPowerSystem, WeightEstimate
from rc_aircraft_design.wing.geometry import (
    Wing,
    ConventionalConcept,
    size_wing,
    compute_mac,
)
from rc_aircraft_design.stability.analysis import (
    analyze_stability,
    check_design_ranges,
)
from rc_aircraft_design.utils.math_helpers import density_isa

# ── Load assumptions ─────────────────────────────────────────────────
ASSUMPTIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "examples" / "passive_sport_flyer.json"
assumptions = json.loads(ASSUMPTIONS_FILE.read_text(encoding="utf-8"))
A = assumptions["assumptions"]
AF = assumptions["airfoil"]


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =====================================================================
# Stage 1 — Aerodynamic analysis (from airfoil assumptions)
# =====================================================================
banner("STAGE 1: Aerodynamic Analysis")

airfoil = LinearAirfoil(
    Cla=AF["Cla"],
    alpha0_deg=AF["alpha0_deg"],
    Cd0=AF["Cd0"],
    Cdi_factor=AF["Cdi_factor"],
)
aero = airfoil.analyze()

print(f"  Airfoil model:  Cl = {AF['Cla']}·(α − ({AF['alpha0_deg']}°))")
print(f"                  Cd = {AF['Cd0']} + {AF['Cdi_factor']}·Cl²")
print(f"  CL_max  = {aero.Clmax:.3f}  at α = {aero.alpha_Clmax:.1f}°")
print(f"  CD_min  = {aero.Cdmin:.4f}")
print(f"  L/D_max = {aero.LDmax:.1f}  at α = {aero.alpha_LDmax:.1f}°")

# Key outputs that feed into Stage 2
Cd_min = AF["Cd0"]
k = AF["Cdi_factor"]


# =====================================================================
# Stage 2 — Constraint analysis (mission → T/W vs W/S)
# =====================================================================
banner("STAGE 2: Constraint Analysis (T/W vs W/S)")

bank_rad = np.radians(A["turn_bank_deg"])
rho = density_isa(A["altitude_m"])

params = ConstraintParams(
    Cd_min=Cd_min,
    k=k,
    rho=rho,
    W_S=np.arange(5, 80.1, 0.5),
    turn_v=A["cruise_speed_ms"],
    turn_n=1.0 / np.cos(bank_rad),
    climb_vv=A["climb_rate_ms"],
    climb_v=A["cruise_speed_ms"] * 0.7,  # climb at 70% of cruise
    cruise_v=A["cruise_speed_ms"],
    ceiling_h=A["altitude_m"] * 2,  # service ceiling = 2× operating altitude
    to_Sg=A["takeoff_ground_roll_m"],
)
constraints = analyze_constraints(params)

# Find the optimal design point: minimum T/W on the envelope
envelope = constraints.envelope
idx_opt = int(np.argmin(envelope))
TW_opt = float(envelope[idx_opt])
WS_opt = float(params.W_S[idx_opt])

print(f"  Air density at {A['altitude_m']} m: ρ = {rho:.4f} kg/m³")
print(f"  Turn load factor:  n = {1/np.cos(bank_rad):.2f}  ({A['turn_bank_deg']}° bank)")
print(f"  Climb speed:       {params.climb_v:.1f} m/s  at {A['climb_rate_ms']} m/s vertical")
print(f"  ─────────────────────────────────")
print(f"  Optimal design point:")
print(f"    T/W = {TW_opt:.3f}")
print(f"    W/S = {WS_opt:.1f} N/m²")


# =====================================================================
# Stage 3 — Weight & power sizing
# =====================================================================
banner("STAGE 3: Weight & Power Sizing")

weight = WeightEstimate(
    m_payload_kg=A["payload_kg"],
    f_payload=A["payload_fraction"],
    v_cruise_ms=A["cruise_speed_ms"],
    endurance_s=A["endurance_s"],
)

m_gross = weight.m_gross_kg
W_gross = weight.W_gross_N

# Required wing area from W/S
S_wing = W_gross / WS_opt

# Required thrust and power
thrust_req = TW_opt * W_gross
power_req = thrust_req * A["cruise_speed_ms"]

# Size a battery/motor (using reasonable RC assumptions)
motor_eff = 0.80
prop_eff = 0.65
shaft_power = power_req / prop_eff
electrical_power = shaft_power / motor_eff
battery_voltage = 11.1  # 3S LiPo
flight_time_hr = A["endurance_s"] / 3600
battery_capacity = electrical_power / battery_voltage * flight_time_hr

eps = ElectricPowerSystem(
    motor_power_W=shaft_power,
    motor_efficiency=motor_eff,
    prop_efficiency=prop_eff,
    battery_voltage=battery_voltage,
    battery_capacity_Ah=max(battery_capacity, 0.5),  # minimum practical size
)

print(f"  Payload:          {A['payload_kg']:.2f} kg  ({A['payload_fraction']*100:.0f}% fraction)")
print(f"  Gross mass:       {m_gross:.2f} kg")
print(f"  Gross weight:     {W_gross:.1f} N")
print(f"  Required wing S:  {S_wing:.4f} m²  ({S_wing*1e4:.0f} cm²)")
print(f"  Required thrust:  {thrust_req:.1f} N")
print(f"  Cruise power:     {power_req:.1f} W")
print(f"  Shaft power:      {shaft_power:.1f} W")
print(f"  Electrical power: {electrical_power:.1f} W")
print(f"  Battery:          {battery_voltage}V / {eps.battery_capacity_Ah:.1f} Ah")
print(f"  Est. endurance:   {eps.endurance_min:.1f} min")


# =====================================================================
# Stage 4 — Geometry sizing (from area + aspect ratio)
# =====================================================================
banner("STAGE 4: Geometry Sizing")

# Design choices for geometry (typical sport trainer ratios)
AR_main = 8.0        # aspect ratio
TR_main = 0.6        # taper ratio
Vh_target = 0.45     # horizontal tail volume coefficient
Vv_target = 0.035    # vertical tail volume coefficient
tail_lever = 0.6     # tail moment arm [m] — estimated from fuselage proportions

b_main, cr_main, ct_main = size_wing(S_wing, AR_main, TR_main)

# Fuselage length scales with wing span
fuse_length = b_main * 0.75

# Size horizontal tail from volume coefficient: Sh = Vh * MAC * S / l
wm = Wing(cr_main, ct_main, b_main, dihedral_deg=5.0, foil=AF["code"],
          type_=0, x=fuse_length * 0.22)
mac_main = compute_mac(wm)
S_horiz = Vh_target * mac_main.mac_length * S_wing / tail_lever
AR_horiz = 5.0
TR_horiz = 0.8
b_h, cr_h, ct_h = size_wing(S_horiz, AR_horiz, TR_horiz)

# Size vertical tail from volume coefficient: Sv = Vv * b * S / l
S_vert = Vv_target * b_main * S_wing / tail_lever
AR_vert = 1.5
TR_vert = 0.5
b_v, cr_v, ct_v = size_wing(S_vert, AR_vert, TR_vert)

# Position tail surfaces
horiz_x = wm.x + tail_lever + 0.1
vert_x = horiz_x - 0.05

wh = Wing(cr_h, ct_h, b_h, foil="0009", type_=0, x=horiz_x)
wv = Wing(cr_v, ct_v, b_v, foil="0009", type_=2, x=vert_x, sweep_deg=25.0)

concept = ConventionalConcept(
    wing_main=wm, wing_horiz=wh, wing_vert=wv,
    fuselage_length=fuse_length,
)

print(f"  Main wing:")
print(f"    Span = {b_main:.3f} m  ({b_main*100:.0f} cm)")
print(f"    Root chord = {cr_main:.3f} m  ({cr_main*100:.1f} cm)")
print(f"    Tip  chord = {ct_main:.3f} m  ({ct_main*100:.1f} cm)")
print(f"    Area = {wm.area:.4f} m²")
print(f"    AR = {wm.aspect_ratio:.1f}")
print(f"    MAC = {mac_main.mac_length:.3f} m")
print(f"  Horizontal tail:")
print(f"    Span = {b_h:.3f} m, S = {wh.area:.4f} m²")
print(f"  Vertical tail:")
print(f"    Span = {b_v:.3f} m, S = {wv.area:.4f} m²")
print(f"  Fuselage length: {fuse_length:.2f} m")


# =====================================================================
# Stage 5 — Stability check
# =====================================================================
banner("STAGE 5: Stability & Control Check")

# CG at 25-30% MAC for sport flyer
X_cg = wm.x + mac_main.x_sweep + 0.28 * mac_main.mac_length

stab = analyze_stability(concept, X_cg=X_cg)
ranges = check_design_ranges(stab)

print(f"  CG position:      X_cg = {X_cg:.3f} m")
print(f"  Neutral point:    X_np = {stab.X_np:.3f} m")
print(f"  Static margin:    SM = {stab.static_margin:.3f}  {'✓ STABLE' if stab.static_margin < 0 else '⚠ CG aft of NP'}")
print(f"  Horizontal Vh:    {stab.Vh:.3f}  {'✓' if ranges['Vh'] else '✗ out of range'}")
print(f"  Vertical Vv:      {stab.Vv:.4f}  {'✓' if ranges['Vv'] else '✗ out of range'}")
print(f"  Spiral B:         {stab.B:.2f}   {'✓' if ranges['B'] else '✗ out of range'}")


# =====================================================================
# Summary — complete aircraft from assumptions
# =====================================================================
banner("RESULT: Complete Aircraft from Assumptions")

print(f"""
  Mission: {A['mission']}

  Assumptions (user inputs):
    Payload .......... {A['payload_kg']} kg ({A['payload_fraction']*100:.0f}% of gross)
    Cruise speed ..... {A['cruise_speed_ms']} m/s
    Endurance ........ {A['endurance_s']//60} min
    Climb rate ....... {A['climb_rate_ms']} m/s
    Turn bank ........ {A['turn_bank_deg']}°
    Takeoff roll ..... {A['takeoff_ground_roll_m']} m
    Airfoil .......... NACA {AF['code']}

  Derived aircraft:
    Gross mass ....... {m_gross:.2f} kg
    Wing span ........ {b_main*100:.0f} cm
    Wing area ........ {S_wing*1e4:.0f} cm²
    Wing AR .......... {AR_main}
    Root chord ....... {cr_main*100:.1f} cm
    Tip chord ........ {ct_main*100:.1f} cm
    Horiz tail S ..... {wh.area*1e4:.0f} cm²
    Vert tail S ...... {wv.area*1e4:.0f} cm²
    Fuselage ......... {fuse_length*100:.0f} cm
    Power required ... {shaft_power:.0f} W
    Battery .......... {battery_voltage}V / {eps.battery_capacity_Ah:.1f} Ah
    T/W .............. {TW_opt:.3f}
    W/S .............. {WS_opt:.1f} N/m²
    Static margin .... {stab.static_margin:.3f}
    CG position ...... {X_cg*100:.1f} cm from nose
""")

print("Pipeline: Assumptions → Aero → Constraints → Weight → Geometry → Stability ✓")
print("          (no iteration — pure forward pass, ported from rAviExp)")
