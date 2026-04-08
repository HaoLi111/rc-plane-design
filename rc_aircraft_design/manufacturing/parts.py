"""Generate manufacturing parts (ribs, formers, spar webs) from aircraft geometry.

Takes a ConventionalConcept + ManufacturingConfig and produces 2D profiles
ready for DXF export and laser cutting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..aero.airfoil import naca4
from ..wing.geometry import Wing, ConventionalConcept
from .config import ManufacturingConfig, WingBuildConfig, FuselageBuildConfig, SparConfig


# ---------------------------------------------------------------------------
# Data structures for generated parts
# ---------------------------------------------------------------------------

@dataclass
class SlotRect:
    """A rectangular slot cut into a rib for a spar/rod/longeron."""

    x0: float       # left edge [mm from LE]
    y0: float       # bottom edge [mm]
    x1: float       # right edge [mm from LE]
    y1: float       # top edge [mm]
    name: str = ""  # spar name for labelling/colour coding
    surface: str = "center"  # "upper" | "lower" | "center"


@dataclass
class LighteningHole:
    """Elliptical weight-saving cutout between spars in a rib."""

    cx: float       # center x [mm from LE]
    cy: float       # center y [mm]
    rx: float       # semi-axis x [mm]
    ry: float       # semi-axis y [mm]


@dataclass
class RibProfile:
    """Single wing rib: outer airfoil contour with spar slots cut out."""

    index: int               # rib number (0 = root)
    span_pos_mm: float       # spanwise position from root [mm]
    chord_mm: float          # local chord [mm]
    x: np.ndarray            # airfoil x coords [mm] (closed loop)
    y: np.ndarray            # airfoil y coords [mm] (closed loop)
    slots: list[SlotRect]    # all spar/rod/longeron slots
    lightening_holes: list[LighteningHole] = field(default_factory=list)
    has_control_surface: bool = False
    hinge_x_mm: float = 0.0  # hinge cut position from LE [mm]
    label: str = ""

    @property
    def spar_slots(self) -> list[tuple[float, float, float, float]]:
        """Legacy compatibility: list of (x0, y0, x1, y1) tuples."""
        return [(s.x0, s.y0, s.x1, s.y1) for s in self.slots]


@dataclass
class FormerProfile:
    """Fuselage cross-section former."""

    index: int
    station_mm: float        # x position along fuselage [mm]
    width_mm: float
    height_mm: float
    x: np.ndarray            # outline x coords [mm]
    y: np.ndarray            # outline y coords [mm]
    longeron_holes: list[tuple[float, float]]  # (x, y) centers for longeron cutouts
    stringer_notches: list[tuple[float, float, float, float]] = field(default_factory=list)
    # (x0, y0, x1, y1) rectangular notches at edge for stringers
    tab_slots: list[tuple[float, float, float, float]] = field(default_factory=list)
    # (x0, y0, x1, y1) tab slots for fuselage side panel interlocking
    label: str = ""


@dataclass
class FuselageSidePanel:
    """Flat fuselage side panel (left or right) with cutouts."""

    side: str                # "left" or "right"
    x: np.ndarray            # outline x coords [mm]
    y: np.ndarray            # outline y coords [mm]
    cutouts: list[tuple[np.ndarray, np.ndarray]]  # list of (x, y) closed-loop cutouts
    tab_positions: list[float]  # x positions of interlocking tabs
    label: str = ""


@dataclass
class Firewall:
    """Motor mount firewall — flat plate at nose with bolt holes."""

    width_mm: float
    height_mm: float
    thickness_mm: float
    x: np.ndarray            # outline x coords [mm]
    y: np.ndarray            # outline y coords [mm]
    motor_holes: list[tuple[float, float, float]]  # (cx, cy, radius) for bolt holes
    label: str = "FW"


@dataclass
class Doubler:
    """Reinforcement doubler (root rib doubler, gusset, etc.)."""

    x: np.ndarray            # outline x coords [mm]
    y: np.ndarray            # outline y coords [mm]
    cutouts: list[tuple[np.ndarray, np.ndarray]]  # internal cutouts
    label: str = ""


@dataclass
class ManufacturingParts:
    """All generated manufacturing parts for one aircraft."""

    wing_ribs: list[RibProfile]
    htail_ribs: list[RibProfile]
    vtail_ribs: list[RibProfile]
    fuselage_formers: list[FormerProfile]
    fuselage_sides: list[FuselageSidePanel] = field(default_factory=list)
    firewall: Firewall | None = None
    doublers: list[Doubler] = field(default_factory=list)
    name: str = ""


# ---------------------------------------------------------------------------
# Rib generation
# ---------------------------------------------------------------------------

def _airfoil_profile_mm(foil_code: str, chord_mm: float,
                        n_points: int = 80) -> tuple[np.ndarray, np.ndarray]:
    """Get closed airfoil contour in mm, ready for cutting."""
    x_n, yu_n, yl_n = naca4(foil_code, n_points=n_points)
    # Upper forward, lower backward → closed loop
    xp = np.concatenate([x_n, x_n[::-1]]) * chord_mm
    yp = np.concatenate([yu_n, yl_n[::-1]]) * chord_mm
    return xp, yp


def _spar_slot_rect(
    chord_mm: float,
    spar: SparConfig,
    foil_code: str,
) -> SlotRect:
    """Compute a spar/rod/longeron slot rectangle in mm.

    surface="center" → full-depth slot (traditional spar web pass-through)
    surface="upper"  → notch from upper skin inward (upper longeron)
    surface="lower"  → notch from lower skin inward (lower longeron)
    """
    x_center = spar.x_frac * chord_mm
    half_w = spar.width_mm / 2.0

    # Get airfoil surfaces at this chordwise position
    x_n, yu_n, yl_n = naca4(foil_code, n_points=200)
    yu_at = float(np.interp(spar.x_frac, x_n, yu_n)) * chord_mm
    yl_at = float(np.interp(spar.x_frac, x_n, yl_n)) * chord_mm

    if spar.surface == "upper":
        # Notch inward from upper surface
        slot_top = yu_at
        slot_bottom = yu_at - spar.height_mm
    elif spar.surface == "lower":
        # Notch inward from lower surface
        slot_bottom = yl_at
        slot_top = yl_at + spar.height_mm
    else:
        # Center / full-depth: spar web runs through the rib
        mid_y = (yu_at + yl_at) / 2.0
        slot_bottom = mid_y - spar.height_mm / 2.0
        slot_top = mid_y + spar.height_mm / 2.0

    return SlotRect(
        x0=x_center - half_w,
        y0=slot_bottom,
        x1=x_center + half_w,
        y1=slot_top,
        name=spar.name,
        surface=spar.surface,
    )


def _compute_lightening_holes(
    chord_mm: float,
    foil_code: str,
    slots: list[SlotRect],
    build: WingBuildConfig,
) -> list[LighteningHole]:
    """Compute elliptical lightening holes between spar slots.

    Places one ellipse in every gap between adjacent spars where
    the gap is wide enough (>= lightening_hole_min_width_mm).
    """
    if not build.lightening_holes or len(slots) < 2:
        return []

    margin = build.lightening_hole_margin_mm
    min_w = build.lightening_hole_min_width_mm
    h_frac = build.lightening_hole_height_frac

    # Get airfoil upper/lower at fine resolution for thickness queries
    x_n, yu_n, yl_n = naca4(foil_code, n_points=200)

    # Sort slots by x position
    sorted_slots = sorted(slots, key=lambda s: s.x0)

    holes: list[LighteningHole] = []
    for i in range(len(sorted_slots) - 1):
        left_edge = sorted_slots[i].x1 + margin
        right_edge = sorted_slots[i + 1].x0 - margin
        gap = right_edge - left_edge

        if gap < min_w:
            continue

        cx = (left_edge + right_edge) / 2.0
        rx = gap / 2.0 * 0.85  # 85% of available width

        # Local airfoil thickness at centre of hole
        x_frac = cx / chord_mm
        if x_frac < 0.01 or x_frac > 0.99:
            continue
        yu_at = float(np.interp(x_frac, x_n, yu_n)) * chord_mm
        yl_at = float(np.interp(x_frac, x_n, yl_n)) * chord_mm
        thickness = yu_at - yl_at
        cy = (yu_at + yl_at) / 2.0
        ry = thickness * h_frac / 2.0

        if ry < 2.0:  # skip degenerate holes
            continue

        holes.append(LighteningHole(cx=cx, cy=cy, rx=rx, ry=ry))

    return holes


def generate_wing_ribs(
    wing: Wing,
    build: WingBuildConfig,
    prefix: str = "W",
) -> list[RibProfile]:
    """Generate rib profiles for one wing half."""
    half_span = wing.span / 2 if wing.type_ == 0 else wing.span
    half_span_mm = half_span * 1000.0
    cr_mm = wing.chord_root * 1000.0
    ct_mm = wing.chord_tip * 1000.0
    foil = wing.foil

    ribs = []
    for i in range(build.n_ribs):
        frac = i / max(build.n_ribs - 1, 1)
        span_pos = frac * half_span_mm
        chord = cr_mm + (ct_mm - cr_mm) * frac

        # Airfoil contour
        x_prof, y_prof = _airfoil_profile_mm(foil, chord)

        # All spar/rod/longeron slots
        slots = []
        for spar in build.spars:
            slot = _spar_slot_rect(chord, spar, foil)
            slots.append(slot)

        # Lightening holes between spars
        l_holes = _compute_lightening_holes(chord, foil, slots, build)

        # Control surface check
        has_cs = False
        hinge_x = 0.0
        for cs in build.control_surfaces:
            end_rib = cs.end_rib if cs.end_rib >= 0 else build.n_ribs - 1
            if cs.start_rib <= i <= end_rib:
                has_cs = True
                hinge_x = cs.hinge_x_frac * chord

        ribs.append(RibProfile(
            index=i,
            span_pos_mm=span_pos,
            chord_mm=chord,
            x=x_prof,
            y=y_prof,
            slots=slots,
            lightening_holes=l_holes,
            has_control_surface=has_cs,
            hinge_x_mm=hinge_x,
            label=f"{prefix}{i}",
        ))

    return ribs


# ---------------------------------------------------------------------------
# Fuselage former generation
# ---------------------------------------------------------------------------

def generate_fuselage_formers(
    concept: ConventionalConcept,
    build: FuselageBuildConfig,
) -> list[FormerProfile]:
    """Generate fuselage cross-section formers."""
    fuse_l_mm = concept.fuselage_length * 1000.0
    stations = concept.fuselage_stations
    radii = concept.fuselage_radii

    if not stations or not radii:
        return []

    formers = []
    n = build.n_formers

    for i in range(n):
        frac = i / max(n - 1, 1)
        station_mm = frac * fuse_l_mm

        # Interpolate radius at this station
        station_m = frac * concept.fuselage_length
        r = float(np.interp(station_m, stations, radii))
        r_mm = r * 1000.0

        if r_mm < 1.0:
            # Degenerate station (nose tip or tail tip)
            r_mm = max(r_mm, 2.0)

        # Rounded-rectangle cross-section (typical RC fuselage)
        width_mm = r_mm * 2.0
        height_mm = r_mm * 2.0 * 1.2  # slightly taller than wide

        # Generate outline (rounded rectangle approximation)
        t = np.linspace(0, 2 * np.pi, 64, endpoint=True)
        x_outline = width_mm / 2 * np.cos(t)
        y_outline = height_mm / 2 * np.sin(t)

        # Longeron hole positions (4 corners)
        lh = []
        for angle in [45, 135, 225, 315]:
            rad = np.radians(angle)
            lx = (width_mm / 2 - build.material_thickness_mm) * np.cos(rad)
            ly = (height_mm / 2 - build.material_thickness_mm) * np.sin(rad)
            lh.append((lx, ly))

        formers.append(FormerProfile(
            index=i,
            station_mm=station_mm,
            width_mm=width_mm,
            height_mm=height_mm,
            x=x_outline,
            y=y_outline,
            longeron_holes=lh[:build.longeron_count],
            label=f"F{i}",
        ))

    return formers


# ---------------------------------------------------------------------------
# Full parts generation
# ---------------------------------------------------------------------------

def generate_all_parts(
    concept: ConventionalConcept,
    config: ManufacturingConfig,
) -> ManufacturingParts:
    """Generate all cutting parts for an aircraft."""
    wing_ribs = generate_wing_ribs(concept.wing_main, config.wing, prefix="W")
    htail_ribs = generate_wing_ribs(concept.wing_horiz, config.htail, prefix="H")
    vtail_ribs = generate_wing_ribs(concept.wing_vert, config.vtail, prefix="V")
    fuselage_formers = generate_fuselage_formers(concept, config.fuselage)

    return ManufacturingParts(
        wing_ribs=wing_ribs,
        htail_ribs=htail_ribs,
        vtail_ribs=vtail_ribs,
        fuselage_formers=fuselage_formers,
        name=config.name,
    )
