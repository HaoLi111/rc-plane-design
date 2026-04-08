"""T/W vs W/S constraint analysis and feasibility regions.

Ported from rAviExp constaint.r — all six constraint types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from numpy.typing import ArrayLike

from ..utils.math_helpers import density_isa, dynamic_pressure


@dataclass
class ConstraintParams:
    """Common parameters for constraint analysis."""

    Cd_min: float = 0.02     # minimum drag coefficient (parasite)
    k: float = 0.04          # induced drag factor 1/(pi*AR*e)
    rho: float = 1.225       # air density [kg/m³]
    W_S: np.ndarray = field(default_factory=lambda: np.arange(5, 50.1, 0.1))

    # Turn constraint
    turn_v: float = 20.0     # airspeed in turn [m/s]
    turn_n: float = 1.414    # load factor in turn (e.g. 60° bank → n = 1/cos(60°) = 2)

    # Climb constraint
    climb_vv: float = 5.0    # vertical speed [m/s]
    climb_v: float = 15.0    # airspeed [m/s]

    # Cruise constraint
    cruise_v: float = 20.0   # cruise speed [m/s]

    # Service ceiling
    ceiling_vv: float = 0.5  # residual climb rate at ceiling [m/s]
    ceiling_h: float = 3000.0  # ceiling altitude [m]

    # Takeoff
    to_Cl: float = 1.2       # Cl during takeoff roll
    to_Cd: float = 0.5       # Cd during takeoff roll (gear down, flaps)
    to_mu: float = 0.2       # runway friction coefficient
    to_Sg: float = 30.0      # ground roll distance [m]


def constraint_turn(p: ConstraintParams) -> np.ndarray:
    """Turn constraint: T/W = q(Cd_min/(W/S) + k*(n/q)²*(W/S)).

    Returns T/W for each W/S value.
    """
    q = dynamic_pressure(p.turn_v, p.rho)
    return q * p.Cd_min / p.W_S + p.k * (p.turn_n / q) ** 2 * p.W_S


def constraint_climb(p: ConstraintParams) -> np.ndarray:
    """Climb constraint: T/W = vv/v + q*Cd_min/(W/S) + k*(W/S)/q."""
    q = dynamic_pressure(p.climb_v, p.rho)
    return p.climb_vv / p.climb_v + q * p.Cd_min / p.W_S + p.k * p.W_S / q


def constraint_cruise(p: ConstraintParams) -> np.ndarray:
    """Cruise (level flight): T/W = q*Cd_min/(W/S) + k*(W/S)/q."""
    q = dynamic_pressure(p.cruise_v, p.rho)
    return q * p.Cd_min / p.W_S + p.k * p.W_S / q


def constraint_service_ceiling(p: ConstraintParams) -> np.ndarray:
    """Service ceiling constraint."""
    rho_ceil = density_isa(p.ceiling_h)
    # Best climb speed at ceiling
    v_best = np.sqrt(2 / rho_ceil * p.W_S * np.sqrt(p.k / (3 * p.Cd_min)))
    return p.ceiling_vv / v_best + 4 * np.sqrt(p.k * p.Cd_min / 3)


def constraint_takeoff(p: ConstraintParams) -> np.ndarray:
    """Takeoff ground-roll distance constraint.

    From: v²/(2*g*Sg) + q*Cd_TO/(2*W/S) + mu*(1 - q*Cl_TO/(2*W/S)) = T/W
    Evaluated at liftoff speed: V_lo = sqrt(2*(W/S) / (rho*Cl_TO))
    """
    g = 9.80665
    v_lo = np.sqrt(2 * p.W_S / (p.rho * p.to_Cl))
    q_lo = dynamic_pressure(v_lo, p.rho)
    return (
        v_lo**2 / (2 * g * p.to_Sg)
        + q_lo * p.to_Cd / (2 * p.W_S)
        + p.to_mu * (1 - q_lo * p.to_Cl / (2 * p.W_S))
    )


def constraint_energy_level(
    p: ConstraintParams,
    v: float = 20.0,
    Ps: float = 0.0,
) -> np.ndarray:
    """Energy-level constraint with specific excess power Ps.

    T/W = Ps/v + q*Cd_min/(W/S) + k*(W/S)/q
    """
    q = dynamic_pressure(v, p.rho)
    return Ps / v + q * p.Cd_min / p.W_S + p.k * p.W_S / q


@dataclass
class ConstraintResult:
    """Result of a full constraint analysis."""

    W_S: np.ndarray
    turn: np.ndarray
    climb: np.ndarray
    cruise: np.ndarray
    ceiling: np.ndarray
    takeoff: np.ndarray
    energy: np.ndarray | None = None

    @property
    def envelope(self) -> np.ndarray:
        """Maximum T/W required across all constraints (feasibility boundary)."""
        arrays = [self.turn, self.climb, self.cruise, self.ceiling, self.takeoff]
        if self.energy is not None:
            arrays.append(self.energy)
        return np.maximum.reduce(arrays)

    def plot(self, ax=None):
        """Plot T/W vs W/S constraint diagram."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 7))
        else:
            fig = ax.get_figure()

        ax.plot(self.W_S, self.turn, label="Turn")
        ax.plot(self.W_S, self.climb, label="Climb")
        ax.plot(self.W_S, self.cruise, label="Cruise")
        ax.plot(self.W_S, self.ceiling, label="Service ceiling")
        ax.plot(self.W_S, self.takeoff, label="Takeoff")
        if self.energy is not None:
            ax.plot(self.W_S, self.energy, label="Energy level")

        ax.fill_between(self.W_S, self.envelope, alpha=0.1, color="grey")
        ax.set(xlabel="W/S [N/m²]", ylabel="T/W", title="Constraint Diagram")
        ax.legend()
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)

        return fig, ax


def analyze_constraints(params: ConstraintParams | None = None) -> ConstraintResult:
    """Run full T/W vs W/S constraint analysis."""
    if params is None:
        params = ConstraintParams()

    return ConstraintResult(
        W_S=params.W_S,
        turn=constraint_turn(params),
        climb=constraint_climb(params),
        cruise=constraint_cruise(params),
        ceiling=constraint_service_ceiling(params),
        takeoff=constraint_takeoff(params),
    )
