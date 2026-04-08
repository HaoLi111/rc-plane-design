"""Motor, propeller, battery sizing, and rubber power models.

Ported from ModelPlanePower (Russell propeller, rubber motor, thrust).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Propeller design (Russell method)
# ---------------------------------------------------------------------------

@dataclass
class Propeller:
    """Propeller geometry from Russell design method.

    All dimensions in metres unless noted.
    """

    diameter: float       # [m]
    radius: float         # [m]
    pitch: float          # [m]
    width: float          # blade width at 75% R [m]
    thickness_wood: float
    thickness_metal: float
    R_upper: float        # upper radius of blade planform
    R_lower: float        # lower radius of blade planform
    R_boss: float         # hub (boss) radius


def design_propeller_russell(
    RPM: float,
    speed_ms: float,
    max_J: float = 0.5,
    max_efficiency: float = 0.7,
) -> Propeller:
    """Design a propeller using Russell's empirical method.

    Parameters
    ----------
    RPM : propeller RPM
    speed_ms : flight speed [m/s]
    max_J : maximum advance ratio (default 0.5)
    max_efficiency : propeller efficiency at design J (default 0.7)

    Returns
    -------
    Propeller geometry
    """
    speed_mph = speed_ms * 2.23694  # m/s → mph
    n_rps = RPM / 60.0

    # Diameter from advance ratio: D = 88 * MPH / (RPM * J)  [inches]
    D_in = 88.0 * speed_mph / (RPM * max_J)
    # Pitch: P = MPH / efficiency * 1.46667 / n  [inches]
    P_in = speed_mph / max_efficiency * 1.46667 / n_rps

    R_in = D_in / 2.0
    width_in = D_in * 0.05
    t_wood = 0.125 * width_in
    t_metal = 0.075 * width_in

    # Convert to metres (1 inch = 0.0254 m)
    c = 0.0254
    return Propeller(
        diameter=D_in * c,
        radius=R_in * c,
        pitch=P_in * c,
        width=width_in * c,
        thickness_wood=t_wood * c,
        thickness_metal=t_metal * c,
        R_upper=0.8 * R_in * c,
        R_lower=0.6 * R_in * c,
        R_boss=0.15 * R_in * c,
    )


def thrust_russell(R_m: float, P_m: float, RPM: float, material: str = "wood") -> float:
    """Theoretical thrust [N] from Russell's method.

    F_t = pi * R * P * n * 0.76 * mu  (in lbs, converted to N)

    Parameters
    ----------
    R_m : propeller radius [m]
    P_m : propeller pitch [m]
    RPM : revolutions per minute
    material : "wood" (mu=0.8) or "metal" (mu=0.85)
    """
    mu = {"wood": 0.8, "metal": 0.85}.get(material, 0.8)
    R_in = R_m / 0.0254
    P_in = P_m / 0.0254
    n_rps = RPM / 60.0
    F_lbs = np.pi * R_in * P_in * n_rps * 0.76 * mu
    return F_lbs * 4.44822  # lbs → N


# ---------------------------------------------------------------------------
# Rubber motor models
# ---------------------------------------------------------------------------

def rubber_breaking_turns_millman(cross_section_area: float, K: float) -> float:
    """Breaking turns per inch (Millman): turns = K / sqrt(A)."""
    return K / np.sqrt(cross_section_area)


def rubber_torque(cross_section_area: float, C: float) -> float:
    """Rubber torque: tau = C * A^1.5."""
    return C * cross_section_area**1.5


def rubber_breaking_turns_sherman(N: int, W: float) -> float:
    """Sherman method: turns = 160*(1 − 2*W) / sqrt(N).

    N = number of strands, W = strand width [inches].
    """
    return 160.0 * (1.0 - 2.0 * W) / np.sqrt(N)


def rubber_torque_sherman(N: int, W: float) -> float:
    """Sherman torque: tau = (0.45 + 10*W) * N^1.38."""
    return (0.45 + 10.0 * W) * N**1.38


# ---------------------------------------------------------------------------
# Battery & electric power sizing
# ---------------------------------------------------------------------------

@dataclass
class ElectricPowerSystem:
    """Simple electric power system sizing."""

    motor_power_W: float       # motor shaft power [W]
    motor_efficiency: float    # motor efficiency (0–1)
    prop_efficiency: float     # propeller efficiency (0–1)
    battery_voltage: float     # nominal battery voltage [V]
    battery_capacity_Ah: float  # battery capacity [Ah]

    @property
    def input_power_W(self) -> float:
        """Electrical input power = shaft power / motor efficiency."""
        return self.motor_power_W / self.motor_efficiency

    @property
    def current_A(self) -> float:
        """Current draw [A]."""
        return self.input_power_W / self.battery_voltage

    @property
    def endurance_min(self) -> float:
        """Estimated endurance [minutes] at full power."""
        return self.battery_capacity_Ah / self.current_A * 60.0

    @property
    def thrust_N(self) -> float:
        """Estimated static thrust [N] (very rough: P_shaft * eta_prop / v_ref).

        Uses a reference speed of 15 m/s for rough static-thrust estimate.
        """
        v_ref = 15.0
        return self.motor_power_W * self.prop_efficiency / v_ref


# ---------------------------------------------------------------------------
# Coarse weight estimation (from rAviExp Weight_coarse.R)
# ---------------------------------------------------------------------------

@dataclass
class WeightEstimate:
    """Coarse weight build-up."""

    m_payload_kg: float
    f_payload: float = 0.3    # payload fraction
    v_cruise_ms: float = 15.0
    P_draw_W: float = 5.0    # electronics draw
    endurance_s: float = 600.0

    @property
    def m_gross_kg(self) -> float:
        """Gross mass = payload / payload_fraction."""
        return self.m_payload_kg / self.f_payload

    @property
    def W_gross_N(self) -> float:
        return self.m_gross_kg * 9.80665
