"""Aerodynamic analysis: angle of attack, lift/drag, airfoil polars.

Ported from rAviExp (ThinAirfoil.R, AFCorr.R) and
ModelAircraftDesignTuningHandbook (liftLine.jl).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike


# ---------------------------------------------------------------------------
# Fundamental coefficients
# ---------------------------------------------------------------------------

def Cl_thin(alpha_rad: float) -> float:
    """Thin-airfoil theory: Cl = 2*pi*alpha."""
    return 2.0 * np.pi * alpha_rad


def Cd_induced(Cl: float, AR: float, e: float = 1.0) -> float:
    """Lift-induced drag coefficient: Cdi = Cl² / (pi * AR * e)."""
    return Cl**2 / (np.pi * AR * e)


def k_factor(AR: float, e: float = 1.0) -> float:
    """Inverse induced-drag factor: k = 1 / (pi * AR * e)."""
    return 1.0 / (np.pi * AR * e)


def oswald_efficiency(AR: float) -> float:
    """Oswald span efficiency (GAAD method 1): e = 1.78(1 − 0.045 AR^0.68) − 0.64."""
    return 1.78 * (1.0 - 0.045 * AR**0.68) - 0.64


def aspect_ratio(span: float, area: float) -> float:
    """AR = b² / S."""
    return span**2 / area


# ---------------------------------------------------------------------------
# Compressibility corrections
# ---------------------------------------------------------------------------

def Cp_prandtl_glauert(Cp0: float, Ma: float) -> float:
    """Prandtl-Glauert compressibility correction."""
    return Cp0 / np.sqrt(1.0 - Ma**2)


def Cp_karman_tsien(Cp0: float, Ma: float) -> float:
    """Kármán-Tsien compressibility correction."""
    beta = np.sqrt(1.0 - Ma**2)
    return Cp0 / (beta + Ma**2 * Cp0 / (2 * (1 + beta)))


def Cl_alpha_corrected(AR: float, sweep_half_chord_rad: float, Ma: float, k: float = 1.0) -> float:
    """Compressible lift-curve slope (per radian).

    CLa = pi*AR / (1 + sqrt(1 + (AR/(2k))² * (1 + tan²Λ - Ma²)))
    """
    term = (AR / (2 * k))**2 * (1.0 + np.tan(sweep_half_chord_rad)**2 - Ma**2)
    return np.pi * AR / (1.0 + np.sqrt(1.0 + term))


# ---------------------------------------------------------------------------
# Form factors (for parasite drag build-up)
# ---------------------------------------------------------------------------

def form_factor_wing(t_c: float) -> float:
    """Wing form factor FF_w (thickness ratio t/c)."""
    return 1.0 + 1.2 * t_c + 100.0 * t_c**4


def form_factor_body(l_d: float) -> float:
    """Body (fuselage) form factor FF_b (fineness ratio l/d)."""
    return 1.0 + 60.0 / l_d**3 + l_d / 400.0


def form_factor_nacelle(l_d: float) -> float:
    """Nacelle form factor FF_n."""
    return 1.0 + 0.35 / l_d


# ---------------------------------------------------------------------------
# Linear airfoil model  (Alpha analysis)
# ---------------------------------------------------------------------------

@dataclass
class LinearAirfoil:
    """Linear airfoil model: Cl = Cla*(alpha − alpha0), Cd = Cd0 + k*Cl²."""

    Cla: float = 0.1          # lift-curve slope [1/deg]
    alpha0_deg: float = -5.0  # zero-lift angle of attack [deg]
    Cd0: float = 0.02         # parasite drag coefficient
    Cdi_factor: float = 0.0398  # induced drag factor  (= 1/(pi*AR*e))

    def Cl(self, alpha_deg: float | ArrayLike) -> np.ndarray:
        alpha_deg = np.asarray(alpha_deg, dtype=float)
        return self.Cla * (alpha_deg - self.alpha0_deg)

    def Cd(self, alpha_deg: float | ArrayLike) -> np.ndarray:
        cl = self.Cl(alpha_deg)
        return self.Cd0 + self.Cdi_factor * cl**2

    def L_over_D(self, alpha_deg: float | ArrayLike) -> np.ndarray:
        cl = self.Cl(alpha_deg)
        cd = self.Cd(alpha_deg)
        return cl / cd

    def analyze(
        self,
        alpha_range: ArrayLike | None = None,
    ) -> "AlphaAnalysis":
        """Run alpha sweep and return analysis results."""
        if alpha_range is None:
            alpha_range = np.arange(-5.0, 20.1, 0.5)
        alpha = np.asarray(alpha_range, dtype=float)
        cl = self.Cl(alpha)
        cd = self.Cd(alpha)
        ld = cl / cd

        idx_clmax = int(np.argmax(cl))
        idx_cdmin = int(np.argmin(cd))
        idx_ldmax = int(np.argmax(ld))

        return AlphaAnalysis(
            alpha=alpha,
            Cl=cl,
            Cd=cd,
            L_over_D=ld,
            alpha_Clmax=float(alpha[idx_clmax]),
            Clmax=float(cl[idx_clmax]),
            alpha_Cdmin=float(alpha[idx_cdmin]),
            Cdmin=float(cd[idx_cdmin]),
            alpha_LDmax=float(alpha[idx_ldmax]),
            LDmax=float(ld[idx_ldmax]),
        )


@dataclass
class AlphaAnalysis:
    """Results of an alpha sweep analysis."""

    alpha: np.ndarray
    Cl: np.ndarray
    Cd: np.ndarray
    L_over_D: np.ndarray
    alpha_Clmax: float
    Clmax: float
    alpha_Cdmin: float
    Cdmin: float
    alpha_LDmax: float
    LDmax: float

    def plot(self, ax=None):
        """4-panel plot: Cl, Cd, L/D vs alpha + drag polar."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(2, 2, figsize=(10, 8))
        else:
            fig = ax.flat[0].get_figure()

        ax[0, 0].plot(self.alpha, self.Cl)
        ax[0, 0].set(xlabel="α [deg]", ylabel="Cl", title="Lift curve")
        ax[0, 0].axhline(self.Clmax, ls="--", color="grey", lw=0.7)

        ax[0, 1].plot(self.alpha, self.Cd)
        ax[0, 1].set(xlabel="α [deg]", ylabel="Cd", title="Drag curve")

        ax[1, 0].plot(self.alpha, self.L_over_D)
        ax[1, 0].set(xlabel="α [deg]", ylabel="L/D", title="Lift-to-drag ratio")
        ax[1, 0].axhline(self.LDmax, ls="--", color="grey", lw=0.7)

        ax[1, 1].plot(self.Cd, self.Cl)
        ax[1, 1].set(xlabel="Cd", ylabel="Cl", title="Drag polar")

        fig.tight_layout()
        return fig, ax


