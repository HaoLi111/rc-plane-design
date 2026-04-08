"""Aerodynamics analysis page — standalone + pipeline, four tabs.

Tabs:
  1. Polars      — Cl, Cd, L/D vs α (works standalone OR from pipeline)
  2. Speed–Lift  — Lift contour over (V × α), stall boundary, L=W curve
  3. V-n Diagram — Load factor envelope (maneuver)
  4. Climb       — Speed, thrust, power vs θ
"""

import json
import traceback

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
from dash_iconify import DashIconify

from components.cards import page_header, empty_state, param_input

dash.register_page(__name__, path="/aero", title="Aerodynamics", name="Aerodynamics")

_PLT = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(l=50, r=20, t=40, b=40),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


# ── Airfoil parameter input panel (shared across tabs) ──────────────────

def _airfoil_panel():
    """Compact input panel for standalone aero analysis."""
    return dbc.Card([
        dbc.CardHeader([
            DashIconify(icon="mdi:tune-vertical-variant", width=16),
            " Airfoil & Flight Params",
            dbc.Button("Analyze", id="aero-btn-run", color="primary", size="sm",
                       className="ms-auto", n_clicks=0),
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(param_input("Clα (1/deg)", "aero-cla", 0.1, step=0.001), md=2),
                dbc.Col(param_input("α₀ (°)", "aero-alpha0", -5.0, step=0.5), md=2),
                dbc.Col(param_input("Cd₀", "aero-cd0", 0.02, step=0.001), md=2),
                dbc.Col(param_input("k (Cdi)", "aero-cdi", 0.0398, step=0.001), md=2),
                dbc.Col(param_input("α stall (°)", "aero-stall-alpha", 15.0, step=0.5), md=2),
                dbc.Col(param_input("S wing (m²)", "aero-wing-area", 0.20, step=0.01), md=2),
            ], className="g-2"),
            dbc.Row([
                dbc.Col(param_input("W (N)", "aero-weight", 9.81, step=0.1), md=2),
                dbc.Col(param_input("ρ (kg/m³)", "aero-rho", 1.225, step=0.01), md=2),
                dbc.Col(param_input("V min (m/s)", "aero-vmin", 3.0, step=0.5), md=2),
                dbc.Col(param_input("V max (m/s)", "aero-vmax", 40.0, step=1), md=2),
                dbc.Col(param_input("n+ limit", "aero-npos", 3.8, step=0.1), md=2),
                dbc.Col(param_input("n− limit", "aero-nneg", -1.5, step=0.1), md=2),
            ], className="g-2 mt-1"),
        ]),
    ], className="mb-3")


# ── Layout ──────────────────────────────────────────────────────────────

def layout(**kwargs):
    return html.Div([
        page_header(
            "Aerodynamic Analysis",
            "Standalone or pipeline: polars, speed–lift contour, V-n diagram, climb performance. "
            "Enter airfoil params and press Analyze, or use data from the design pipeline.",
        ),
        _airfoil_panel(),
        dbc.Tabs([
            dbc.Tab(label="Polars",       tab_id="tab-polars",     id="aero-tab-polars"),
            dbc.Tab(label="Speed–Lift",    tab_id="tab-speed-lift", id="aero-tab-speed-lift"),
            dbc.Tab(label="V-n Diagram",   tab_id="tab-vn",        id="aero-tab-vn"),
            dbc.Tab(label="Climb",         tab_id="tab-climb",     id="aero-tab-climb"),
        ], id="aero-tabs", active_tab="tab-polars", className="mb-3"),
        dcc.Loading(html.Div(id="aero-tab-content"), type="dot", color="#2563eb"),
    ])


# ── Fill inputs from pipeline result if available ────────────────────────

@callback(
    Output("aero-cla", "value"),
    Output("aero-alpha0", "value"),
    Output("aero-cd0", "value"),
    Output("aero-cdi", "value"),
    Output("aero-wing-area", "value"),
    Output("aero-weight", "value"),
    Input("store-design-result", "data"),
    prevent_initial_call=True,
)
def fill_from_pipeline(result):
    if not result:
        return [no_update] * 6
    return [
        result.get("Cla", no_update),
        result.get("alpha0_deg", no_update),
        result.get("Cd_min", no_update),
        result.get("k", no_update),
        result.get("S_wing", no_update),
        result.get("W_gross_N", no_update),
    ]


# ── Main analysis callback ──────────────────────────────────────────────

