"""Stability analysis: CG, neutral point, static margin.

Ported from rAviExp StabilitySimplified.R.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..wing.geometry import Wing, ConventionalConcept, compute_mac


@dataclass
class StabilityResult:
    """Simplified stability analysis output."""

    Vh: float           # horizontal tail volume coefficient
    Vv: float           # vertical tail volume coefficient
    static_margin: float  # SM = (Xcg - Xnp) / MAC  (negative = stable)
    X_np: float         # neutral point x-position [m]
    X_cg: float         # CG x-position [m]
    M_de: float         # pitch-moment effectiveness (elevator)
    B: float            # spiral stability factor
    VvB: float          # Vv * B product


def horizontal_tail_volume(Sh: float, Lh: float, Sw: float, mac_w: float) -> float:
    """Vh = Sh * Lh / (Sw * c̄_w)."""
    return Sh * Lh / (Sw * mac_w)


def vertical_tail_volume(Sv: float, Lv: float, Sw: float, bw: float) -> float:
    """Vv = Sv * Lv / (Sw * b_w)."""
    return Sv * Lv / (Sw * bw)


def spiral_stability(lv: float, b: float, dihedral_deg: float, Cl: float) -> float:
    """B = (lv / b) * (Γ / Cl), where Γ is dihedral in degrees."""
    return (lv / b) * (dihedral_deg / Cl)


def neutral_point(
    Xac_w: float,
    AR_w: float,
    AR_h: float,
    Vh: float,
) -> float:
    """Simplified neutral point location.

    Xnp = Xac_w + [(1+2/AR_w)/(1+2/AR_h)] * [1 - 4/(AR_w+2)] * Vh * c̄_w

    Returns the neutral point x-position (add to Xac_w).
    Note: the result is the *offset* from the wing AC in units of MAC.
    """
    ratio = (1 + 2 / AR_w) / (1 + 2 / AR_h)
    downwash = 1 - 4 / (AR_w + 2)
    return Xac_w + ratio * downwash * Vh


def analyze_stability(
    concept: ConventionalConcept,
    X_cg: float,
    Cl: float = 0.45,
) -> StabilityResult:
    """Run simplified stability analysis on a conventional aircraft concept.

    Parameters
    ----------
    concept : aircraft layout
    X_cg : x-position of center of gravity [m]
    Cl : operating lift coefficient (for spiral stability)
    """
    wm = concept.wing_main
    wh = concept.wing_horiz
    wv = concept.wing_vert

    mac_m = compute_mac(wm)
    mac_h = compute_mac(wh)
    mac_v = compute_mac(wv)

    # Moment arms
    Lh = mac_h.x_aero_focus - mac_m.x_aero_focus
    Lv = mac_v.x_aero_focus - mac_m.x_aero_focus

    # Volume coefficients
    Vh = horizontal_tail_volume(wh.area, Lh, wm.area, mac_m.mac_length)
    Vv = vertical_tail_volume(wv.area, Lv, wm.area, wm.span)

    # Neutral point
    X_np = neutral_point(
        mac_m.x_aero_focus, wm.aspect_ratio, wh.aspect_ratio, Vh,
    )

    # Static margin (negative = stable, CG ahead of NP)
    SM = (X_cg - X_np) / mac_m.mac_length

    # Moment effectiveness (simplified)
    M_de = Vh  # proportional to tail volume

    # Spiral stability
    B = spiral_stability(Lv, wm.span, wm.dihedral_deg, Cl)

    return StabilityResult(
        Vh=Vh, Vv=Vv, static_margin=SM,
        X_np=X_np, X_cg=X_cg,
        M_de=M_de, B=B, VvB=Vv * B,
    )


# ---------------------------------------------------------------------------
# Stability design-space check (from rAviExp Aspect_polar.R)
# ---------------------------------------------------------------------------

# Typical design ranges for conventional RC aircraft
DESIGN_RANGES = {
    "Vh": (0.30, 0.60),
    "Vv": (0.02, 0.05),
    "SM": (-0.40, 0.40),   # negative = stable
    "B": (3.0, 8.0),
}


def check_design_ranges(result: StabilityResult) -> dict[str, bool]:
    """Check whether stability values fall in typical design ranges."""
    return {
        "Vh": DESIGN_RANGES["Vh"][0] <= result.Vh <= DESIGN_RANGES["Vh"][1],
        "Vv": DESIGN_RANGES["Vv"][0] <= result.Vv <= DESIGN_RANGES["Vv"][1],
        "SM": DESIGN_RANGES["SM"][0] <= result.static_margin <= DESIGN_RANGES["SM"][1],
        "B": DESIGN_RANGES["B"][0] <= result.B <= DESIGN_RANGES["B"][1],
    }
