"""3D surface unfolding to 2D cutting templates.

Ported from eXpand (Julia): quad and triangle unfolding with sequential strips.
Used for foamboard / cardboard manufacturing templates.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from ..utils.math_helpers import euclidean


def _solve_angle_cos(a: float, b: float, c: float) -> float:
    """Law of cosines: angle opposite side *c* given sides a, b, c.

    cos(Z) = (a² + b² − c²) / (2ab)
    """
    cos_val = (a**2 + b**2 - c**2) / (2 * a * b)
    cos_val = np.clip(cos_val, -1.0, 1.0)  # numerical safety
    return float(np.arccos(cos_val))


def expand_quad(
    bl: ArrayLike,
    br: ArrayLike,
    tl: ArrayLike,
    tr: ArrayLike,
    proj_left: tuple[float, float] = (0.0, 0.0),
    proj_right: tuple[float, float] = (1.0, 0.0),
    base_angle_left: float = 0.0,
    base_angle_right: float = np.pi,
) -> dict:
    """Unfold a 3D quadrilateral to 2D, preserving edge lengths.

    Parameters
    ----------
    bl, br, tl, tr : bottom-left, bottom-right, top-left, top-right (3D points)
    proj_left, proj_right : 2D positions of the bottom edge
    base_angle_left, base_angle_right : accumulated fold angles

    Returns
    -------
    dict with keys: p_left, p_right (2D top points), angle_new_left, angle_new_right
    """
    bl, br, tl, tr = (np.asarray(p, dtype=float) for p in (bl, br, tl, tr))
    pl = np.asarray(proj_left, dtype=float)
    pr = np.asarray(proj_right, dtype=float)

    # Edge lengths
    d_bottom = euclidean(bl, br)
    d_left = euclidean(bl, tl)
    d_right = euclidean(br, tr)
    d_diag = euclidean(bl, tr)  # diagonal for triangulation
    d_top = euclidean(tl, tr)

    # Triangle 1: bl-br-tr  (bottom-right triangle)
    angle_bl_1 = _solve_angle_cos(d_bottom, d_diag, d_right)
    # Place tr relative to bottom edge
    angle_tr_from_left = base_angle_left + angle_bl_1
    p_right_2d = pl + d_diag * np.array([np.cos(angle_tr_from_left), np.sin(angle_tr_from_left)])

    # Triangle 2: bl-tl-tr  (top-left triangle)
    d_diag_tl = euclidean(bl, tr)
    d_bl_tl = d_left
    angle_bl_2 = _solve_angle_cos(d_bl_tl, d_diag_tl, d_top)
    angle_tl_from_left = base_angle_left + angle_bl_1 + angle_bl_2
    p_left_2d = pl + d_left * np.array([np.cos(angle_tl_from_left), np.sin(angle_tl_from_left)])

    # New fold angles for next row
    base_len = euclidean(p_left_2d, p_right_2d)
    angle_new_left = angle_tl_from_left
    angle_new_right = np.pi - _solve_angle_cos(d_top, d_right, d_diag) + angle_tr_from_left

    return {
        "p_left": tuple(p_left_2d),
        "p_right": tuple(p_right_2d),
        "angle_new_left": angle_new_left,
        "angle_new_right": angle_new_right,
    }


def expand_triangle(
    bl: ArrayLike,
    br: ArrayLike,
    top: ArrayLike,
    proj_left: tuple[float, float] = (0.0, 0.0),
    proj_right: tuple[float, float] = (1.0, 0.0),
    base_angle_left: float = 0.0,
) -> dict:
    """Unfold a 3D triangle to 2D, preserving edge lengths.

    Returns
    -------
    dict with keys: p_top (2D), angle_new_left, angle_new_right
    """
    bl, br, top = (np.asarray(p, dtype=float) for p in (bl, br, top))
    pl = np.asarray(proj_left, dtype=float)

    d_bottom = euclidean(bl, br)
    d_left = euclidean(bl, top)
    d_right = euclidean(br, top)

    angle_at_bl = _solve_angle_cos(d_bottom, d_left, d_right)
    angle_total = base_angle_left + angle_at_bl

    p_top = pl + d_left * np.array([np.cos(angle_total), np.sin(angle_total)])

    return {
        "p_top": tuple(p_top),
        "angle_new_left": angle_total,
        "angle_new_right": np.pi - _solve_angle_cos(d_right, d_bottom, d_left) + base_angle_left,
    }


def expand_strip(
    left_points: list[ArrayLike],
    right_points: list[ArrayLike],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Unfold a sequential strip of quadrilaterals from 3D to 2D.

    Parameters
    ----------
    left_points : list of N 3D points along the left edge (bottom to top)
    right_points : list of N 3D points along the right edge (bottom to top)

    Returns
    -------
    proj_left, proj_right : lists of 2D projected points
    """
    n = len(left_points)
    if len(right_points) != n:
        raise ValueError("left_points and right_points must have the same length")
    if n < 2:
        raise ValueError("Need at least 2 rows of points")

    # Initial bottom edge
    d0 = euclidean(left_points[0], right_points[0])
    proj_l = [(0.0, 0.0)]
    proj_r = [(d0, 0.0)]
    angle_l = 0.0
    angle_r = np.pi

    for i in range(1, n):
        result = expand_quad(
            left_points[i - 1], right_points[i - 1],
            left_points[i], right_points[i],
            proj_left=proj_l[-1],
            proj_right=proj_r[-1],
            base_angle_left=angle_l,
            base_angle_right=angle_r,
        )
        proj_l.append(result["p_left"])
        proj_r.append(result["p_right"])
        angle_l = result["angle_new_left"]
        angle_r = result["angle_new_right"]

    return proj_l, proj_r


