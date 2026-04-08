"""Discrete spanwise wing load analysis.

Computes cumulative shear force, bending moment, and optionally torsion
along a trapezoid wing half-span, given a spanwise lift distribution.

The load distribution can be:
  - Provided directly (e.g. from VLM / VSPAERO .lod output)
  - Estimated from thin-airfoil Cl with an elliptic correction
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass
class SpanLoadResult:
    """Discrete spanwise structural loads (tip-to-root cumulation)."""

    y: np.ndarray               # spanwise stations [m] (root=0, tip=b/2)
    chord: np.ndarray           # local chord [m]
    lift_per_span: np.ndarray   # distributed lift q(y) [N/m]
    shear: np.ndarray           # cumulative shear V(y) [N]
    bending: np.ndarray         # cumulative bending moment M(y) [N·m]
    torsion: np.ndarray | None = None  # cumulative torsion T(y) [N·m] if computed

    @property
    def total_lift(self) -> float:
        """Total half-wing lift [N] (integrate lift_per_span)."""
        _trapz = getattr(np, "trapezoid", None) or np.trapz
        return float(_trapz(self.lift_per_span, self.y))


def trapezoid_chord(y: ArrayLike, half_span: float, root_chord: float, tip_chord: float) -> np.ndarray:
    """Chord at spanwise station y for a linear-taper wing."""
    y = np.asarray(y, dtype=float)
    eta = np.clip(y / half_span, 0.0, 1.0)
    return root_chord + (tip_chord - root_chord) * eta


def elliptic_Cl(y: ArrayLike, half_span: float, CL_total: float, AR: float) -> np.ndarray:
    """Approximate spanwise Cl assuming elliptic loading.

    Cl(y) = (4 * CL_total) / (pi * AR) * sqrt(1 - (2y/b)^2)  ... section Cl
    But typically we want the *loading* L'(y) = q * c(y) * Cl(y).
    Here we return just the Cl distribution shaped by the elliptic planform.
    """
    y = np.asarray(y, dtype=float)
    eta = np.clip(y / half_span, -1.0, 1.0)
    return CL_total * np.sqrt(np.maximum(1.0 - eta**2, 0.0))


def compute_span_loads(
    y: ArrayLike,
    chord: ArrayLike,
    Cl: ArrayLike,
    q_inf: float,
    weight_per_span: ArrayLike | float = 0.0,
    Cm: ArrayLike | None = None,
) -> SpanLoadResult:
    """Compute shear and bending from discrete spanwise aero data.

    Stations must be ordered root (y=0) → tip (y=b/2).
    Cumulation is from tip to root.

    Parameters
    ----------
    y : Spanwise stations [m], root=0.
    chord : Local chord at each station [m].
    Cl : Local lift coefficient at each station.
    q_inf : Dynamic pressure 0.5 * rho * V^2 [Pa].
    weight_per_span : Distributed wing weight relief [N/m] (subtracted from lift).
        Can be a scalar or per-station array.
    Cm : Local pitching moment coefficient (for torsion). Optional.

    Returns
    -------
    SpanLoadResult with shear, bending, and optionally torsion.
    """
    y = np.asarray(y, dtype=float)
    chord = np.asarray(chord, dtype=float)
    Cl = np.asarray(Cl, dtype=float)
    n = len(y)

    # Lift per unit span: L'(y) = q * c(y) * Cl(y)
    lift_per_span = q_inf * chord * Cl

    # Subtract wing structural weight as a relief load
    w = np.broadcast_to(np.asarray(weight_per_span, dtype=float), (n,)).copy()
    net_load = lift_per_span - w  # net upward load per unit span [N/m]

    # Integrate tip → root using the trapezoidal rule
    # V(y_i) = integral from y_i to y_tip of net_load dy
    # M(y_i) = integral from y_i to y_tip of V(y') dy'
    shear = np.zeros(n)
    bending = np.zeros(n)

    for i in range(n - 2, -1, -1):
        dy = y[i + 1] - y[i]
        # Trapezoidal integration of load → shear
        shear[i] = shear[i + 1] + 0.5 * (net_load[i] + net_load[i + 1]) * dy
        # Trapezoidal integration of shear → bending
        bending[i] = bending[i + 1] + 0.5 * (shear[i] + shear[i + 1]) * dy

    # Optional torsion from pitching moment
    torsion = None
    if Cm is not None:
        Cm = np.asarray(Cm, dtype=float)
        moment_per_span = q_inf * chord**2 * Cm  # [N·m/m]
        torsion = np.zeros(n)
        for i in range(n - 2, -1, -1):
            dy = y[i + 1] - y[i]
            torsion[i] = torsion[i + 1] + 0.5 * (moment_per_span[i] + moment_per_span[i + 1]) * dy

    return SpanLoadResult(
        y=y,
        chord=chord,
        lift_per_span=lift_per_span,
        shear=shear,
        bending=bending,
        torsion=torsion,
    )


def compute_span_loads_simple(
    half_span: float,
    root_chord: float,
    tip_chord: float,
    CL: float,
    velocity: float,
    rho: float = 1.225,
    n_stations: int = 50,
    wing_mass_kg: float = 0.0,
) -> SpanLoadResult:
    """Convenience: estimate span loads for a simple trapezoid wing.

    Uses elliptic Cl distribution and uniform wing weight.

    Parameters
    ----------
    half_span : Half-span [m].
    root_chord, tip_chord : Chord lengths [m].
    CL : Total wing lift coefficient.
    velocity : Airspeed [m/s].
    rho : Air density [kg/m³].
    n_stations : Number of spanwise stations.
    wing_mass_kg : Total wing mass [kg] (distributed uniformly for relief).

    Returns
    -------
    SpanLoadResult
    """
    y = np.linspace(0, half_span, n_stations)
    chord = trapezoid_chord(y, half_span, root_chord, tip_chord)
    S = (root_chord + tip_chord) * half_span  # half-wing area
    AR = (2 * half_span) ** 2 / (2 * S)

    Cl = elliptic_Cl(y, half_span, CL, AR)
    q_inf = 0.5 * rho * velocity**2

    # Uniform weight relief per unit span [N/m]
    g = 9.80665
    if wing_mass_kg > 0:
        weight_per_span = (wing_mass_kg / 2.0) * g / half_span
    else:
        weight_per_span = 0.0

    return compute_span_loads(y, chord, Cl, q_inf, weight_per_span=weight_per_span)


def plot_span_loads(result: SpanLoadResult, ax=None):
    """Plot lift distribution, shear, and bending moment."""
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    else:
        fig = ax[0].get_figure()

    ax[0].plot(result.y, result.lift_per_span)
    ax[0].set(ylabel="Lift/span [N/m]", title="Spanwise Lift Distribution")
    ax[0].fill_between(result.y, result.lift_per_span, alpha=0.2)

    ax[1].plot(result.y, result.shear)
    ax[1].set(ylabel="Shear [N]", title="Shear Force")

    ax[2].plot(result.y, result.bending)
    ax[2].set(xlabel="Spanwise station y [m]", ylabel="Bending [N·m]", title="Bending Moment")

    fig.tight_layout()
    return fig, ax
