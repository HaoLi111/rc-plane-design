"""Shared math, interpolation, and optimization helpers."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


# ---------------------------------------------------------------------------
# Trigonometric helpers (degree-based)
# ---------------------------------------------------------------------------

def sind(deg: float | ArrayLike) -> float | np.ndarray:
    """Sine of angle in degrees."""
    return np.sin(np.radians(deg))


def cosd(deg: float | ArrayLike) -> float | np.ndarray:
    """Cosine of angle in degrees."""
    return np.cos(np.radians(deg))


def tand(deg: float | ArrayLike) -> float | np.ndarray:
    """Tangent of angle in degrees."""
    return np.tan(np.radians(deg))


def asind(x: float | ArrayLike) -> float | np.ndarray:
    return np.degrees(np.arcsin(x))


def acosd(x: float | ArrayLike) -> float | np.ndarray:
    return np.degrees(np.arccos(x))


def atand(x: float | ArrayLike) -> float | np.ndarray:
    return np.degrees(np.arctan(x))


# ---------------------------------------------------------------------------
# Standard atmosphere (ISA, SI units)
# ---------------------------------------------------------------------------

_R = 287.05  # specific gas constant for dry air, J/(kg·K)
_g = 9.80665  # gravitational acceleration, m/s²
_T0 = 288.15  # sea-level temperature, K
_P0 = 101325.0  # sea-level pressure, Pa
_rho0 = 1.225  # sea-level density, kg/m³
_L = 0.0065  # temperature lapse rate, K/m (troposphere)


def temperature_isa(h: float) -> float:
    """ISA temperature [K] at altitude *h* [m] (troposphere, h < 11 km)."""
    return _T0 - _L * h


def pressure_isa(h: float) -> float:
    """ISA pressure [Pa] at altitude *h* [m]."""
    return _P0 * (1 - _L * h / _T0) ** (_g / (_L * _R))


def density_isa(h: float) -> float:
    """ISA air density [kg/m³] at altitude *h* [m]."""
    return _rho0 * (1 - _L * h / _T0) ** (_g / (_L * _R) - 1)


def dynamic_pressure(v: float, rho: float | None = None, h: float = 0.0) -> float:
    """Dynamic pressure q = 0.5 * rho * v².

    If *rho* is None, compute from ISA at altitude *h*.
    """
    if rho is None:
        rho = density_isa(h)
    return 0.5 * rho * v**2


# ---------------------------------------------------------------------------
# Reynolds number & skin friction
# ---------------------------------------------------------------------------

def reynolds(rho: float, v: float, L: float, mu: float) -> float:
    """Reynolds number Re = rho * v * L / mu."""
    return rho * v * L / mu


def skin_friction_turbulent(Re: float) -> float:
    """Flat-plate turbulent skin-friction coefficient (Schlichting).

    Cf = 0.455 / (log10(Re))^2.58
    """
    return 0.455 / np.log10(Re) ** 2.58


# ---------------------------------------------------------------------------
# Interpolation helpers
# ---------------------------------------------------------------------------

def interp1d(x: ArrayLike, y: ArrayLike, xq: float) -> float:
    """Simple piecewise-linear 1-D interpolation (no extrapolation)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.interp(xq, x, y))


def arc_length(x: ArrayLike, y: ArrayLike) -> float:
    """Compute arc length of a 2-D polyline."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    return float(np.sum(np.hypot(np.diff(x), np.diff(y))))


def euclidean(p1: ArrayLike, p2: ArrayLike) -> float:
    """Euclidean distance between two points (any dimension)."""
    return float(np.linalg.norm(np.asarray(p1) - np.asarray(p2)))
