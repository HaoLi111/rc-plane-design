"""Full pipeline demo: Design → 3D Visualization → Manufacturing Parts → DXF.

Runs the passive design for sport flyer, then:
  1. 3D matplotlib rendering of the full aircraft
  2. Generates manufacturing parts (ribs, formers) from config
  3. Exports parts to DXF for laser cutting
  4. Plots a rib gallery and parts overview

Run with:  uv run python examples/full_pipeline_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rc_aircraft_design.passive import run_passive_design
from rc_aircraft_design.viz.plot3d import plot_aircraft_3d
from rc_aircraft_design.manufacturing.config import (
    ManufacturingConfig, make_sport_flyer_config,
)
from rc_aircraft_design.manufacturing.parts import generate_all_parts
from rc_aircraft_design.manufacturing.export_dxf import export_parts_dxf

OUT = Path(__file__).resolve().parent.parent / "results" / "examples"
OUT.mkdir(parents=True, exist_ok=True)

DATA = Path(__file__).resolve().parent.parent / "data" / "examples"


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {path}")


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =====================================================================
#  Step 1: Design the aircraft
# =====================================================================

def step_design():
    banner("STEP 1: Passive Design — Sport Flyer")
    data = json.loads((DATA / "passive_sport_flyer.json").read_text(encoding="utf-8"))
    result = run_passive_design(data["assumptions"], data["airfoil"])

    wm = result.concept.wing_main
    print(f"  Gross mass:  {result.m_gross_kg:.2f} kg")
    print(f"  Wing span:   {wm.span*100:.0f} cm")
    print(f"  Wing area:   {result.S_wing*1e4:.0f} cm²")
    print(f"  T/W = {result.TW_opt:.3f}   W/S = {result.WS_opt:.1f} N/m²")
    return result


# =====================================================================
#  Step 2: 3D Visualization
# =====================================================================

def step_3d_viz(result):
    banner("STEP 2: 3D Aircraft Visualization")
    concept = result.concept

    # Multiple views
    views = [
        ("3d_perspective", 20, -135, "3D Perspective"),
        ("3d_front", 0, 0, "Front View"),
        ("3d_top", 90, -90, "Top View"),
        ("3d_side", 0, -90, "Side View"),
    ]

    for suffix, elev, azim, label in views:
        fig = plot_aircraft_3d(concept, title=f"Sport Flyer — {label}",
                                elev=elev, azim=azim)
        save(fig, f"sport_flyer_{suffix}.png")


# =====================================================================
#  Step 3: Manufacturing Parts
# =====================================================================

def step_manufacturing(result):
    banner("STEP 3: Manufacturing Parts Generation")
    concept = result.concept
    config = make_sport_flyer_config()

    parts = generate_all_parts(concept, config)

    print(f"  Wing ribs:       {len(parts.wing_ribs)}")
    print(f"  H-tail ribs:     {len(parts.htail_ribs)}")
    print(f"  V-tail ribs:     {len(parts.vtail_ribs)}")
    print(f"  Fuselage formers: {len(parts.fuselage_formers)}")

    # Print rib table
    print(f"\n  {'Rib':>4} {'Span[mm]':>9} {'Chord[mm]':>10} {'Slots':>6} {'Ctrl':>5} {'Hinge':>8}")
    print(f"  {'─'*45}")
    for rib in parts.wing_ribs:
        cs_flag = "✓" if rib.has_control_surface else ""
        hinge = f"{rib.hinge_x_mm:.1f}" if rib.has_control_surface else ""
        print(f"  {rib.label:>4} {rib.span_pos_mm:9.1f} {rib.chord_mm:10.1f} {len(rib.slots):6} {cs_flag:>5} {hinge:>8}")

    # Print spar legend
    if parts.wing_ribs:
        print(f"\n  Spars in each rib:")
        for slot in parts.wing_ribs[0].slots:
            print(f"    {slot.name:20s}  x={slot.x0:.0f}–{slot.x1:.0f} mm  ({slot.surface})")

    # Print former table
    print(f"\n  {'Fmr':>4} {'Station[mm]':>12} {'W[mm]':>7} {'H[mm]':>7}")
    print(f"  {'─'*32}")
    for f in parts.fuselage_formers:
        print(f"  {f.label:>4} {f.station_mm:12.1f} {f.width_mm:7.1f} {f.height_mm:7.1f}")

    return parts, config


# =====================================================================
#  Step 4: Rib gallery plot
# =====================================================================

# Colour map for slot types
_SLOT_COLORS = {
    "upper":  "#e07020",   # orange — upper longeron
    "lower":  "#2080e0",   # blue — lower longeron
    "center": "#d02020",   # red — full-depth spar / LE rod / TE stock
}


def step_rib_gallery(parts):
    banner("STEP 4: Rib Gallery Visualization")

    # Wing ribs
    n = len(parts.wing_ribs)
    cols = min(n, 6)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.5 * cols, 3 * rows))
    axes_flat = np.array(axes).flatten() if n > 1 else [axes]

    for i, rib in enumerate(parts.wing_ribs):
        ax = axes_flat[i]
        ax.plot(rib.x, rib.y, "C0", lw=1.2)
        ax.fill(rib.x, rib.y, alpha=0.08, color="C0")

        # Draw spar/rod/longeron slots with type-based colours
        for slot in rib.slots:
            rect_x = [slot.x0, slot.x1, slot.x1, slot.x0, slot.x0]
            rect_y = [slot.y0, slot.y0, slot.y1, slot.y1, slot.y0]
            color = _SLOT_COLORS.get(slot.surface, "red")
            ax.fill(rect_x, rect_y, color=color, alpha=0.5)
            ax.plot(rect_x, rect_y, color=color, lw=0.6)

        # Hinge line
        if rib.has_control_surface:
            ax.axvline(rib.hinge_x_mm, color="green", ls="--", lw=1.0, alpha=0.8)

        ax.set_aspect("equal")
        ax.set_title(f"{rib.label}  ({rib.chord_mm:.0f} mm)", fontsize=8)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.2)

    # Hide unused axes
    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("Wing Rib Profiles — Sport Flyer\n"
                 "(red=spar/LE/TE  orange=upper longeron  blue=lower longeron  green=hinge)",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, "sport_flyer_rib_gallery.png")

    # Fuselage formers
    nf = len(parts.fuselage_formers)
    if nf > 0:
        fig2, axes2 = plt.subplots(1, nf, figsize=(2.5 * nf, 3))
        if nf == 1:
            axes2 = [axes2]
        for i, former in enumerate(parts.fuselage_formers):
            ax = axes2[i]
            ax.plot(former.x, former.y, "C1", lw=1.2)
            ax.fill(former.x, former.y, alpha=0.1, color="C1")
            for lx, ly in former.longeron_holes:
                ax.plot(lx, ly, "ko", ms=3)
            ax.set_aspect("equal")
            ax.set_title(f"{former.label}\n{former.width_mm:.0f}×{former.height_mm:.0f} mm",
                          fontsize=8)
            ax.tick_params(labelsize=6)
            ax.grid(True, alpha=0.2)
        fig2.suptitle("Fuselage Formers — Sport Flyer", fontsize=12, fontweight="bold")
        fig2.tight_layout()
        save(fig2, "sport_flyer_formers.png")


# =====================================================================
#  Step 5: DXF Export
# =====================================================================

def step_dxf_export(parts):
    banner("STEP 5: DXF Export for Laser Cutting")
    dxf_path = OUT / "sport_flyer_laser_parts.dxf"
    export_parts_dxf(parts, dxf_path, spacing_mm=8.0)
    print(f"  Exported → {dxf_path}")
    print(f"  → Open in any CAD viewer or feed to DeepNest for nesting optimization")


# =====================================================================
#  Main
# =====================================================================

if __name__ == "__main__":
    result = step_design()
    step_3d_viz(result)
    parts, config = step_manufacturing(result)
    step_rib_gallery(parts)
    step_dxf_export(parts)

    banner("PIPELINE COMPLETE")
    print("""
  Design → 3D Viz → Manufacturing → DXF  ✓

  Generated files:
    results/examples/sport_flyer_3d_perspective.png   — 3D rendering
    results/examples/sport_flyer_3d_front.png         — front view
    results/examples/sport_flyer_3d_top.png           — top view
    results/examples/sport_flyer_3d_side.png          — side view
    results/examples/sport_flyer_rib_gallery.png      — all wing ribs
    results/examples/sport_flyer_formers.png          — fuselage formers
    results/examples/sport_flyer_laser_parts.dxf      — laser cut file

  Next steps:
    1. Open .dxf in DeepNest (github.com/nicbarker/deepnest) for nesting
    2. Cut on laser cutter
    3. Assemble!
""")
