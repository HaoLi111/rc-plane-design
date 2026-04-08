"""Aerodynamics analysis page — Cl, Cd, L/D polars."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/aero", title="Aerodynamics", name="Aerodynamics")

PLOT_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(l=50, r=20, t=40, b=40),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


def layout(**kwargs):
    return html.Div([
        page_header("Aerodynamic Analysis", "Airfoil lift, drag, and efficiency curves from the linear model"),
        dcc.Loading(
            html.Div(id="aero-content"),
            type="dot",
            color="#2563eb",
        ),
    ])


@callback(Output("aero-content", "children"), Input("store-design-result", "data"))
def update_aero(result):
    if not result or "aero" not in result:
        return empty_state("mdi:airplane-off", "No Aero Data", "Run the design pipeline from Configuration first.")

    aero = result["aero"]
    alpha = np.array(aero["alpha"])
    Cl = np.array(aero["Cl"])
    Cd = np.array(aero["Cd"])
    LD = np.array(aero["L_over_D"])

    colors = dict(cl="#2563eb", cd="#ef4444", ld="#22c55e", polar="#8b5cf6")

    # 4-panel figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Lift Coefficient (Cl)", "Drag Coefficient (Cd)", "Lift-to-Drag Ratio (L/D)", "Drag Polar"),
        horizontal_spacing=0.1, vertical_spacing=0.12,
    )

    # Cl vs alpha
    fig.add_trace(go.Scatter(x=alpha, y=Cl, mode="lines", line=dict(color=colors["cl"], width=2.5), name="Cl"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[aero["alpha_Clmax"]], y=[aero["Clmax"]],
        mode="markers+text", marker=dict(size=10, color=colors["cl"]),
        text=[f"Clmax={aero['Clmax']:.2f}"], textposition="top right",
        showlegend=False,
    ), row=1, col=1)

    # Cd vs alpha
    fig.add_trace(go.Scatter(x=alpha, y=Cd, mode="lines", line=dict(color=colors["cd"], width=2.5), name="Cd"), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=[aero["alpha_Cdmin"]], y=[aero["Cdmin"]],
        mode="markers+text", marker=dict(size=10, color=colors["cd"]),
        text=[f"Cdmin={aero['Cdmin']:.4f}"], textposition="top right",
        showlegend=False,
    ), row=1, col=2)

    # L/D vs alpha
    fig.add_trace(go.Scatter(x=alpha, y=LD, mode="lines", line=dict(color=colors["ld"], width=2.5), name="L/D"), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=[aero["alpha_LDmax"]], y=[aero["LDmax"]],
        mode="markers+text", marker=dict(size=10, color=colors["ld"]),
        text=[f"L/Dmax={aero['LDmax']:.1f}"], textposition="top right",
        showlegend=False,
    ), row=2, col=1)

    # Drag polar Cl vs Cd
    fig.add_trace(go.Scatter(x=Cd, y=Cl, mode="lines", line=dict(color=colors["polar"], width=2.5), name="Polar"), row=2, col=2)

    fig.update_xaxes(title_text="α (°)", row=1, col=1)
    fig.update_xaxes(title_text="α (°)", row=1, col=2)
    fig.update_xaxes(title_text="α (°)", row=2, col=1)
    fig.update_xaxes(title_text="Cd", row=2, col=2)
    fig.update_yaxes(title_text="Cl", row=1, col=1)
    fig.update_yaxes(title_text="Cd", row=1, col=2)
    fig.update_yaxes(title_text="L/D", row=2, col=1)
    fig.update_yaxes(title_text="Cl", row=2, col=2)

    fig.update_layout(height=680, showlegend=False, **PLOT_LAYOUT)

    # Summary table
    summary_table = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Metric"), html.Th("Value"), html.Th("At α")])),
            html.Tbody([
                html.Tr([html.Td("Cl max"), html.Td(f"{aero['Clmax']:.3f}"), html.Td(f"{aero['alpha_Clmax']:.1f}°")]),
                html.Tr([html.Td("Cd min"), html.Td(f"{aero['Cdmin']:.5f}"), html.Td(f"{aero['alpha_Cdmin']:.1f}°")]),
                html.Tr([html.Td("L/D max"), html.Td(f"{aero['LDmax']:.2f}"), html.Td(f"{aero['alpha_LDmax']:.1f}°")]),
                html.Tr([html.Td("Cd₀"), html.Td(f"{result.get('Cd_min', 0):.5f}"), html.Td("—")]),
                html.Tr([html.Td("k (induced)"), html.Td(f"{result.get('k', 0):.5f}"), html.Td("—")]),
            ]),
        ],
        bordered=True, hover=True, size="sm", className="mt-3",
    )

    return html.Div([
        dbc.Card([
            dbc.CardHeader("Aerodynamic Polars"),
            dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": True, "displaylogo": False})),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Key Metrics"),
                    dbc.CardBody(summary_table),
                ]),
                md=6,
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Airfoil Model Info"),
                    dbc.CardBody([
                        html.P("Linear aerodynamic model (thin airfoil theory):", className="text-muted mb-2"),
                        html.Div([
                            html.Code("Cl(α) = Clα × (α − α₀)"),
                            html.Br(),
                            html.Code("Cd(α) = Cd₀ + k × Cl²"),
                        ], style={"fontFamily": "monospace", "fontSize": "13px", "lineHeight": "1.8"}),
                        html.Hr(),
                        html.P("This is a preliminary design model suitable for initial sizing. "
                               "For detailed analysis, use XFOIL or NeuralFoil integration.",
                               className="text-muted mb-0", style={"fontSize": "12px"}),
                    ]),
                ]),
                md=6,
            ),
        ]),
    ])
