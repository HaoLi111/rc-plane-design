"""Stability analysis page — Vh, Vv, SM, spiral stability gauges."""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/stability", title="Stability", name="Stability")

DESIGN_RANGES = {
    "Vh": (0.30, 0.60),
    "Vv": (0.02, 0.05),
    "SM": (-0.40, 0.40),
    "B": (3.0, 8.0),
}


def _gauge(title, value, min_val, max_val, good_lo, good_hi, suffix="", fmt=".3f"):
    """Create a Plotly indicator gauge."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(size=14, family="Inter, sans-serif")),
        number=dict(suffix=suffix, font=dict(size=22)),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickfont=dict(size=10)),
            bar=dict(color="#2563eb"),
            bgcolor="rgba(0,0,0,0.03)",
            steps=[
                dict(range=[min_val, good_lo], color="rgba(239,68,68,0.12)"),
                dict(range=[good_lo, good_hi], color="rgba(34,197,94,0.15)"),
                dict(range=[good_hi, max_val], color="rgba(239,68,68,0.12)"),
            ],
            threshold=dict(
                line=dict(color="#22c55e", width=3),
                thickness=0.8,
                value=value,
            ),
        ),
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def layout(**kwargs):
    return html.Div([
        page_header("Stability & Control", "Static margin, tail volume coefficients, and spiral stability analysis"),
        dcc.Loading(html.Div(id="stability-content"), type="dot", color="#2563eb"),
    ])


@callback(Output("stability-content", "children"), Input("store-design-result", "data"))
def update_stability(result):
    if not result or "stability" not in result:
        return empty_state("mdi:scale-balance", "No Stability Data", "Run the design pipeline first.")

    stab = result["stability"]
    checks = result.get("stability_checks", {})

    Vh = stab.get("Vh", 0)
    Vv = stab.get("Vv", 0)
    SM = stab.get("static_margin", 0)
    B = stab.get("B", 0)
    X_cg = stab.get("X_cg", 0)
    X_np = stab.get("X_np", 0)
    M_de = stab.get("M_de", 0)
    VvB = stab.get("VvB", 0)

    # Gauges
    gauges = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(
            dcc.Graph(figure=_gauge("Horizontal Volume (Vh)", Vh, 0, 1.0, 0.30, 0.60), config={"displayModeBar": False})
        )), md=3),
        dbc.Col(dbc.Card(dbc.CardBody(
            dcc.Graph(figure=_gauge("Vertical Volume (Vv)", Vv, 0, 0.10, 0.02, 0.05), config={"displayModeBar": False})
        )), md=3),
        dbc.Col(dbc.Card(dbc.CardBody(
            dcc.Graph(figure=_gauge("Static Margin (SM)", SM, -0.6, 0.6, -0.40, 0.40), config={"displayModeBar": False})
        )), md=3),
        dbc.Col(dbc.Card(dbc.CardBody(
            dcc.Graph(figure=_gauge("Spiral Stability (B)", B, 0, 15, 3.0, 8.0), config={"displayModeBar": False})
        )), md=3),
    ], className="mb-4 g-3")

    # Detail table
    rows = [
        ("Vh", f"{Vh:.4f}", "0.30 – 0.60", checks.get("Vh", False)),
        ("Vv", f"{Vv:.4f}", "0.02 – 0.05", checks.get("Vv", False)),
        ("Static Margin", f"{SM:.4f}", "−0.40 – 0.40", checks.get("SM", False)),
        ("B (spiral)", f"{B:.2f}", "3.0 – 8.0", checks.get("B", False)),
        ("X_cg", f"{X_cg:.4f} m", "—", None),
        ("X_np", f"{X_np:.4f} m", "—", None),
        ("M_de", f"{M_de:.4f}", "—", None),
        ("VvB", f"{VvB:.4f}", "—", None),
    ]

    def _badge(val):
        if val is None:
            return "—"
        return html.Span("PASS" if val else "FAIL", className="badge-pass" if val else "badge-fail")

    detail_table = dbc.Table([
        html.Thead(html.Tr([html.Th("Parameter"), html.Th("Value"), html.Th("Range"), html.Th("Status")])),
        html.Tbody([
            html.Tr([html.Td(name), html.Td(val), html.Td(rng), html.Td(_badge(ok))])
            for name, val, rng, ok in rows
        ]),
    ], bordered=True, hover=True, size="sm")

    return html.Div([
        gauges,
        dbc.Card([
            dbc.CardHeader("Stability Detail"),
            dbc.CardBody(detail_table),
        ]),
    ])
