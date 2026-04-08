"""Trapezoid wing geometry, planform, and sizing.

Ported from rAviExp (Geom.R, MAC.R, size_wing_1.R) and WebrAviExpConvConcept.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from ..utils.math_helpers import tand


# ---------------------------------------------------------------------------
# Wing definition
# ---------------------------------------------------------------------------

@dataclass
class Wing:
    """Trapezoid wing panel (half-span or full, depending on *type_*).

    Parameters
    ----------
    chord_root : root chord [m]
    chord_tip : tip chord [m]
    span : total span [m]  (both sides for type_=0, one side for type_=1/2)
    sweep_deg : leading-edge sweep [deg]
    dihedral_deg : dihedral angle [deg]
    foil : NACA code (e.g. "2412") or name
    type_ : 0 = full wing, 1 = right half, 2 = vertical
    xf_c : aerodynamic-focus position as fraction of chord (default 0.25)
    x, y, z : wing root position [m]
    """

    chord_root: float
    chord_tip: float
    span: float
    sweep_deg: float = 0.0
    dihedral_deg: float = 0.0
    foil: str = "0012"
    type_: int = 0
    xf_c: float = 0.25
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # -- Derived quantities --------------------------------------------------

    @property
    def area(self) -> float:
        """Planform area S = (Cr + Ct) * span / 2."""
        return (self.chord_root + self.chord_tip) * self.span / 2.0

    @property
    def taper_ratio(self) -> float:
        """λ = Ct / Cr."""
        return self.chord_tip / self.chord_root

    @property
    def aspect_ratio(self) -> float:
        """AR = b² / S."""
        return self.span**2 / self.area

    @property
    def mac(self) -> MACResult:
        """Full MAC computation (delegates to :func:`compute_mac`)."""
        return compute_mac(self)


# ---------------------------------------------------------------------------
# MAC computations (detailed, matching rAviExp MAC.R)
# ---------------------------------------------------------------------------

@dataclass
class MACResult:
    """Mean Aerodynamic Chord computation results."""

    mac_length: float       # MAC chord length
    x_sweep: float          # chordwise offset of MAC LE from root LE
    y_mac: float            # spanwise position of MAC
    x_aero_focus: float     # x-position of aerodynamic focus
    chord_at_mac: float     # chord at the MAC station


def compute_mac(wing: Wing) -> MACResult:
    """Full MAC computation for a wing panel."""
    Cr = wing.chord_root
    Ct = wing.chord_tip
    half_span = wing.span / 2 if wing.type_ == 0 else wing.span
    lam = wing.taper_ratio

    # Sweep distance at tip
    S_tip = half_span * tand(wing.sweep_deg)

    # MAC length
    mac = Cr * (1 + lam + lam**2) / (3 * (1 + lam))

    # Sweep distance at MAC station
    x_sweep = S_tip * (Cr + 2 * Ct) / (3 * (Cr + Ct))

    # Chord at MAC station
    chord_at_mac = Cr - (Cr - Ct) * (1 + 2 * lam) / (3 * (1 + lam))

    # Spanwise location
    y_mac = half_span * (1 + 2 * lam) / (3 * (1 + lam))

    # Aerodynamic focus
    x_af = wing.x + x_sweep + wing.xf_c * mac

    return MACResult(
        mac_length=mac,
        x_sweep=x_sweep,
        y_mac=y_mac,
        x_aero_focus=x_af,
        chord_at_mac=chord_at_mac,
    )


# ---------------------------------------------------------------------------
# Sizing helpers
# ---------------------------------------------------------------------------

def size_wing(S: float, AR: float, taper_ratio: float = 1.0) -> tuple[float, float, float]:
    """Compute span and chords from area, aspect ratio, and taper ratio.

    Returns (span, chord_root, chord_tip).
    """
    span = np.sqrt(S * AR)
    chord_root = 2 * S / (span * (1 + taper_ratio))
    chord_tip = taper_ratio * chord_root
    return float(span), float(chord_root), float(chord_tip)


@dataclass
class ConventionalConcept:
    """Conventional RC aircraft layout: main wing + horizontal tail + vertical tail + fuselage."""

    wing_main: Wing
    wing_horiz: Wing
    wing_vert: Wing
    fuselage_length: float = 1.5
    fuselage_radii: list[float] | None = None
    fuselage_stations: list[float] | None = None

    def __post_init__(self):
        if self.fuselage_radii is None:
            self.fuselage_radii = [0.05, 0.10, 0.10, 0.03, 0.01, 0.0]
        if self.fuselage_stations is None:
            n = len(self.fuselage_radii)
            self.fuselage_stations = [i / (n - 1) * self.fuselage_length for i in range(n)]


def size_conventional(
    S_main: float = 0.3,
    AR_main: float = 8.0,
    TR_main: float = 0.6,
    S_horiz: float = 0.06,
    AR_horiz: float = 5.0,
    TR_horiz: float = 0.8,
    S_vert: float = 0.02,
    AR_vert: float = 1.5,
    TR_vert: float = 0.5,
    fuselage_length: float = 1.5,
    main_x: float = 0.3,
    horiz_x: float = 1.3,
    vert_x: float = 1.25,
) -> ConventionalConcept:
    """Create a conventional RC aircraft concept from summary parameters."""
    b_m, cr_m, ct_m = size_wing(S_main, AR_main, TR_main)
    b_h, cr_h, ct_h = size_wing(S_horiz, AR_horiz, TR_horiz)
    b_v, cr_v, ct_v = size_wing(S_vert, AR_vert, TR_vert)

    wm = Wing(cr_m, ct_m, b_m, x=main_x, type_=0)
    wh = Wing(cr_h, ct_h, b_h, x=horiz_x, type_=0)
    wv = Wing(cr_v, ct_v, b_v, x=vert_x, type_=2)

    return ConventionalConcept(
        wing_main=wm, wing_horiz=wh, wing_vert=wv,
        fuselage_length=fuselage_length,
    )


# ---------------------------------------------------------------------------
# Planform coordinate generation (for plotting / DXF export)
# ---------------------------------------------------------------------------

def planform_coords(wing: Wing) -> tuple[np.ndarray, np.ndarray]:
    """Return (x, y) outline of a trapezoid wing planform.

    Returns closed polygon suitable for plotting.
    """
    Cr = wing.chord_root
    Ct = wing.chord_tip
    half_span = wing.span / 2 if wing.type_ == 0 else wing.span
    sweep_offset = half_span * tand(wing.sweep_deg)

    if wing.type_ == 2:
        # Vertical tail: "span" is height, plot in x-z
        x = np.array([
            wing.x, wing.x + Cr,
            wing.x + sweep_offset + Ct, wing.x + sweep_offset,
            wing.x,
        ])
        y = np.array([
            wing.z, wing.z,
            wing.z + half_span, wing.z + half_span,
            wing.z,
        ])
    elif wing.type_ == 0:
        # Full wing (symmetric) — trace: root LE → right tip LE → right tip TE
        # → root TE → left tip TE → left tip LE → close
        x = np.array([
            wing.x,                          # root LE
            wing.x + sweep_offset,           # right tip LE
            wing.x + sweep_offset + Ct,      # right tip TE
            wing.x + Cr,                     # root TE
            wing.x - sweep_offset + Ct,      # left tip TE
            wing.x - sweep_offset,           # left tip LE
            wing.x,                          # close
        ])
        y = np.array([
            wing.y,
            wing.y + half_span,
            wing.y + half_span,
            wing.y,
            wing.y - half_span,
            wing.y - half_span,
            wing.y,
        ])
    else:
        # Half wing
        x = np.array([
            wing.x, wing.x + Cr,
            wing.x + sweep_offset + Ct, wing.x + sweep_offset,
            wing.x,
        ])
        y = np.array([
            wing.y, wing.y,
            wing.y + half_span, wing.y + half_span,
            wing.y,
        ])

    return x, y