@callback(
    Output("aero-tab-content", "children"),
    Input("aero-btn-run", "n_clicks"),
    Input("aero-tabs", "active_tab"),
    State("aero-cla", "value"),
    State("aero-alpha0", "value"),
    State("aero-cd0", "value"),
    State("aero-cdi", "value"),
    State("aero-stall-alpha", "value"),
    State("aero-wing-area", "value"),
    State("aero-weight", "value"),
    State("aero-rho", "value"),
    State("aero-vmin", "value"),
    State("aero-vmax", "value"),
    State("aero-npos", "value"),
    State("aero-nneg", "value"),
    State("store-design-result", "data"),
)
def render_tab(n_clicks, active_tab,
               cla, alpha0, cd0, cdi, stall_alpha, S, W, rho, vmin, vmax, npos, nneg,
               pipeline_result):
    try:
        cla = float(cla or 0.1)
        alpha0 = float(alpha0 or -5)
        cd0 = float(cd0 or 0.02)
        cdi = float(cdi or 0.04)
        stall_alpha = float(stall_alpha or 15)
        S = float(S or 0.20)
        W = float(W or 9.81)
        rho = float(rho or 1.225)
        vmin = float(vmin or 3)
        vmax = float(vmax or 40)
        npos = float(npos or 3.8)
        nneg = float(nneg or -1.5)
    except (TypeError, ValueError):
        return dbc.Alert("Check input values — some are invalid.", color="warning")

    from callbacks.stages import run_stage_aero, run_stage_speed_lift, run_stage_vn, run_stage_climb

    try:
        if active_tab == "tab-polars":
            return _render_polars(cla, alpha0, cd0, cdi, pipeline_result)
        elif active_tab == "tab-speed-lift":
            return _render_speed_lift(cla, alpha0, cd0, cdi, stall_alpha, rho, S, W, vmin, vmax)
        elif active_tab == "tab-vn":
            return _render_vn(cla, alpha0, cd0, cdi, stall_alpha, W, S, rho, vmax, npos, nneg)
        elif active_tab == "tab-climb":
            return _render_climb(cd0, cdi, cla, alpha0, rho, S, W)
        else:
            return empty_state("mdi:tab", "Unknown Tab", "")
    except Exception as e:
        return dbc.Alert(f"Analysis error: {e}", color="danger")


# ── Tab 1: Polars ───────────────────────────────────────────────────────

def _render_polars(cla, alpha0, cd0, cdi, pipeline_result=None):
    from callbacks.stages import run_stage_aero

    r = run_stage_aero({"Cla": cla, "alpha0_deg": alpha0, "Cd0": cd0, "Cdi_factor": cdi,
                         "alpha_min": -5, "alpha_max": 20, "alpha_step": 0.5})

    alpha = np.array(r["alpha"])
    Cl = np.array(r["Cl"])
    Cd = np.array(r["Cd"])
    LD = np.array(r["L_over_D"])
    colors = dict(cl="#2563eb", cd="#ef4444", ld="#22c55e", polar="#8b5cf6")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Lift Coefficient (Cl)", "Drag Coefficient (Cd)",
                        "Lift-to-Drag Ratio (L/D)", "Drag Polar"),
        horizontal_spacing=0.1, vertical_spacing=0.12,
    )
    fig.add_trace(go.Scatter(x=alpha, y=Cl, line=dict(color=colors["cl"], width=2.5), name="Cl"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[r["alpha_Clmax"]], y=[r["Clmax"]], mode="markers+text",
        marker=dict(size=10, color=colors["cl"]),
        text=[f"Clmax={r['Clmax']:.2f}"], textposition="top right", showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=alpha, y=Cd, line=dict(color=colors["cd"], width=2.5), name="Cd"), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=[r["alpha_Cdmin"]], y=[r["Cdmin"]], mode="markers+text",
        marker=dict(size=10, color=colors["cd"]),
        text=[f"Cdmin={r['Cdmin']:.4f}"], textposition="top right", showlegend=False,
    ), row=1, col=2)

    fig.add_trace(go.Scatter(x=alpha, y=LD, line=dict(color=colors["ld"], width=2.5), name="L/D"), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=[r["alpha_LDmax"]], y=[r["LDmax"]], mode="markers+text",
        marker=dict(size=10, color=colors["ld"]),
        text=[f"L/Dmax={r['LDmax']:.1f}"], textposition="top right", showlegend=False,
    ), row=2, col=1)

    fig.add_trace(go.Scatter(x=Cd, y=Cl, line=dict(color=colors["polar"], width=2.5), name="Polar"), row=2, col=2)

    fig.update_xaxes(title_text="α (°)", row=1, col=1)
    fig.update_xaxes(title_text="α (°)", row=1, col=2)
    fig.update_xaxes(title_text="α (°)", row=2, col=1)
    fig.update_xaxes(title_text="Cd", row=2, col=2)
    fig.update_yaxes(title_text="Cl", row=1, col=1)
    fig.update_yaxes(title_text="Cd", row=1, col=2)
    fig.update_yaxes(title_text="L/D", row=2, col=1)
    fig.update_yaxes(title_text="Cl", row=2, col=2)
    fig.update_layout(height=680, showlegend=False, **_PLT)

    summary = dbc.Table(
        [html.Thead(html.Tr([html.Th("Metric"), html.Th("Value"), html.Th("At α")])),
         html.Tbody([
             html.Tr([html.Td("Cl max"), html.Td(f"{r['Clmax']:.3f}"), html.Td(f"{r['alpha_Clmax']:.1f}°")]),
             html.Tr([html.Td("Cd min"), html.Td(f"{r['Cdmin']:.5f}"), html.Td(f"{r['alpha_Cdmin']:.1f}°")]),
             html.Tr([html.Td("L/D max"), html.Td(f"{r['LDmax']:.2f}"), html.Td(f"{r['alpha_LDmax']:.1f}°")]),
             html.Tr([html.Td("Cd₀"), html.Td(f"{cd0:.5f}"), html.Td("—")]),
             html.Tr([html.Td("k (induced)"), html.Td(f"{cdi:.5f}"), html.Td("—")]),
         ])],
        bordered=True, hover=True, size="sm",
    )

    return html.Div([
        dbc.Card([dbc.CardHeader("Aerodynamic Polars"),
                  dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": True, "displaylogo": False}))],
                 className="mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader("Key Metrics"), dbc.CardBody(summary)]), md=5),
            dbc.Col(dbc.Card([dbc.CardHeader("Airfoil Model"),
                              dbc.CardBody([
                                  html.Code("Cl(α) = Clα × (α − α₀)"), html.Br(),
                                  html.Code("Cd(α) = Cd₀ + k × Cl²"),
                                  html.Hr(),
                                  html.P("Linear model for initial sizing. Use XFOIL/NeuralFoil for detail.",
                                         className="text-muted mb-0", style={"fontSize": "12px"}),
                              ])]), md=7),
        ]),
    ])


