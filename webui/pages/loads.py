"""Loads page — Span load distribution (lift, shear, bending)."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/loads", title="Loads", name="Loads")


def layout(**kwargs):
    return html.Div([
        page_header("Structural Loads", "Spanwise lift, shear, and bending moment distributions"),
        dcc.Loading(html.Div(id="loads-content"), type="dot", color="#2563eb"),
    ])


@callback(Output("loads-content", "children"), Input("store-design-result", "data"))
def update_loads(result):
    if not result or "span_loads" not in result:
        return empty_state("mdi:chart-bell-curve-cumulative", "No Load Data", "Run the design pipeline first.")

    sl = result["span_loads"]
    y = np.array(sl["y"])
    lift = np.array(sl["lift_per_span"])
    shear = np.array(sl["shear"])
    bending = np.array(sl["bending"])

    colors = {"lift": "#2563eb", "shear": "#f59e0b", "bending": "#ef4444"}

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=("Lift Distribution (N/m)", "Shear Force (N)", "Bending Moment (N·m)"),
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=y, y=lift, mode="lines", name="Lift/span",
        line=dict(color=colors["lift"], width=2.5),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.1)",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=y, y=shear, mode="lines", name="Shear",
        line=dict(color=colors["shear"], width=2.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.1)",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=y, y=bending, mode="lines", name="Bending",
        line=dict(color=colors["bending"], width=2.5),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.1)",
    ), row=3, col=1)

    fig.update_xaxes(title_text="Span position y (m)", row=3, col=1)
    fig.update_yaxes(title_text="N/m", row=1, col=1)
    fig.update_yaxes(title_text="N", row=2, col=1)
    fig.update_yaxes(title_text="N·m", row=3, col=1)

    fig.update_layout(
        height=700,
        showlegend=False,
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=60, r=20, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    total_lift = sl.get("total_lift", 0)
    max_shear = float(np.max(np.abs(shear))) if len(shear) else 0
    max_bending = float(np.max(np.abs(bending))) if len(bending) else 0

    summary = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("TOTAL LIFT", className="stat-label"),
            html.Div(f"{total_lift:.2f} N", className="stat-value", style={"fontSize": "20px"}),
        ]), className="stat-card"), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("MAX SHEAR", className="stat-label"),
            html.Div(f"{max_shear:.2f} N", className="stat-value", style={"fontSize": "20px"}),
        ]), className="stat-card accent-amber"), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("MAX BENDING", className="stat-label"),
            html.Div(f"{max_bending:.3f} N·m", className="stat-value", style={"fontSize": "20px"}),
        ]), className="stat-card accent-red"), md=4),
    ], className="mb-4 g-3")

    return html.Div([
        summary,
        dbc.Card([
            dbc.CardHeader("Span Load Distributions"),
            dbc.CardBody(dcc.Graph(figure=fig, config={"displaylogo": False})),
        ]),
    ])
