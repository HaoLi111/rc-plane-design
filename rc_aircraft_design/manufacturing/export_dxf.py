"""Export manufacturing parts to DXF for laser cutting.

Arranges ribs and formers on sheets, ready for DeepNest or direct cutting.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..cad.dxf_writer import DxfWriter
from .parts import ManufacturingParts, RibProfile, FormerProfile


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

    # Spar slot cutouts
    for slot in rib.spar_slots:
        x0, y0, x1, y1 = slot
        slot_pts = np.array([
            [x0 + offset_x, y0 + offset_y],
            [x1 + offset_x, y0 + offset_y],
            [x1 + offset_x, y1 + offset_y],
            [x0 + offset_x, y1 + offset_y],
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

    # Longeron holes
    for lx, ly in former.longeron_holes:
        dxf.circle(lx + offset_x, ly + offset_y, 2.0, layer=layer + "_HOLES")

    # Label
    dxf.text(offset_x - former.width_mm / 2, offset_y - former.height_mm / 2 - 5,
             former.label, height=3.0, layer=layer + "_LABEL")


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
    dxf.add_layer("FORMERS_LABEL", color=7)

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

    dxf.save(output_path)