# ── Tab 2: Speed–Lift Contour ──────────────────────────────────────────

def _render_speed_lift(cla, alpha0, cd0, cdi, stall_alpha, rho, S, W, vmin, vmax):
    from callbacks.stages import run_stage_speed_lift

    r = run_stage_speed_lift({
        "Cla": cla, "alpha0_deg": alpha0, "Cd0": cd0, "Cdi_factor": cdi,
        "stall_alpha_deg": stall_alpha, "rho": rho, "S": S, "W": W,
        "v_min": vmin, "v_max": vmax, "alpha_min": -2, "alpha_max": stall_alpha + 2,
    })

    v = np.array(r["v"])
    alpha_arr = np.array(r["alpha"])
    Lift = np.array(r["Lift_grid"])
    lf_alpha = np.array(r["level_flight_alpha"])
    v_stall = r["stall_speed_1g_ms"]

    fig = go.Figure()

    fig.add_trace(go.Contour(
        x=v, y=alpha_arr, z=Lift,
        colorscale="Blues", contours_coloring="heatmap", line_width=1,
        colorbar=dict(title="Lift (N)", len=0.8), name="Lift (N)",
    ))
    fig.add_hline(y=stall_alpha, line_dash="dash", line_color="#ef4444", line_width=2,
                  annotation_text=f"Stall α = {stall_alpha}°", annotation_position="top right")

    mask = (lf_alpha >= alpha_arr.min()) & (lf_alpha <= alpha_arr.max())
    fig.add_trace(go.Scatter(
        x=v[mask], y=lf_alpha[mask], mode="lines",
        line=dict(color="#22c55e", width=3, dash="dot"), name="Level flight (L=W)",
    ))
    if v_stall > 0:
        fig.add_vline(x=v_stall, line_dash="dash", line_color="#f59e0b", line_width=2,
                      annotation_text=f"V_stall = {v_stall:.1f} m/s")

    fig.update_layout(height=520, xaxis_title="Airspeed (m/s)",
                      yaxis_title="Angle of Attack α (°)",
                      title="Speed–Lift Contour", **_PLT)

    stats = dbc.Row([
        dbc.Col(_stat("Stall Speed (1 g)", f"{v_stall:.1f} m/s"), md=3),
        dbc.Col(_stat("Cl at Stall", f"{r['Cl_stall']:.3f}"), md=3),
        dbc.Col(_stat("Weight", f"{W:.2f} N"), md=3),
        dbc.Col(_stat("Wing Area", f"{S:.4f} m²"), md=3),
    ], className="mt-3")

    return html.Div([
        dbc.Card([dbc.CardBody(dcc.Graph(figure=fig, config={"displaylogo": False}))]),
        stats,
    ])


