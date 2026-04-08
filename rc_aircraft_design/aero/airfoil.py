"""NACA airfoil generation: 4-digit and 6-series profiles.

Generates (x, y_upper, y_lower) coordinate arrays for airfoil geometry.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def naca4(
    code: str,
    n_points: int = 100,
    cosine_spacing: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate NACA 4-digit airfoil coordinates.

    Parameters
    ----------
    code : 4-character string, e.g. "2412"
        - 1st digit: max camber (% chord)
        - 2nd digit: location of max camber (tenths of chord)
        - 3rd-4th digits: max thickness (% chord)
    n_points : number of points along each surface
    cosine_spacing : use cosine-spaced x for finer LE resolution

    Returns
    -------
    x, y_upper, y_lower : arrays of shape (n_points,)
    """
    if len(code) != 4 or not code.isdigit():
        raise ValueError(f"Invalid NACA 4-digit code: {code!r}")

    m = int(code[0]) / 100.0      # max camber
    p = int(code[1]) / 10.0       # location of max camber
    t = int(code[2:]) / 100.0     # max thickness

    if cosine_spacing:
        beta = np.linspace(0, np.pi, n_points)
        x = 0.5 * (1 - np.cos(beta))
    else:
        x = np.linspace(0, 1, n_points)

    # Thickness distribution (open trailing edge)
    yt = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )

    # Camber line and its derivative
    if m == 0 or p == 0:
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    else:
        yc = np.where(
            x < p,
            m / p**2 * (2 * p * x - x**2),
            m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x**2),
        )
        dyc = np.where(
            x < p,
            2 * m / p**2 * (p - x),
            2 * m / (1 - p) ** 2 * (p - x),
        )

    theta = np.arctan(dyc)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    return x, yu, yl


def naca4_camber(code: str, n_points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Return just the camber line (x, yc) for a NACA 4-digit airfoil."""
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0

    beta = np.linspace(0, np.pi, n_points)
    x = 0.5 * (1 - np.cos(beta))

    if m == 0 or p == 0:
        return x, np.zeros_like(x)

    yc = np.where(
        x < p,
        m / p**2 * (2 * p * x - x**2),
        m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x**2),
    )
    return x, yc


def naca6_thickness(
    t_c: float,
    a: float = 1.0,
    n_points: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """NACA 6-series thickness distribution (simplified).

    Uses the analytical approximation for 6-series profiles.

    Parameters
    ----------
    t_c : max thickness-to-chord ratio (e.g. 0.12)
    a : chordwise extent of uniform loading (0-1, default 1.0)
    n_points : number of points

    Returns
    -------
    x, yt : chordwise stations and half-thickness
    """
    beta = np.linspace(0, np.pi, n_points)
    x = 0.5 * (1 - np.cos(beta))

    # Simplified 6-series: use a modified thickness distribution
    # that provides the laminar bucket shape
    yt = t_c / 0.2 * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4  # closed trailing edge
    )
    # Shift max thickness aft (characteristic of 6-series)
    shift = 0.1 * a
    x_shifted = np.clip(x - shift * np.sin(np.pi * x), 0, 1)
    return x_shifted, yt
