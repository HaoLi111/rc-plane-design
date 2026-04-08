"""Generate passive-design result images for the README.

Runs the pipeline for three missions, produces:
  - Three-view planform + fuselage centreline for each
  - Constraint diagram for each
  - Summary comparison table printed to stdout

Run with:  uv run python examples/passive_design_gallery.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rc_aircraft_design.passive import run_passive_design, PassiveDesignResult
from rc_aircraft_design.wing.geometry import planform_coords, compute_mac
from rc_aircraft_design.aero.airfoil import naca4

from datetime import datetime
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = Path(__file__).resolve().parent.parent / "results" / "examples" / RUN_ID
OUT.mkdir(parents=True, exist_ok=True)

MISSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "examples" / "missions"
TOPLEVEL = Path(__file__).resolve().parent.parent / "data" / "examples" / "passive_sport_flyer.json"


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {path}")


def load_mission(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Three-view planform plot ─────────────────────────────────────────

def plot_three_view(result: PassiveDesignResult, title: str) -> plt.Figure:
    """Top-view planform + side-view fuselage + CG/NP markers."""
    concept = result.concept
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [2, 1]})

    # --- Top view (planform) ---
    ax = axes[0]
    for wing, color, label in [
        (concept.wing_main, "C0", "Main wing"),
        (concept.wing_horiz, "C1", "H-tail"),
        (concept.wing_vert, "C2", "V-tail"),
    ]:
        px, py = planform_coords(wing)
        ax.fill(px, py, alpha=0.25, color=color)
        ax.plot(px, py, color=color, lw=1.5, label=label)

    # Fuselage centreline
    fuse_l = concept.fuselage_length
    ax.plot([0, fuse_l], [0, 0], "k-", lw=2, label="Fuselage CL")

    # CG and NP markers
    mac = compute_mac(concept.wing_main)
    ax.plot(result.stability.X_cg, 0, "r^", ms=10, zorder=5, label=f"CG ({result.stability.X_cg:.3f} m)")
    ax.plot(result.stability.X_np, 0, "bv", ms=10, zorder=5, label=f"NP ({result.stability.X_np:.3f} m)")

    # MAC bar
    mac_x0 = concept.wing_main.x + mac.x_sweep
    ax.plot([mac_x0, mac_x0 + mac.mac_length], [mac.y_mac, mac.y_mac],
            "k--", lw=1, alpha=0.6)
    ax.annotate("MAC", xy=(mac_x0 + mac.mac_length / 2, mac.y_mac),
                fontsize=7, ha="center", va="bottom")

    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title(f"{title} — Top View")
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(True, alpha=0.3)

    # --- Info panel ---
    ax2 = axes[1]
    ax2.axis("off")
    wm = concept.wing_main
    info_lines = [
        f"Gross mass:  {result.m_gross_kg:.2f} kg",
        f"Wing span:   {wm.span*100:.0f} cm",
        f"Wing area:   {result.S_wing*1e4:.0f} cm²",
        f"Wing AR:     {wm.aspect_ratio:.1f}",
        f"Root chord:  {wm.chord_root*100:.1f} cm",
        f"Tip chord:   {wm.chord_tip*100:.1f} cm",
        f"Taper ratio: {wm.taper_ratio:.2f}",
        f"H-tail S:    {concept.wing_horiz.area*1e4:.0f} cm²",
        f"V-tail S:    {concept.wing_vert.area*1e4:.0f} cm²",
        f"Fuse length: {concept.fuselage_length*100:.0f} cm",
        "",
        f"T/W:         {result.TW_opt:.3f}",
        f"W/S:         {result.WS_opt:.1f} N/m²",
        f"Shaft power: {result.shaft_power_W:.0f} W",
        f"L/D max:     {result.aero.LDmax:.1f}",
        "",
        f"Vh:          {result.stability.Vh:.3f}",
        f"Vv:          {result.stability.Vv:.4f}",
        f"SM:          {result.stability.static_margin:.3f}",
        f"CG:          {result.stability.X_cg*100:.1f} cm",
        f"NP:          {result.stability.X_np*100:.1f} cm",
    ]
    ax2.text(0.05, 0.95, "\n".join(info_lines), transform=ax2.transAxes,
             fontsize=9, fontfamily="monospace", verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


# ── Constraint diagram ───────────────────────────────────────────────

def plot_constraints(result: PassiveDesignResult, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 6))
    cr = result.constraints
    ax.plot(cr.W_S, cr.turn, label="Turn")
    ax.plot(cr.W_S, cr.climb, label="Climb")
    ax.plot(cr.W_S, cr.cruise, label="Cruise")
    ax.plot(cr.W_S, cr.ceiling, label="Service ceiling")
    ax.plot(cr.W_S, cr.takeoff, label="Takeoff")
    ax.fill_between(cr.W_S, cr.envelope, alpha=0.08, color="grey")

    # Mark design point
    ax.plot(result.WS_opt, result.TW_opt, "r*", ms=14, zorder=5,
            label=f"Design point (W/S={result.WS_opt:.1f}, T/W={result.TW_opt:.3f})")

    ax.set(xlabel="W/S [N/m²]", ylabel="T/W", title=f"{title} — Constraint Diagram")
    ax.legend(fontsize=8)
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ── Airfoil profile overlay ─────────────────────────────────────────

def plot_airfoil(result: PassiveDesignResult, title: str, code: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 3))
    x, yu, yl = naca4(code, n_points=150)
    ax.fill_between(x, yl, yu, alpha=0.15, color="C0")
    ax.plot(x, yu, "C0", lw=1.5, label="upper")
    ax.plot(x, yl, "C0", lw=1.5, label="lower")
    ax.set_aspect("equal")
    ax.set_title(f"{title} — NACA {code}", fontsize=12, fontweight="bold")
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ── DXF export demo ─────────────────────────────────────────────────

def export_dxf(result: PassiveDesignResult, name: str):
    from rc_aircraft_design.cad import DxfWriter
    from rc_aircraft_design.aero.airfoil import naca4

    concept = result.concept
    dxf = DxfWriter()

    # Main wing planform
    px, py = planform_coords(concept.wing_main)
    dxf.add_planform(px, py, layer="WING_MAIN")

    # H-tail planform
    px, py = planform_coords(concept.wing_horiz)
    dxf.add_planform(px, py, layer="H_TAIL")

    # V-tail planform
    px, py = planform_coords(concept.wing_vert)
    dxf.add_planform(px, py, layer="V_TAIL")

    # Root airfoil
    code = concept.wing_main.foil
    x, yu, yl = naca4(code, n_points=60)
    dxf.add_airfoil(x, yu, yl, chord=concept.wing_main.chord_root,
                     offset_y=-0.5, layer="AIRFOIL_ROOT")

    # CG marker
    dxf.add_layer("CG_NP", color=1)
    dxf.circle(result.stability.X_cg, 0, 0.01, layer="CG_NP")
    dxf.circle(result.stability.X_np, 0, 0.01, layer="CG_NP")

    path = OUT / f"{name}_planform.dxf"
    dxf.save(path)
    print(f"  saved → {path}")


# ── Multi-mission comparison ─────────────────────────────────────────

def plot_comparison(results: dict[str, PassiveDesignResult]) -> plt.Figure:
    """Side-by-side planform silhouettes of all missions (shared scale)."""
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1:
        axes = [axes]

    # First pass: find global bounding box so all subplots share the same scale
    all_x, all_y = [], []
    for r in results.values():
        concept = r.concept
        for wing in (concept.wing_main, concept.wing_horiz, concept.wing_vert):
            px, py = planform_coords(wing)
            all_x.extend(px)
            all_y.extend(py)
        all_x.append(concept.fuselage_length)
    pad = 0.05
    x_lo, x_hi = min(all_x) - pad, max(all_x) + pad
    y_lo, y_hi = min(all_y) - pad, max(all_y) + pad
    # Ensure symmetric y range (planforms are symmetric about y=0)
    y_abs = max(abs(y_lo), abs(y_hi))
    y_lo, y_hi = -y_abs, y_abs

    for ax, (name, r) in zip(axes, results.items()):
        concept = r.concept
        for wing, color in [
            (concept.wing_main, "C0"),
            (concept.wing_horiz, "C1"),
            (concept.wing_vert, "C2"),
        ]:
            px, py = planform_coords(wing)
            ax.fill(px, py, alpha=0.3, color=color)
            ax.plot(px, py, color=color, lw=1.2)

        fuse_l = concept.fuselage_length
        ax.plot([0, fuse_l], [0, 0], "k-", lw=2)
        ax.plot(r.stability.X_cg, 0, "r^", ms=8)
        ax.plot(r.stability.X_np, 0, "bv", ms=8)

        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(y_lo, y_hi)
        ax.set_aspect("equal")
        ax.set_title(f"{name}\n{r.m_gross_kg:.2f} kg, {concept.wing_main.span*100:.0f} cm span",
                      fontsize=9)
        ax.set_xlabel("x [m]")
        ax.grid(True, alpha=0.2)

    fig.suptitle("Passive Design — Mission Comparison", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


# =====================================================================
#  Main
# =====================================================================

def main():
    # Gather missions
    missions = {}
    if TOPLEVEL.exists():
        missions["Sport Flyer"] = load_mission(TOPLEVEL)
    for p in sorted(MISSIONS_DIR.glob("*.json")):
        missions[p.stem.replace("_", " ").title()] = load_mission(p)

    results: dict[str, PassiveDesignResult] = {}

    for name, data in missions.items():
        print(f"\n{'='*60}")
        print(f"  Mission: {name}")
        print(f"{'='*60}")

        r = run_passive_design(data["assumptions"], data["airfoil"])
        results[name] = r

        slug = name.lower().replace(" ", "_")

        # Three-view
        fig = plot_three_view(r, name)
        save(fig, f"passive_{slug}_threeview.png")

        # Constraint diagram
        fig = plot_constraints(r, name)
        save(fig, f"passive_{slug}_constraints.png")

        # DXF
        export_dxf(r, f"passive_{slug}")

        # Print summary
        wm = r.concept.wing_main
        print(f"  Gross mass:  {r.m_gross_kg:.2f} kg")
        print(f"  Wing span:   {wm.span*100:.0f} cm")
        print(f"  Wing area:   {r.S_wing*1e4:.0f} cm²")
        print(f"  T/W = {r.TW_opt:.3f}   W/S = {r.WS_opt:.1f} N/m²")
        print(f"  SM = {r.stability.static_margin:.3f}   Vh = {r.stability.Vh:.3f}   Vv = {r.stability.Vv:.4f}")

    # Comparison
    print(f"\n{'='*60}")
    print("  Generating comparison chart...")
    fig = plot_comparison(results)
    save(fig, "passive_comparison.png")

    print("\nDone — all images in", OUT)


if __name__ == "__main__":
    main()