# ---------------------------------------------------------------------------
# Wing surface unfolding helper
# ---------------------------------------------------------------------------

def unfold_wing_surface(
    airfoil_x: ArrayLike,
    airfoil_y: ArrayLike,
    chord_root: float,
    chord_tip: float,
    span: float,
    n_span: int = 10,
    upper: bool = True,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Unfold a wing surface (upper or lower) to a flat 2D template.

    Parameters
    ----------
    airfoil_x, airfoil_y : normalized airfoil coordinates (0–1)
    chord_root, chord_tip : root and tip chords [m]
    span : half-span [m]
    n_span : number of spanwise strips
    upper : True for upper surface, False for lower (negate y)

    Returns
    -------
    proj_left, proj_right : 2D unfolded coordinates
    """
    ax = np.asarray(airfoil_x, dtype=float)
    ay = np.asarray(airfoil_y, dtype=float)
    if not upper:
        ay = -ay

    n_chord = len(ax)
    spanwise = np.linspace(0, span, n_span + 1)

    # Build 3D surface grid: grid[j][i] = 3D point at span station j, chord station i
    grid = []
    for j, y_pos in enumerate(spanwise):
        chord = chord_root + (chord_tip - chord_root) * y_pos / span
        row = [[ax[i] * chord, y_pos, ay[i] * chord] for i in range(n_chord)]
        grid.append(row)

    # Unfold each chordwise strip independently, then concatenate
    all_proj_l: list[tuple[float, float]] = []
    all_proj_r: list[tuple[float, float]] = []
    for j in range(n_span):
        left_edge = [grid[j][i] for i in range(n_chord)]
        right_edge = [grid[j + 1][i] for i in range(n_chord)]
        pl, pr = expand_strip(left_edge, right_edge)
        if j == 0:
            all_proj_l = pl
            all_proj_r = pr
        else:
            # Stitch: shift so left edge aligns with previous right edge
            dx = all_proj_r[-1][0] - pl[0][0]
            dy = all_proj_r[-1][1] - pl[0][1]
            all_proj_r = [(x + dx, y + dy) for x, y in pr]

    return all_proj_l, all_proj_r
