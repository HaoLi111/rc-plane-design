"""Matplotlib-based 3D aircraft visualization (headless-safe, no OpenGL).

Renders a full ConventionalConcept aircraft as a 3D wireframe/surface plot
using only matplotlib — works on any machine without GPU or display server.
"""

from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from ..aero.airfoil import naca4
from ..wing.geometry import Wing, ConventionalConcept
from ..utils.math_helpers import tand


def _wing_surface_points(
    wing: Wing,
    n_span: int = 20,
    n_chord: int = 40,
    side: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate 3D surface grid for one half of a wing panel.

    Returns X, Y, Z arrays of shape (n_span+1, 2*n_chord).
    side: +1 for right half, -1 for left half.
    """
    foil_code = wing.foil if len(wing.foil) == 4 else "0012"
    x_af, yu, yl = naca4(foil_code, n_points=n_chord)

    # Combine upper + lower into one closed profile per section
    # Upper: LE→TE, Lower: TE→LE
    x_profile = np.concatenate([x_af, x_af[::-1]])
    z_profile = np.concatenate([yu, yl[::-1]])
    nc = len(x_profile)

    half_span = wing.span / 2 if wing.type_ == 0 else wing.span
    span_stations = np.linspace(0, half_span, n_span + 1)

    X = np.zeros((n_span + 1, nc))
    Y = np.zeros((n_span + 1, nc))
    Z = np.zeros((n_span + 1, nc))

    for i, y_pos in enumerate(span_stations):
        frac = y_pos / half_span if half_span > 0 else 0
        chord = wing.chord_root + (wing.chord_tip - wing.chord_root) * frac
        sweep_x = y_pos * tand(wing.sweep_deg)
        dihedral_z = y_pos * tand(wing.dihedral_deg)

        # Washout could be added here as rotation about quarter-chord

        X[i, :] = wing.x + sweep_x + x_profile * chord
        if wing.type_ == 2:
            # Vertical tail: span goes in Z direction
            Y[i, :] = wing.y + z_profile * chord
            Z[i, :] = wing.z + y_pos
        else:
            Y[i, :] = wing.y + side * y_pos
            Z[i, :] = wing.z + dihedral_z + z_profile * chord

    return X, Y, Z


def _fuselage_surface(
    concept: ConventionalConcept,
    n_circ: int = 24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate fuselage surface as (X, Y, Z) grid."""
    stations = np.array(concept.fuselage_stations)
    radii = np.array(concept.fuselage_radii)
    ns = len(stations)
    t = np.linspace(0, 2 * np.pi, n_circ, endpoint=True)

    X = np.zeros((ns, n_circ))
    Y = np.zeros((ns, n_circ))
    Z = np.zeros((ns, n_circ))

    for i in range(ns):
        X[i, :] = stations[i]
        Y[i, :] = radii[i] * np.cos(t)
        Z[i, :] = radii[i] * np.sin(t)

    return X, Y, Z


def plot_aircraft_3d(
    concept: ConventionalConcept,
    title: str = "RC Aircraft",
    elev: float = 25.0,
    azim: float = -135.0,
    figsize: tuple[float, float] = (14, 8),
) -> plt.Figure:
    """Render a full 3D view of a ConventionalConcept aircraft.

    Returns a matplotlib Figure with the 3D plot.
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    wing_color = "#4488cc"
    htail_color = "#cc8844"
    vtail_color = "#44aa44"
    fuse_color = "#888888"

    # ── Main wing (both halves) ──────────────────────────────────────
    for side in [+1, -1]:
        X, Y, Z = _wing_surface_points(concept.wing_main, n_span=15, n_chord=30, side=side)
        ax.plot_surface(X, Y, Z, color=wing_color, alpha=0.45, edgecolor=wing_color,
                        linewidth=0.2, shade=True)

    # ── Horizontal tail (both halves) ────────────────────────────────
    for side in [+1, -1]:
        X, Y, Z = _wing_surface_points(concept.wing_horiz, n_span=8, n_chord=20, side=side)
        ax.plot_surface(X, Y, Z, color=htail_color, alpha=0.45, edgecolor=htail_color,
                        linewidth=0.2, shade=True)

    # ── Vertical tail ────────────────────────────────────────────────
    X, Y, Z = _wing_surface_points(concept.wing_vert, n_span=8, n_chord=20, side=1)
    ax.plot_surface(X, Y, Z, color=vtail_color, alpha=0.45, edgecolor=vtail_color,
                    linewidth=0.2, shade=True)

    # ── Fuselage ─────────────────────────────────────────────────────
    Xf, Yf, Zf = _fuselage_surface(concept, n_circ=16)
    ax.plot_surface(Xf, Yf, Zf, color=fuse_color, alpha=0.35, edgecolor=fuse_color,
                    linewidth=0.15, shade=True)

    # ── Axis setup ───────────────────────────────────────────────────
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)

    # Equal aspect ratio
    all_pts = []
    for side in [+1, -1]:
        X, Y, Z = _wing_surface_points(concept.wing_main, n_span=4, n_chord=4, side=side)
        all_pts.append(np.column_stack([X.ravel(), Y.ravel(), Z.ravel()]))
    pts = np.vstack(all_pts)
    max_range = (pts.max(axis=0) - pts.min(axis=0)).max() / 2
    mid = (pts.max(axis=0) + pts.min(axis=0)) / 2
    ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax.set_zlim(mid[2] - max_range * 0.5, mid[2] + max_range * 0.5)

    fig.tight_layout()
    return fig