# ---------------------------------------------------------------------------
# Motion / climb analysis (from Theta.R)
# ---------------------------------------------------------------------------

@dataclass
class ClimbAnalysis:
    """Straight climb performance at various flight-path angles."""

    theta_deg: np.ndarray
    v: np.ndarray        # airspeed [m/s]
    vx: np.ndarray       # horizontal speed [m/s]
    vy: np.ndarray       # vertical speed [m/s]
    thrust: np.ndarray   # required thrust [N]
    power: np.ndarray    # required power [W]


def climb_analysis(
    Cl: float,
    Cd: float,
    rho: float,
    S: float,
    W: float,
    theta_range_deg: ArrayLike | None = None,
) -> ClimbAnalysis:
    """Analyze performance across climb angles.

    Parameters
    ----------
    Cl, Cd : operating lift/drag coefficients
    rho : air density [kg/m³]
    S : wing area [m²]
    W : weight [N]
    theta_range_deg : flight path angles [deg]
    """
    if theta_range_deg is None:
        theta_range_deg = np.arange(0, 90.1, 1.0)
    theta = np.asarray(theta_range_deg, dtype=float)
    theta_rad = np.radians(theta)
    k = Cl / Cd

    # minimum speed at each angle (lift = weight component)
    v = np.sqrt(2 * W / (Cl * rho * S)) * np.sqrt(np.cos(theta_rad))
    vx = v * np.cos(theta_rad)
    vy = v * np.sin(theta_rad)

    # thrust = weight*(sin θ + cos θ / (L/D))
    thrust = W * (np.sin(theta_rad) + np.cos(theta_rad) / k)

    # power = thrust * v
    power = thrust * v

    return ClimbAnalysis(
        theta_deg=theta, v=v, vx=vx, vy=vy, thrust=thrust, power=power,
    )


# ---------------------------------------------------------------------------
# Load factor (V-n / V-G diagram)
# ---------------------------------------------------------------------------

@dataclass
class LoadAnalysis:
    """V-n (V-G) diagram data."""

    v: np.ndarray
    n_pos: np.ndarray
    n_neg: np.ndarray
    n_limit_pos: float
    n_limit_neg: float


def load_analysis(
    Clmax_pos: float,
    Clmax_neg: float,
    W_over_S: float,
    rho: float,
    n_limit_pos: float = 3.8,
    n_limit_neg: float = -1.5,
    v_range: ArrayLike | None = None,
) -> LoadAnalysis:
    """Compute V-n envelope.

    n = q * Cl / (W/S)  →  n = 0.5 * rho * v² * Cl / (W/S)
    """
    if v_range is None:
        v_range = np.linspace(0, 80, 500)
    v = np.asarray(v_range, dtype=float)
    q = 0.5 * rho * v**2

    n_pos = np.minimum(q * Clmax_pos / W_over_S, n_limit_pos)
    n_neg = np.maximum(-q * abs(Clmax_neg) / W_over_S, n_limit_neg)

    return LoadAnalysis(
        v=v, n_pos=n_pos, n_neg=n_neg,
        n_limit_pos=n_limit_pos, n_limit_neg=n_limit_neg,
    )
