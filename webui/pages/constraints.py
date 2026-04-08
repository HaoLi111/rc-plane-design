"""Constraints page — T/W vs W/S constraint diagram."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/constraints", title="Constraints", name="Constraints")

CONSTRAINT_COLORS = {
    "turn": "#8b5cf6",
    "climb": "#22c55e",
    "cruise": "#2563eb",
    "ceiling": "#f59e0b",
    "takeoff": "#ef4444",
}


def layout(**kwargs):
    return html.Div([
        page_header("Constraint Analysis", "Thrust-to-weight vs wing loading feasibility envelope"),
        dcc.Loading(html.Div(id="constraints-content"), type="dot", color="#2563eb"),
    ])


@callback(Output("constraints-content", "children"), Input("store-design-result", "data"))
def update_constraints(result):
    if not result or "constraints" not in result:
        return empty_state("mdi:chart-scatter-plot", "No Constraint Data", "Run the design pipeline first.")

    c = result["constraints"]
    W_S = np.array(c["W_S"])

    fig = go.Figure()

    for name, color in CONSTRAINT_COLORS.items():
        if name in c:
            fig.add_trace(go.Scatter(
                x=W_S, y=np.array(c[name]),
                mode="lines", name=name.capitalize(),
                line=dict(color=color, width=2.5),
            ))

    # Envelope (filled)
    if "envelope" in c:
        envelope = np.array(c["envelope"])
        fig.add_trace(go.Scatter(
            x=W_S, y=envelope,
            mode="lines", name="Envelope",
            line=dict(color="#0f172a", width=3, dash="dot"),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.06)",
        ))

    # Design point
    tw_opt = result.get("TW_opt", 0)
    ws_opt = result.get("WS_opt", 0)
    if tw_opt > 0:
        fig.add_trace(go.Scatter(
            x=[ws_opt], y=[tw_opt],
            mode="markers+text",
            marker=dict(size=14, color="#ef4444", symbol="star", line=dict(width=2, color="#fff")),
            text=[f"Design Point<br>W/S={ws_opt:.1f}, T/W={tw_opt:.3f}"],
            textposition="top right",
            textfont=dict(size=11, color="#ef4444"),
            name="Design Point",
        ))

    fig.update_layout(
        xaxis_title="Wing Loading W/S (N/m²)",
        yaxis_title="Thrust Loading T/W",
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=60, r=20, t=30, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=550,
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(255,255,255,0.8)"),
    )
    fig.update_xaxes(gridcolor="#e2e8f0", zeroline=False)
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False, rangemode="tozero")

    # Summary
    summary = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("DESIGN POINT", className="stat-label"),
            html.Div(f"W/S = {ws_opt:.1f} N/m²", className="stat-value", style={"fontSize": "20px"}),
            html.Div(f"T/W = {tw_opt:.4f}", className="mt-1", style={"fontWeight": "600"}),
        ]), className="stat-card"), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("GROSS WEIGHT", className="stat-label"),
            html.Div(f"{result.get('W_gross_N', 0):.2f} N", className="stat-value", style={"fontSize": "20px"}),
            html.Div(f"{result.get('m_gross_kg', 0):.3f} kg", className="mt-1", style={"fontWeight": "600"}),
        ]), className="stat-card accent-cyan"), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("WING AREA", className="stat-label"),
            html.Div(f"{result.get('S_wing', 0) * 1e4:.0f} cm²", className="stat-value", style={"fontSize": "20px"}),
            html.Div(f"{result.get('S_wing', 0):.4f} m²", className="mt-1", style={"fontWeight": "600"}),
        ]), className="stat-card accent-green"), md=4),
    ], className="mb-4 g-3")

    return html.Div([
        summary,
        dbc.Card([
            dbc.CardHeader("T/W vs W/S Constraint Diagram"),
            dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": True, "displaylogo": False})),
        ]),
    ])
