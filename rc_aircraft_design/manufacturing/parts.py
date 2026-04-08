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
from .config import ManufacturingConfig, WingBuildConfig, FuselageBuildConfig


# ---------------------------------------------------------------------------
# Data structures for generated parts
# ---------------------------------------------------------------------------

@dataclass
class RibProfile:
    """Single wing rib: outer airfoil contour with spar slots cut out."""

    index: int               # rib number (0 = root)
    span_pos_mm: float       # spanwise position from root [mm]
    chord_mm: float          # local chord [mm]
    x: np.ndarray            # airfoil x coords [mm] (closed loop)
    y: np.ndarray            # airfoil y coords [mm] (closed loop)
    spar_slots: list[tuple[float, float, float, float]]  # [(x0, y0, x1, y1), ...] slot rects
    has_control_surface: bool = False
    hinge_x_mm: float = 0.0  # hinge cut position from LE [mm]
    label: str = ""


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
    label: str = ""


@dataclass
class ManufacturingParts:
    """All generated manufacturing parts for one aircraft."""

    wing_ribs: list[RibProfile]
    htail_ribs: list[RibProfile]
    vtail_ribs: list[RibProfile]
    fuselage_formers: list[FormerProfile]
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
    spar_x_frac: float,
    foil_code: str,
    spar_width_mm: float,
    material_thickness_mm: float,
) -> tuple[float, float, float, float]:
    """Compute a spar slot rectangle (x0, y_bottom, x1, y_top) in mm."""
    x_center = spar_x_frac * chord_mm
    half_w = spar_width_mm / 2.0
    # Find airfoil thickness at spar position
    x_n, yu_n, yl_n = naca4(foil_code, n_points=200)
    yu_at = float(np.interp(spar_x_frac, x_n, yu_n)) * chord_mm
    yl_at = float(np.interp(spar_x_frac, x_n, yl_n)) * chord_mm
    # Slot goes from lower surface up by material thickness, centered on spar
    slot_bottom = yl_at
    slot_top = yl_at + material_thickness_mm
    return (x_center - half_w, slot_bottom, x_center + half_w, slot_top)


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

        # Spar slots
        slots = []
        for spar_frac in build.spar_x_frac:
            slot = _spar_slot_rect(chord, spar_frac, foil,
                                   build.spar_width_mm,
                                   build.material_thickness_mm)
            slots.append(slot)

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
            spar_slots=slots,
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
