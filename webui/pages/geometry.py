"""Geometry page — 3D planform view + MAC details."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/geometry", title="Geometry", name="Geometry")

WING_COLORS = {"main": "#2563eb", "htail": "#22c55e", "vtail": "#f59e0b", "fuselage": "#94a3b8"}


def layout(**kwargs):
    return html.Div([
        page_header("Geometry & Planform", "3D aircraft layout with wing, tail, and fuselage geometry"),
        dcc.Loading(html.Div(id="geometry-content"), type="dot", color="#2563eb"),
    ])


def _planform_xy(w):
    """Generate closed planform polygon from wing dict."""
    cr, ct = w["chord_root"], w["chord_tip"]
    b = w["span"]
    sweep = np.radians(w.get("sweep_deg", 0))
    half_b = b / 2
    xr = w.get("x", 0)

    x_tip_le = xr + half_b * np.tan(sweep)
    # Full-span wing (type_ 0) or half-span (1,2)
    type_ = w.get("type_", 0)

    if type_ == 2:
        # Vertical tail — draw in x-z
        return None  # handled separately

    xs = [xr, xr + cr, x_tip_le + ct, x_tip_le]
    ys = [0, 0, half_b, half_b]

    if type_ == 0:
        # Mirror
        xs += [x_tip_le, x_tip_le + ct, xr + cr, xr]
        ys += [-half_b, -half_b, 0, 0]

    return xs, ys


@callback(Output("geometry-content", "children"), Input("store-design-result", "data"))
def update_geometry(result):
    if not result or "concept" not in result:
        return empty_state("mdi:cube-outline", "No Geometry Data", "Run the design pipeline first.")

    concept = result["concept"]
    wm = concept["wing_main"]
    wh = concept["wing_horiz"]
    wv = concept["wing_vert"]

    # === Top-View 2D ===
    fig_top = go.Figure()

    for w, name, color in [(wm, "Main Wing", WING_COLORS["main"]),
                            (wh, "H-Tail", WING_COLORS["htail"])]:
        coords = _planform_xy(w)
        if coords:
            xs, ys = coords
            fig_top.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", fill="toself",
                fillcolor=color + "18", line=dict(color=color, width=2),
                name=name,
            ))

    # Vertical tail (side projection onto top view — show as line)
    vx = wv.get("x", 0)
    vcr, vct = wv["chord_root"], wv["chord_tip"]
    vspan = wv["span"]
    vsweep = np.radians(wv.get("sweep_deg", 0))
    fig_top.add_trace(go.Scatter(
        x=[vx, vx + vcr], y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["vtail"], width=3, dash="dash"),
        name="V-Tail (root chord)",
    ))

    # Fuselage centerline
    fuse_len = concept.get("fuselage_length", 1.0)
    stations = concept.get("fuselage_stations")
    radii = concept.get("fuselage_radii")

    if stations and radii:
        st = np.array(stations)
        ra = np.array(radii)
        fig_top.add_trace(go.Scatter(
            x=np.concatenate([st, st[::-1]]),
            y=np.concatenate([ra, -ra[::-1]]),
            mode="lines", fill="toself",
            fillcolor="rgba(148,163,184,0.12)",
            line=dict(color=WING_COLORS["fuselage"], width=1.5),
            name="Fuselage",
        ))
    else:
        fig_top.add_trace(go.Scatter(
            x=[0, fuse_len], y=[0, 0],
            mode="lines", line=dict(color=WING_COLORS["fuselage"], width=2, dash="dot"),
            name="Fuselage CL",
        ))

    # CG and NP markers
    x_cg = result.get("X_cg", 0)
    x_np = result.get("X_np", 0)
    if x_cg:
        fig_top.add_trace(go.Scatter(
            x=[x_cg], y=[0], mode="markers+text",
            marker=dict(size=12, color="#ef4444", symbol="x"),
            text=["CG"], textposition="top center", textfont=dict(color="#ef4444", size=11),
            name="CG",
        ))
    if x_np:
        fig_top.add_trace(go.Scatter(
            x=[x_np], y=[0], mode="markers+text",
            marker=dict(size=12, color="#2563eb", symbol="diamond"),
            text=["NP"], textposition="top center", textfont=dict(color="#2563eb", size=11),
            name="NP",
        ))

    fig_top.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=40, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=450,
        xaxis=dict(title="x (m)", scaleanchor="y", scaleratio=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="y (m)", gridcolor="#e2e8f0"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )

    # === Side-View 2D ===
    fig_side = go.Figure()

    # Fuselage side
    if stations and radii:
        st = np.array(stations)
        ra = np.array(radii)
        fig_side.add_trace(go.Scatter(
            x=np.concatenate([st, st[::-1]]),
            y=np.concatenate([ra, -ra[::-1]]),
            mode="lines", fill="toself",
            fillcolor="rgba(148,163,184,0.12)",
            line=dict(color=WING_COLORS["fuselage"], width=1.5),
            name="Fuselage",
        ))

    # Wing root chord (side view)
    fig_side.add_trace(go.Scatter(
        x=[wm["x"], wm["x"] + wm["chord_root"]],
        y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["main"], width=4),
        name="Wing Root",
    ))

    # H-Tail root
    fig_side.add_trace(go.Scatter(
        x=[wh["x"], wh["x"] + wh["chord_root"]],
        y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["htail"], width=3),
        name="H-Tail Root",
    ))

    # V-Tail
    vx_tip = vx + vspan * np.tan(vsweep)
    fig_side.add_trace(go.Scatter(
        x=[vx, vx + vcr, vx_tip + vct, vx_tip, vx],
        y=[0, 0, vspan, vspan, 0],
        mode="lines", fill="toself",
        fillcolor=WING_COLORS["vtail"] + "18",
        line=dict(color=WING_COLORS["vtail"], width=2),
        name="V-Tail",
    ))

    fig_side.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=40, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
        xaxis=dict(title="x (m)", scaleanchor="y", scaleratio=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="z (m)", gridcolor="#e2e8f0"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )

    # === MAC tables ===
    mac_tables = []
    for label, w_key in [("Main Wing", "mac_main"), ("H-Tail", "mac_htail"), ("V-Tail", "mac_vtail")]:
        m = result.get(w_key)
        if m:
            mac_tables.append(dbc.Col(dbc.Card([
                dbc.CardHeader(f"{label} MAC"),
                dbc.CardBody(dbc.Table([
                    html.Tbody([
                        html.Tr([html.Td("MAC Length"), html.Td(f"{m['mac_length']*1000:.1f} mm")]),
                        html.Tr([html.Td("x Sweep"), html.Td(f"{m['x_sweep']*1000:.1f} mm")]),
                        html.Tr([html.Td("y MAC"), html.Td(f"{m['y_mac']*1000:.1f} mm")]),
                        html.Tr([html.Td("x Aero Focus"), html.Td(f"{m['x_aero_focus']*1000:.1f} mm")]),
                    ]),
                ], bordered=True, size="sm")),
            ]), md=4))

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Top View — Planform"),
                dbc.CardBody(dcc.Graph(figure=fig_top, config={"displaylogo": False})),
            ]), lg=7),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Side View"),
                dbc.CardBody(dcc.Graph(figure=fig_side, config={"displaylogo": False})),
            ]), lg=5),
        ], className="mb-4 g-3"),
        dbc.Row(mac_tables, className="g-3") if mac_tables else html.Div(),
    ])