# ── Tab 3: V-n Diagram ─────────────────────────────────────────────────

def _render_vn(cla, alpha0, cd0, cdi, stall_alpha, W, S, rho, vmax, npos, nneg):
    from callbacks.stages import run_stage_vn

    # Clmax from linear model at stall alpha
    Clmax_pos = cla * (stall_alpha - alpha0)
    # Negative Clmax ~ 60 % of positive
    Clmax_neg = -0.6 * Clmax_pos
    WS = W / S if S > 0 else 50

    r = run_stage_vn({
        "Clmax_pos": Clmax_pos, "Clmax_neg": Clmax_neg,
        "W_over_S": WS, "rho": rho,
        "n_limit_pos": npos, "n_limit_neg": nneg, "v_max": vmax,
    })

    v = np.array(r["v"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v, y=np.array(r["n_pos"]), name="n+ (pos)",
                              line=dict(color="#2563eb", width=2.5)))
    fig.add_trace(go.Scatter(x=v, y=np.array(r["n_neg"]), name="n− (neg)",
                              line=dict(color="#ef4444", width=2.5)))
    fig.add_hline(y=r["n_limit_pos"], line_dash="dash", line_color="#2563eb",
                  annotation_text=f"n+ = {r['n_limit_pos']}")
    fig.add_hline(y=r["n_limit_neg"], line_dash="dash", line_color="#ef4444",
                  annotation_text=f"n− = {r['n_limit_neg']}")
    fig.add_hline(y=1.0, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(height=460, xaxis_title="Airspeed (m/s)", yaxis_title="Load Factor n",
                      title="V-n Diagram", **_PLT)

    return html.Div([
        dbc.Card([dbc.CardBody(dcc.Graph(figure=fig, config={"displaylogo": False}))]),
        dbc.Row([
            dbc.Col(_stat("Cl max (pos)", f"{Clmax_pos:.3f}"), md=3),
            dbc.Col(_stat("Cl max (neg)", f"{Clmax_neg:.3f}"), md=3),
            dbc.Col(_stat("W/S", f"{WS:.1f} N/m²"), md=3),
            dbc.Col(_stat("ρ", f"{rho:.3f} kg/m³"), md=3),
        ], className="mt-3"),
    ])


# ── Tab 4: Climb ───────────────────────────────────────────────────────

def _render_climb(cd0, cdi, cla, alpha0, rho, S, W):
    from callbacks.stages import run_stage_climb

    # Use operating Cl for level flight ~ moderate alpha
    Cl_op = cla * (5.0 - alpha0)  # ~5 deg operating
    Cd_op = cd0 + cdi * Cl_op ** 2

    r = run_stage_climb({"Cl": Cl_op, "Cd": Cd_op, "rho": rho, "S": S, "W": W, "theta_max": 60})

    th = np.array(r["theta_deg"])
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Airspeed (m/s)", "Thrust (N)", "Power (W)"))
    fig.add_trace(go.Scatter(x=th, y=np.array(r["v"]), line=dict(color="#2563eb", width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=th, y=np.array(r["thrust"]), line=dict(color="#f59e0b", width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=th, y=np.array(r["power"]), line=dict(color="#ef4444", width=2.5)), row=1, col=3)
    fig.update_xaxes(title_text="θ (°)")
    fig.update_layout(height=380, showlegend=False, **_PLT)

    return html.Div([
        dbc.Card([dbc.CardBody(dcc.Graph(figure=fig, config={"displaylogo": False}))]),
        dbc.Row([
            dbc.Col(_stat("Operating Cl", f"{Cl_op:.3f}"), md=3),
            dbc.Col(_stat("Operating Cd", f"{Cd_op:.5f}"), md=3),
            dbc.Col(_stat("Level Speed", f"{r['v'][0]:.1f} m/s"), md=3),
            dbc.Col(_stat("Level Thrust", f"{r['thrust'][0]:.2f} N"), md=3),
        ], className="mt-3"),
    ])


# ── Helpers ─────────────────────────────────────────────────────────────

def _stat(label, value):
    return dbc.Card(dbc.CardBody([
        html.Div(label, className="text-muted", style={"fontSize": "11px"}),
        html.Div(value, style={"fontSize": "16px", "fontWeight": "600"}),
    ]), className="text-center")
