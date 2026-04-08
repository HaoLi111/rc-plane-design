"""Dashboard — overview page."""

import json
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_iconify import DashIconify

from components.cards import page_header, stat_card, empty_state

dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")

DATA_DIR = Path(__file__).resolve().parents[1] / ".." / "data" / "examples"

PRESETS = [
    ("passive_sport_flyer.json", "Sport Flyer", "Passive design from assumptions — weekend sport flying", "mdi:airplane"),
    ("sport_trainer_40.json", "Sport Trainer .40", "Classic .40-size trainer with gentle handling", "mdi:school-outline"),
    ("classic_2m_glider.json", "2m Glider", "Hand-launch glider, 2m wingspan, no motor", "mdi:weather-windy"),
    ("extra_330sc_3d.json", "Extra 330SC 3D", "High-performance aerobatic pattern plane", "mdi:rotate-3d-variant"),
]


def layout(**kwargs):
    preset_cards = []
    for fname, name, desc, icon in PRESETS:
        preset_cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div([
                            DashIconify(icon=icon, width=32, color="#2563eb"),
                            html.H5(name, className="mt-2 mb-1", style={"fontWeight": "700", "fontSize": "15px"}),
                            html.P(desc, className="text-muted", style={"fontSize": "12px", "margin": 0}),
                        ]),
                    ]),
                    className="preset-card",
                    id={"type": "preset-card", "index": fname},
                    style={"height": "100%"},
                ),
                md=3, sm=6, className="mb-3",
            )
        )

    return html.Div([
        page_header("Dashboard", "RC Aircraft Design Studio — concept to manufacturing in one workflow"),

        # Quick-start presets
        dbc.Card([
            dbc.CardHeader([DashIconify(icon="mdi:rocket-launch-outline", width=16), " Quick Start — Load a Preset"]),
            dbc.CardBody([
                dbc.Row(preset_cards),
                html.Div(id="preset-load-status", className="mt-2"),
            ]),
        ], className="mb-4"),

        # Overview stats (populated after design run)
        html.Div(id="dashboard-stats"),

        # Design summary
        html.Div(id="dashboard-summary"),
    ])


@callback(
    Output("store-aircraft-config", "data", allow_duplicate=True),
    Output("store-preset-name", "data", allow_duplicate=True),
    Output("preset-load-status", "children"),
    Input({"type": "preset-card", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def load_preset(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or all(n is None for n in n_clicks):
        return no_update, no_update, no_update

    prop_id = ctx.triggered[0]["prop_id"]
    fname = json.loads(prop_id.rsplit(".", 1)[0])["index"]

    fpath = DATA_DIR / fname
    if not fpath.exists():
        return no_update, no_update, dbc.Alert(f"File not found: {fname}", color="danger")

    config = json.loads(fpath.read_text())
    label = config.get("name", fname)
    return (
        config,
        label,
        dbc.Alert(
            [DashIconify(icon="mdi:check-circle", width=16), f"  Loaded: {label}"],
            color="success",
            duration=3000,
        ),
    )


@callback(
    Output("dashboard-stats", "children"),
    Output("dashboard-summary", "children"),
    Input("store-design-result", "data"),
    Input("store-preset-name", "data"),
)
def update_dashboard(result, preset_name):
    if not result:
        return (
            empty_state(
                "mdi:airplane-off",
                "No Design Loaded",
                "Select a preset above or go to Configuration to define your aircraft, then run the design pipeline.",
            ),
            "",
        )

    stats_row = dbc.Row([
        dbc.Col(stat_card("Gross Mass", f"{result.get('m_gross_kg', 0):.2f} kg", "accent-cyan", "mdi:weight"), md=3),
        dbc.Col(stat_card("Wing Span", f"{result.get('span_m', 0):.2f} m", "", "mdi:arrow-expand-horizontal"), md=3),
        dbc.Col(stat_card("Wing Area", f"{result.get('S_wing', 0) * 1e4:.0f} cm²", "accent-green"), md=3),
        dbc.Col(stat_card("Shaft Power", f"{result.get('shaft_power_W', 0):.0f} W", "accent-amber"), md=3),
    ], className="mb-4 g-3")

    checks = result.get("stability_checks", {})
    check_badges = []
    for key, passed in checks.items():
        cls = "badge-pass" if passed else "badge-fail"
        txt = "PASS" if passed else "FAIL"
        check_badges.append(
            html.Span([f"{key}: ", html.Span(txt, className=cls)], className="me-3")
        )

    summary = dbc.Card([
        dbc.CardHeader([DashIconify(icon="mdi:clipboard-check-outline", width=16), f" Design Summary — {preset_name or 'Custom'}"]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("Performance", className="text-muted"),
                    html.Div(f"T/W optimum: {result.get('TW_opt', 0):.3f}"),
                    html.Div(f"W/S optimum: {result.get('WS_opt', 0):.1f} N/m²"),
                    html.Div(f"L/D max: {result.get('LDmax', 0):.1f}"),
                ], md=3),
                dbc.Col([
                    html.H6("Stability", className="text-muted"),
                    html.Div(f"Static Margin: {result.get('static_margin', 0):.3f}"),
                    html.Div(f"Vh: {result.get('Vh', 0):.3f}"),
                    html.Div(f"Vv: {result.get('Vv', 0):.4f}"),
                ], md=3),
                dbc.Col([
                    html.H6("Power System", className="text-muted"),
                    html.Div(f"Motor: {result.get('shaft_power_W', 0):.0f} W"),
                    html.Div(f"Thrust: {result.get('thrust_N', 0):.1f} N"),
                    html.Div(f"Endurance: {result.get('endurance_min', 0):.1f} min"),
                ], md=3),
                dbc.Col([
                    html.H6("Stability Checks", className="text-muted"),
                    html.Div(check_badges),
                ], md=3),
            ]),
        ]),
    ], className="mb-4")

    return stats_row, summary
