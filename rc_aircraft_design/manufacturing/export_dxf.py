"""Export manufacturing parts to DXF for laser cutting.

Arranges ribs and formers on sheets, ready for DeepNest or direct cutting.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..cad.dxf_writer import DxfWriter
from .parts import (
    ManufacturingParts, RibProfile, FormerProfile, ProfileFuselagePanel,
    SlotRect, LighteningHole,
)


def _add_rib_to_dxf(
    dxf: DxfWriter,
    rib: RibProfile,
    offset_x: float,
    offset_y: float,
    layer: str,
):
    """Add one rib profile to the DXF at the given offset."""
    pts = np.column_stack([rib.x + offset_x, rib.y + offset_y])
    dxf.polyline(pts, closed=True, layer=layer)

    # Spar / rod / longeron slot cutouts
    for slot in rib.slots:
        slot_pts = np.array([
            [slot.x0 + offset_x, slot.y0 + offset_y],
            [slot.x1 + offset_x, slot.y0 + offset_y],
            [slot.x1 + offset_x, slot.y1 + offset_y],
            [slot.x0 + offset_x, slot.y1 + offset_y],
        ])
        dxf.polyline(slot_pts, closed=True, layer=layer + "_SLOTS")

    # Hinge cut line for control surfaces
    if rib.has_control_surface and rib.hinge_x_mm > 0:
        # Find y extents at hinge position
        x_n = rib.x
        y_n = rib.y
        hx = rib.hinge_x_mm
        # Simple: draw vertical line at hinge x
        dxf.line(hx + offset_x, min(y_n) + offset_y,
                 hx + offset_x, max(y_n) + offset_y,
                 layer=layer + "_HINGE")

    # Label
    dxf.text(offset_x + 2, offset_y, rib.label, height=3.0, layer=layer + "_LABEL")


def _add_former_to_dxf(
    dxf: DxfWriter,
    former: FormerProfile,
    offset_x: float,
    offset_y: float,
    layer: str,
):
    """Add one fuselage former to the DXF."""
    pts = np.column_stack([former.x + offset_x, former.y + offset_y])
    dxf.polyline(pts, closed=True, layer=layer)

    # Longeron holes (round formers)
    for lx, ly in former.longeron_holes:
        dxf.circle(lx + offset_x, ly + offset_y, 2.0, layer=layer + "_HOLES")

    # Bar slots (box formers) — rectangular cutouts for longerons/cross-bars
    for slot in former.bar_slots:
        slot_pts = np.array([
            [slot.x0 + offset_x, slot.y0 + offset_y],
            [slot.x1 + offset_x, slot.y0 + offset_y],
            [slot.x1 + offset_x, slot.y1 + offset_y],
            [slot.x0 + offset_x, slot.y1 + offset_y],
        ])
        dxf.polyline(slot_pts, closed=True, layer=layer + "_SLOTS")

    # Label
    dxf.text(offset_x - former.width_mm / 2, offset_y - former.height_mm / 2 - 5,
             former.label, height=3.0, layer=layer + "_LABEL")


def _add_profile_panel_to_dxf(
    dxf: DxfWriter,
    panel: ProfileFuselagePanel,
    offset_x: float,
    offset_y: float,
    layer: str,
):
    """Add a profile fuselage panel to the DXF."""
    pts = np.column_stack([panel.x + offset_x, panel.y + offset_y])
    dxf.polyline(pts, closed=True, layer=layer)

    # Wing spar pass-through slot
    if panel.wing_slot:
        sx0, sy0, sx1, sy1 = panel.wing_slot
        slot_pts = np.array([
            [sx0 + offset_x, sy0 + offset_y],
            [sx1 + offset_x, sy0 + offset_y],
            [sx1 + offset_x, sy1 + offset_y],
            [sx0 + offset_x, sy1 + offset_y],
        ])
        dxf.polyline(slot_pts, closed=True, layer=layer + "_SLOTS")

    # Lightening holes (ellipse approximated as polyline)
    for hole in panel.lightening_holes:
        t = np.linspace(0, 2 * np.pi, 32, endpoint=True)
        hx = hole.cx + hole.rx * np.cos(t) + offset_x
        hy = hole.cy + hole.ry * np.sin(t) + offset_y
        h_pts = np.column_stack([hx, hy])
        dxf.polyline(h_pts, closed=True, layer=layer + "_HOLES")

    # Motor mount holes
    for mx, my, mr in panel.motor_mount_holes:
        dxf.circle(mx + offset_x, my + offset_y, mr, layer=layer + "_HOLES")

    # Label
    dxf.text(offset_x + 5, offset_y - float(np.min(panel.y)) - 8,
             panel.label, height=3.0, layer=layer + "_LABEL")


def export_parts_dxf(
    parts: ManufacturingParts,
    output_path: str | Path,
    spacing_mm: float = 10.0,
):
    """Export all parts to a DXF file, laid out in rows.

    Parts are arranged left-to-right with spacing between them.
    Wing ribs in the first row, tail ribs next, formers last.
    """
    dxf = DxfWriter()

    # Layer setup
    dxf.add_layer("WING_RIBS", color=5)       # blue
    dxf.add_layer("WING_RIBS_SLOTS", color=1)  # red
    dxf.add_layer("WING_RIBS_HINGE", color=3)  # green
    dxf.add_layer("WING_RIBS_LABEL", color=7)
    dxf.add_layer("HTAIL_RIBS", color=4)
    dxf.add_layer("HTAIL_RIBS_SLOTS", color=1)
    dxf.add_layer("HTAIL_RIBS_HINGE", color=3)
    dxf.add_layer("HTAIL_RIBS_LABEL", color=7)
    dxf.add_layer("VTAIL_RIBS", color=4)
    dxf.add_layer("VTAIL_RIBS_SLOTS", color=1)
    dxf.add_layer("VTAIL_RIBS_HINGE", color=3)
    dxf.add_layer("VTAIL_RIBS_LABEL", color=7)
    dxf.add_layer("FORMERS", color=2)          # yellow
    dxf.add_layer("FORMERS_HOLES", color=1)
    dxf.add_layer("FORMERS_SLOTS", color=1)
    dxf.add_layer("FORMERS_LABEL", color=7)
    dxf.add_layer("PROFILE_PANEL", color=6)    # magenta
    dxf.add_layer("PROFILE_PANEL_SLOTS", color=1)
    dxf.add_layer("PROFILE_PANEL_HOLES", color=1)
    dxf.add_layer("PROFILE_PANEL_LABEL", color=7)

    cursor_x = 0.0
    cursor_y = 0.0
    row_height = 0.0

    # Row 1: Wing ribs
    for rib in parts.wing_ribs:
        h = float(np.ptp(rib.y))
        w = float(np.ptp(rib.x))
        y_center = -float(np.min(rib.y))  # shift so rib bottom is at cursor_y
        _add_rib_to_dxf(dxf, rib, cursor_x - float(np.min(rib.x)), cursor_y + y_center,
                         "WING_RIBS")
        cursor_x += w + spacing_mm
        row_height = max(row_height, h)

    cursor_y -= row_height + spacing_mm * 2
    cursor_x = 0.0
    row_height = 0.0

    # Row 2: H-tail ribs
    for rib in parts.htail_ribs:
        h = float(np.ptp(rib.y))
        w = float(np.ptp(rib.x))
        y_center = -float(np.min(rib.y))
        _add_rib_to_dxf(dxf, rib, cursor_x - float(np.min(rib.x)), cursor_y + y_center,
                         "HTAIL_RIBS")
        cursor_x += w + spacing_mm
        row_height = max(row_height, h)

    # V-tail ribs on same row
    for rib in parts.vtail_ribs:
        h = float(np.ptp(rib.y))
        w = float(np.ptp(rib.x))
        y_center = -float(np.min(rib.y))
        _add_rib_to_dxf(dxf, rib, cursor_x - float(np.min(rib.x)), cursor_y + y_center,
                         "VTAIL_RIBS")
        cursor_x += w + spacing_mm
        row_height = max(row_height, h)

    cursor_y -= row_height + spacing_mm * 2
    cursor_x = 0.0

    # Row 3: Fuselage formers
    for former in parts.fuselage_formers:
        w = former.width_mm
        h = former.height_mm
        _add_former_to_dxf(dxf, former, cursor_x + w / 2, cursor_y, "FORMERS")
        cursor_x += w + spacing_mm

    # Row 4: Profile fuselage panel (if present)
    if parts.profile_panel is not None:
        panel = parts.profile_panel
        h = float(np.ptp(panel.y))
        cursor_y -= h + spacing_mm * 2
        cursor_x = 0.0
        y_center = -float(np.min(panel.y))
        _add_profile_panel_to_dxf(
            dxf, panel,
            cursor_x - float(np.min(panel.x)),
            cursor_y + y_center,
            "PROFILE_PANEL",
        )

    dxf.save(output_path)
