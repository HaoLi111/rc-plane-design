"""Aerodynamic analysis: angle of attack, lift/drag, airfoil polars."""

from .analysis import (
    Cl_thin, Cd_induced, k_factor, oswald_efficiency, aspect_ratio,
    Cp_prandtl_glauert, Cp_karman_tsien, Cl_alpha_corrected,
    form_factor_wing, form_factor_body, form_factor_nacelle,
    LinearAirfoil, AlphaAnalysis,
    climb_analysis, ClimbAnalysis,
    load_analysis, LoadAnalysis,
)
from .airfoil import naca4, naca4_camber, naca6_thickness
