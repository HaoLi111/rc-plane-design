"""Smoke-test examples for aero analysis and wing load modules.

Generates plots to ``results/examples/<run_id>/`` and prints key figures to stdout.
Run with:  uv run python examples/smoke_test_loads.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI / headless
import matplotlib.pyplot as plt
import numpy as np

# Ensure the package is importable even when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rc_aircraft_design.aero.airfoil import naca4, naca4_camber
from rc_aircraft_design.aero.analysis import (
    LinearAirfoil,
    Cd_induced,
    aspect_ratio,
    oswald_efficiency,
)
from rc_aircraft_design.wing.loads import (
    compute_span_loads,
    compute_span_loads_simple,
    elliptic_Cl,
    plot_span_loads,
    trapezoid_chord,
)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = Path(__file__).resolve().parent.parent / "results" / "examples" / RUN_ID
OUT.mkdir(parents=True, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────

def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved → {path}")


# =====================================================================
# Example 1 — NACA Airfoil Profiles
# =====================================================================

def example_airfoils():
    print("\n=== Example 1: NACA Airfoil Profiles ===")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    codes = ["0012", "2412", "4412", "6412"]

    for ax, code in zip(axes.flat, codes):
        x, yu, yl = naca4(code, n_points=150)
        ax.fill_between(x, yl, yu, alpha=0.15, color="C0")
        ax.plot(x, yu, "C0", lw=1.5, label="upper")
        ax.plot(x, yl, "C0", lw=1.5, label="lower")
        # camber
        xc, yc = naca4_camber(code, n_points=150)
        ax.plot(xc, yc, "k--", lw=0.8, label="camber")
        ax.set_title(f"NACA {code}", fontsize=12, fontweight="bold")
        ax.set_aspect("equal")
        ax.set_xlim(-0.02, 1.02)
        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("NACA 4-Digit Airfoil Profiles", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save(fig, "naca_airfoils.png")


# =====================================================================
# Example 2 — Linear Airfoil Alpha Sweep
# =====================================================================

def example_alpha_sweep():
    print("\n=== Example 2: Linear Airfoil Alpha Sweep ===")

    # Typical RC trainer parameters
    span = 1.2        # m
    S = 0.24           # m²  (1200mm × 200mm avg)
    AR = aspect_ratio(span, S)
    e = oswald_efficiency(AR)
    k = 1.0 / (np.pi * AR * e)

    af = LinearAirfoil(
        Cla=0.11,          # per degree, typical cambered airfoil
        alpha0_deg=-2.0,
        Cd0=0.012,
        Cdi_factor=k,
    )
    result = af.analyze(alpha_range=np.arange(-5, 16, 0.5))
    fig, ax = result.plot()
    fig.suptitle(f"RC Trainer Aero  (AR={AR:.1f}, e={e:.2f})", fontsize=13, fontweight="bold", y=1.01)
    save(fig, "alpha_sweep.png")

    print(f"  AR = {AR:.2f},  e = {e:.3f}")
    print(f"  CL_max = {result.Clmax:.3f} at α = {result.alpha_Clmax:.1f}°")
    print(f"  L/D_max = {result.LDmax:.1f} at α = {result.alpha_LDmax:.1f}°")
    print(f"  CD_min = {result.Cdmin:.4f}")


# =====================================================================
# Example 3 — Wing Span Loading (Simple)
# =====================================================================

def example_span_loads_simple():
    print("\n=== Example 3: Trapezoid Wing Span Loads ===")

    half_span = 0.6      # m  (1.2 m total)
    root_chord = 0.25    # m
    tip_chord = 0.15     # m
    CL = 0.8
    V = 15.0             # m/s
    rho = 1.225
    wing_mass = 0.12     # kg

    result = compute_span_loads_simple(
        half_span=half_span,
        root_chord=root_chord,
        tip_chord=tip_chord,
        CL=CL,
        velocity=V,
        rho=rho,
        n_stations=80,
        wing_mass_kg=wing_mass,
    )

    fig, ax = plot_span_loads(result)
    fig.suptitle(
        f"Wing Span Loads — CL={CL}, V={V} m/s, span={2*half_span} m",
        fontsize=13, fontweight="bold", y=1.01,
    )
    save(fig, "span_loads_simple.png")

    print(f"  Half-wing lift   = {result.total_lift:.2f} N")
    print(f"  Root shear       = {result.shear[0]:.2f} N")
    print(f"  Root bending     = {result.bending[0]:.3f} N·m")


# =====================================================================
# Example 4 — Comparing Taper Ratios
# =====================================================================

def example_taper_comparison():
    print("\n=== Example 4: Taper Ratio Comparison ===")

    half_span = 0.6
    root_chord = 0.25
    V = 15.0
    rho = 1.225
    CL = 0.8
    q_inf = 0.5 * rho * V**2
    n = 80

    taper_ratios = [1.0, 0.7, 0.5, 0.3]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for lam in taper_ratios:
        tip_chord = root_chord * lam
        y = np.linspace(0, half_span, n)
        chord = trapezoid_chord(y, half_span, root_chord, tip_chord)
        S_half = (root_chord + tip_chord) * half_span
        AR = (2 * half_span) ** 2 / (2 * S_half)
        Cl = elliptic_Cl(y, half_span, CL, AR)

        result = compute_span_loads(y, chord, Cl, q_inf)

        label = f"λ={lam:.1f}"
        axes[0].plot(result.y, result.lift_per_span, label=label)
        axes[1].plot(result.y, result.shear, label=label)
        axes[2].plot(result.y, result.bending, label=label)

    axes[0].set(xlabel="y [m]", ylabel="Lift/span [N/m]", title="Lift Distribution")
    axes[1].set(xlabel="y [m]", ylabel="Shear [N]", title="Shear Force")
    axes[2].set(xlabel="y [m]", ylabel="Bending [N·m]", title="Bending Moment")

    for ax in axes:
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        f"Effect of Taper Ratio on Structural Loads  (CL={CL}, V={V} m/s)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "taper_comparison.png")

    print("  Plotted taper ratios:", taper_ratios)


# =====================================================================
# Example 5 — V-n (manoeuvre) Envelope
# =====================================================================

def example_load_factor():
    print("\n=== Example 5: V-n Manoeuvre Envelope ===")

    # ── Aircraft parameters ──────────────────────────────────────────
    half_span = 0.6
    root_chord = 0.25
    tip_chord = 0.15
    S = (root_chord + tip_chord) * half_span  # half-wing area × 2
    W = 1.2 * 9.81          # weight [N]  (~1.2 kg AUW)
    rho = 1.225
    CL_max = 1.5            # positive max lift coefficient
    CL_min = -0.8           # negative max lift coefficient (inverted)
    n_pos_limit = 4.0       # positive limit load factor
    n_neg_limit = -2.0      # negative limit load factor
    V_ne = 35.0             # never-exceed speed [m/s]

    # ── Speed range ──────────────────────────────────────────────────
    V = np.linspace(1.0, V_ne + 5.0, 300)

    # aerodynamic load factor: n = 0.5 ρ V² S CL / W
    n_aero_pos = 0.5 * rho * V**2 * S * CL_max / W
    n_aero_neg = 0.5 * rho * V**2 * S * CL_min / W

    # Clamp to structural limits
    n_upper = np.minimum(n_aero_pos, n_pos_limit)
    n_lower = np.maximum(n_aero_neg, n_neg_limit)

    # Stall speeds
    V_s1 = np.sqrt(2 * W / (rho * S * CL_max))   # 1g stall
    V_s_neg = np.sqrt(2 * W / (rho * S * abs(CL_min)))

    # ── Plot ─────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))

    # Positive envelope
    ax.plot(V, n_upper, "C0", linewidth=2, label="+ envelope")
    ax.fill_between(V, 0, n_upper, alpha=0.08, color="C0")

    # Negative envelope
    ax.plot(V, n_lower, "C3", linewidth=2, label="− envelope")
    ax.fill_between(V, 0, n_lower, alpha=0.08, color="C3")

    # Limit load lines
    ax.axhline(n_pos_limit, color="C1", linestyle="--", linewidth=1.2,
               label=f"+n limit = {n_pos_limit:+.1f} g")
    ax.axhline(n_neg_limit, color="C2", linestyle="--", linewidth=1.2,
               label=f"−n limit = {n_neg_limit:+.1f} g")
    ax.axhline(0, color="k", linewidth=0.5)

    # Never-exceed speed
    ax.axvline(V_ne, color="red", linestyle="-.", linewidth=1.5,
               label=f"$V_{{ne}}$ = {V_ne:.0f} m/s")

    # 1g stall speed annotation
    ax.axvline(V_s1, color="C0", linestyle=":", linewidth=1, alpha=0.6)
    ax.annotate(f"$V_{{s1}}$ = {V_s1:.1f} m/s", xy=(V_s1, 1.0),
                xytext=(V_s1 + 1.5, 1.8), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="C0"))

    ax.set(xlabel="Airspeed V [m/s]", ylabel="Load factor n [g]",
           title="V-n Manoeuvre Envelope")
    ax.set_xlim(0, V_ne + 6)
    ax.set_ylim(n_neg_limit - 1, n_pos_limit + 1.5)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save(fig, "load_factor_envelope.png")

    print(f"  V_s1 = {V_s1:.1f} m/s,  V_ne = {V_ne:.0f} m/s")
    print(f"  +n limit = {n_pos_limit:.1f} g,  −n limit = {n_neg_limit:.1f} g")


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    print(f"Run ID: {RUN_ID}")
    print(f"Output directory: {OUT}")
    example_airfoils()
    example_alpha_sweep()
    example_span_loads_simple()
    example_taper_comparison()
    example_load_factor()
    print(f"\nAll examples complete. Plots in {OUT}")
