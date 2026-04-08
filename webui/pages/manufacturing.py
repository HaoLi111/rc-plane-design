"""Manufacturing page — rib/former profile preview."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/manufacturing", title="Manufacturing", name="Manufacturing")


def layout(**kwargs):
    return html.Div([
        page_header("Manufacturing", "Wing rib profiles, fuselage formers, and NACA airfoil geometry"),
        dcc.Loading(html.Div(id="mfg-content"), type="dot", color="#2563eb"),
    ])


@callback(Output("mfg-content", "children"), Input("store-design-result", "data"))
def update_manufacturing(result):
    if not result or "concept" not in result:
        return empty_state("mdi:printer-3d-nozzle-outline", "No Manufacturing Data", "Run the design pipeline first.")

    concept = result["concept"]
    wm = concept["wing_main"]
    naca_code = result.get("naca_code", "2412")

    # Generate NACA airfoil preview
    from rc_aircraft_design.aero.airfoil import naca4
    try:
        x, yu, yl = naca4(naca_code, n_points=80)
    except Exception:
        x, yu, yl = naca4("2412", n_points=80)

    fig_airfoil = go.Figure()
    fig_airfoil.add_trace(go.Scatter(
        x=x, y=yu, mode="lines", name="Upper",
        line=dict(color="#2563eb", width=2.5),
    ))
    fig_airfoil.add_trace(go.Scatter(
        x=x, y=yl, mode="lines", name="Lower",
        line=dict(color="#06b6d4", width=2.5),
    ))
    fig_airfoil.add_trace(go.Scatter(
        x=[0.25], y=[0], mode="markers",
        marker=dict(size=8, color="#ef4444", symbol="cross"),
        name="Quarter-chord",
    ))
    fig_airfoil.update_layout(
        title=dict(text=f"NACA {naca_code} Airfoil Profile", font=dict(size=14)),
        xaxis=dict(title="x/c", scaleanchor="y", scaleratio=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="y/c", gridcolor="#e2e8f0"),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        height=300,
        margin=dict(l=50, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=0.7, y=0.95),
    )

    # Rib chord distribution preview
    cr = wm["chord_root"]
    ct = wm["chord_tip"]
    half_span = wm["span"] / 2
    n_ribs = 12
    y_stations = np.linspace(0, half_span, n_ribs)
    chords = cr + (ct - cr) * (y_stations / half_span)

    fig_ribs = go.Figure()
    for i, (yp, ch) in enumerate(zip(y_stations, chords)):
        scale = ch
        fig_ribs.add_trace(go.Scatter(
            x=x * scale * 1000,
            y=(yu if (i % 2 == 0) else yl) * scale * 1000 + i * 8,  # stacked view
            mode="lines",
            line=dict(color="#2563eb" if i % 2 == 0 else "#06b6d4", width=1.5),
            showlegend=False,
            hovertext=f"Rib {i+1}: y={yp*1000:.0f}mm, chord={ch*1000:.0f}mm",
        ))

    fig_ribs.update_layout(
        title=dict(text="Wing Rib Profiles (stacked view)", font=dict(size=14)),
        xaxis=dict(title="mm", gridcolor="#e2e8f0"),
        yaxis=dict(title="mm", gridcolor="#e2e8f0"),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        height=400,
        margin=dict(l=50, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    # Rib table
    rib_rows = [
        html.Tr([
            html.Td(f"{i+1}"),
            html.Td(f"{yp*1000:.0f}"),
            html.Td(f"{ch*1000:.0f}"),
            html.Td(f"{ch*1000*0.12:.1f}"),  # approx thickness for NACA xx12
        ])
        for i, (yp, ch) in enumerate(zip(y_stations, chords))
    ]

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Airfoil Profile"),
                dbc.CardBody(dcc.Graph(figure=fig_airfoil, config={"displaylogo": False})),
            ]), lg=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Rib Schedule"),
                dbc.CardBody(dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("#"), html.Th("y (mm)"), html.Th("Chord (mm)"), html.Th("Thickness (mm)"),
                    ])),
                    html.Tbody(rib_rows),
                ], bordered=True, hover=True, size="sm", style={"maxHeight": "300px", "overflowY": "auto"})),
            ]), lg=6),
        ], className="mb-4 g-3"),

        dbc.Card([
            dbc.CardHeader("Wing Rib Profiles"),
            dbc.CardBody(dcc.Graph(figure=fig_ribs, config={"displaylogo": False})),
        ]),
    ])
