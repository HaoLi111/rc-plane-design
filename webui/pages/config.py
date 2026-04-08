"""Configuration page — aircraft parameter editor + run pipeline."""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, no_update, ALL
from dash_iconify import DashIconify

from components.cards import page_header, param_input, param_row, info_card

dash.register_page(__name__, path="/config", title="Configuration", name="Configuration")


def _mission_panel():
    return dbc.Card([
        dbc.CardHeader([DashIconify(icon="mdi:target", width=16), " Mission Parameters"]),
        dbc.CardBody([
            param_row(
                param_input("Payload (kg)", "cfg-payload-kg", 0.25, min=0.01, step=0.01),
                param_input("Payload Fraction", "cfg-payload-frac", 0.25, min=0.05, max=0.60, step=0.01),
            ),
            param_row(
                param_input("Cruise Speed (m/s)", "cfg-cruise-v", 18.0, min=3, step=0.5),
                param_input("Endurance (s)", "cfg-endurance", 600, min=60, step=30),
            ),
            param_row(
                param_input("Altitude (m)", "cfg-altitude", 200, min=0, step=50),
                param_input("Climb Rate (m/s)", "cfg-climb-rate", 5.0, min=0, step=0.5),
            ),
            param_row(
                param_input("Turn Bank (°)", "cfg-turn-bank", 45, min=10, max=80, step=5),
                param_input("Takeoff Roll (m)", "cfg-to-roll", 20, min=1, step=1),
            ),
        ]),
    ], className="mb-3")


def _airfoil_panel():
    return dbc.Card([
        dbc.CardHeader([DashIconify(icon="mdi:wing", width=16), " Airfoil Parameters"]),
        dbc.CardBody([
            param_row(
                param_input("NACA Code", "cfg-naca-code", "2412", type_="text"),
                param_input("Clα (1/°)", "cfg-cla", 0.1, min=0.01, step=0.005),
            ),
            param_row(
                param_input("α₀ (°)", "cfg-alpha0", -5.0, step=0.5),
                param_input("Cd₀", "cfg-cd0", 0.02, min=0.005, step=0.001),
            ),
            param_row(
                param_input("Cdi Factor (k)", "cfg-cdi-factor", 0.0398, min=0.01, step=0.001),
                html.Div(),  # spacer
            ),
        ]),
    ], className="mb-3")


def _geometry_panel():
    return dbc.Card([
        dbc.CardHeader([DashIconify(icon="mdi:ruler-square", width=16), " Design Choices"]),
        dbc.CardBody([
            param_row(
                param_input("Aspect Ratio", "cfg-ar", 8.0, min=3, max=20, step=0.5),
                param_input("Taper Ratio", "cfg-tr", 0.6, min=0.2, max=1.0, step=0.05),
            ),
            param_row(
                param_input("Sweep (°)", "cfg-sweep", 0, min=-10, max=30, step=1),
                param_input("Dihedral (°)", "cfg-dihedral", 5, min=0, max=15, step=1),
            ),
            param_row(
                param_input("Vh Target", "cfg-vh", 0.45, min=0.2, max=0.8, step=0.01),
                param_input("Vv Target", "cfg-vv", 0.035, min=0.01, max=0.08, step=0.001),
            ),
            param_row(
                param_input("Static Margin Target", "cfg-sm", -0.10, min=-0.5, max=0.5, step=0.01),
                param_input("Fuselage L/D", "cfg-fuse-ld", 8.0, min=4, max=15, step=0.5),
            ),
        ]),
    ], className="mb-3")


def _power_panel():
    return dbc.Card([
        dbc.CardHeader([DashIconify(icon="mdi:battery-charging", width=16), " Power System"]),
        dbc.CardBody([
            param_row(
                param_input("Motor Efficiency", "cfg-motor-eff", 0.80, min=0.3, max=0.98, step=0.01),
                param_input("Propeller Efficiency", "cfg-prop-eff", 0.65, min=0.3, max=0.85, step=0.01),
            ),
            param_row(
                param_input("Battery Voltage (V)", "cfg-batt-v", 11.1, min=3.7, step=0.1),
                param_input("Battery Capacity (Ah)", "cfg-batt-ah", 2.2, min=0.3, step=0.1),
            ),
        ]),
    ], className="mb-3")


def layout(**kwargs):
    return html.Div([
        page_header("Aircraft Configuration", "Define mission parameters, airfoil, geometry, and power system"),

        dbc.Row([
            # Left: input panels
            dbc.Col([
                _mission_panel(),
                _airfoil_panel(),
            ], lg=6),

            # Right: geometry + power + run
            dbc.Col([
                _geometry_panel(),
                _power_panel(),

                # Run button
                html.Div([
                    dbc.Button(
                        [DashIconify(icon="mdi:play-circle", width=20), "  Run Design Pipeline"],
                        id="btn-run-design",
                        className="btn-run w-100",
                        n_clicks=0,
                    ),
                ], className="mt-3 mb-3"),

                # Status
                dcc.Loading(
                    html.Div(id="run-status"),
                    type="dot",
                    color="#2563eb",
                ),
            ], lg=6),
        ]),
    ])
