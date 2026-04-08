"""Workbench — run any stage as a standalone JSON function.

This replaces the .RData workflow from rAviExp.  Each stage takes
JSON input, produces JSON output, and can be exported/imported at
every boundary.  Think of it as calling a function with the right
JSON arguments — the GUI is just a convenience wrapper.
"""

import json
import traceback

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_iconify import DashIconify

from components.cards import page_header
from callbacks.stages import STAGES

dash.register_page(__name__, path="/workbench", title="Workbench", name="Workbench")

_STAGE_OPTIONS = [{"label": f"{v['name']}", "value": k} for k, v in STAGES.items()]


def layout(**kwargs):
    return html.Div([
        page_header(
            "Workbench",
            "Run any analysis stage standalone — paste JSON input, execute, inspect & export output. "
            "Every stage is a pure function: JSON in → JSON out (replaces .RData).",
        ),

        dbc.Row([
            # ── Left: Input ──
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        DashIconify(icon="mdi:function-variant", width=16),
                        " Select Stage & Input",
                    ]),
                    dbc.CardBody([
                        # Stage picker
                        dbc.Label("Stage", className="param-group"),
                        dcc.Dropdown(
                            id="wb-stage-select",
                            options=_STAGE_OPTIONS,
                            value="aero",
                            clearable=False,
                            style={"fontSize": "13px"},
                        ),
                        html.Div(id="wb-stage-desc", className="text-muted mt-1 mb-3",
                                 style={"fontSize": "12px"}),

                        # JSON editor
                        dbc.Label("Input JSON", className="param-group"),
                        dcc.Textarea(
                            id="wb-input-json",
                            style={
                                "width": "100%", "height": "340px",
                                "fontFamily": "Consolas, 'Fira Code', monospace",
                                "fontSize": "12px",
                                "borderRadius": "6px",
                                "border": "1px solid #e2e8f0",
                                "padding": "12px",
                                "backgroundColor": "#f8fafc",
                            },
                        ),

                        # Action row
                        html.Div([
                            dbc.Button(
                                [DashIconify(icon="mdi:play", width=16), " Run Stage"],
                                id="wb-btn-run",
                                className="btn-run me-2",
                                n_clicks=0,
                            ),
                            dcc.Upload(
                                dbc.Button(
                                    [DashIconify(icon="mdi:upload", width=16), " Import JSON"],
                                    color="secondary", outline=True, size="sm",
                                ),
                                id="wb-upload-json",
                                accept=".json",
                            ),
                        ], className="d-flex align-items-center mt-3"),
                    ]),
                ]),
            ], lg=5),

            # ── Right: Output ──
            dbc.Col([
                dcc.Loading(
                    html.Div(id="wb-output"),
                    type="dot", color="#2563eb",
                ),
            ], lg=7),
        ], className="g-3"),
    ])


# ── Populate default JSON when stage changes ────────────────────────────

@callback(
    Output("wb-input-json", "value"),
    Output("wb-stage-desc", "children"),
    Input("wb-stage-select", "value"),
)
def update_default_json(stage_key):
    if not stage_key or stage_key not in STAGES:
        return "", ""
    info = STAGES[stage_key]
    return json.dumps(info["schema"], indent=2), info["desc"]


# ── Import uploaded JSON ─────────────────────────────────────────────────

@callback(
    Output("wb-input-json", "value", allow_duplicate=True),
    Input("wb-upload-json", "contents"),
    State("wb-upload-json", "filename"),
    prevent_initial_call=True,
)
def import_json(contents, filename):
    if contents is None:
        return no_update
    import base64
    _, content_string = contents.split(",")
    decoded = base64.b64decode(content_string).decode("utf-8")
    # Pretty-print
    try:
        obj = json.loads(decoded)
        return json.dumps(obj, indent=2)
    except json.JSONDecodeError:
        return decoded


# ── Run stage ────────────────────────────────────────────────────────────

@callback(
    Output("wb-output", "children"),
    Input("wb-btn-run", "n_clicks"),
    State("wb-stage-select", "value"),
    State("wb-input-json", "value"),
    prevent_initial_call=True,
)
def run_stage(n_clicks, stage_key, input_json_str):
    if not n_clicks or not stage_key:
        return no_update

    # Parse input
    try:
        params = json.loads(input_json_str)
    except json.JSONDecodeError as e:
        return dbc.Alert(f"Invalid JSON: {e}", color="danger")

    # Execute
    try:
        fn = STAGES[stage_key]["fn"]
        result = fn(params)
    except Exception as e:
        tb = traceback.format_exc()
        return html.Div([
            dbc.Alert([DashIconify(icon="mdi:alert-circle", width=16), f" Error: {e}"], color="danger"),
            html.Pre(tb, style={"fontSize": "11px", "maxHeight": "200px", "overflow": "auto"}),
        ])

    # Build output
    output_json = json.dumps(result, indent=2, default=str)

    # Try to build a chart for this stage
    chart = _build_chart(stage_key, result)

    return html.Div([
        # Status
        dbc.Alert(
            [DashIconify(icon="mdi:check-circle", width=16),
             f"  {STAGES[stage_key]['name']} — completed"],
            color="success", duration=4000,
        ),

        # Chart (if available)
        chart if chart else html.Div(),

        # Output JSON
        dbc.Card([
            dbc.CardHeader([
                DashIconify(icon="mdi:code-json", width=16),
                " Output JSON",
                dbc.Button(
                    [DashIconify(icon="mdi:download", width=14), " Export"],
                    id="wb-btn-export",
                    color="primary", outline=True, size="sm",
                    className="ms-auto",
                ),
            ], className="d-flex align-items-center"),
            dbc.CardBody(
                html.Pre(
                    output_json,
                    id="wb-output-json-text",
                    style={
                        "fontSize": "11px", "maxHeight": "400px",
                        "overflow": "auto", "whiteSpace": "pre-wrap",
                        "backgroundColor": "#f8fafc", "padding": "12px",
                        "borderRadius": "6px", "border": "1px solid #e2e8f0",
                    },
                ),
            ),
        ], className="mt-3"),

        # Hidden download
        dcc.Download(id="wb-download"),
        dcc.Store(id="wb-result-store", data=output_json),
    ])


@callback(
    Output("wb-download", "data"),
    Input("wb-btn-export", "n_clicks"),
    State("wb-result-store", "data"),
    prevent_initial_call=True,
)
def export_result(n, json_str):
    if not json_str:
        return no_update
    try:
        obj = json.loads(json_str)
        stage = obj.get("_stage", "output")
    except Exception:
        stage = "output"
    return dict(content=json_str, filename=f"stage_{stage}.json", type="application/json")


# ── Auto-chart builders ─────────────────────────────────────────────────

_PLOT_KW = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(l=50, r=20, t=40, b=40),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


def _build_chart(stage_key: str, result: dict):
    """Auto-generate a Plotly chart from stage output."""
    import numpy as np

    builders = {
        "aero": _chart_aero,
        "constraints": _chart_constraints,
        "climb": _chart_climb,
        "vn_diagram": _chart_vn,
        "speed_lift": _chart_speed_lift,
        "loads": _chart_loads,
    }
    builder = builders.get(stage_key)
    if not builder:
        return None
    try:
        fig = builder(result)
        return dbc.Card([
            dbc.CardBody(dcc.Graph(figure=fig, config={"displaylogo": False})),
        ], className="mb-3")
    except Exception:
        return None


def _chart_aero(r):
    import numpy as np
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Cl vs α", "Cd vs α", "L/D vs α", "Drag Polar"),
                        horizontal_spacing=0.1, vertical_spacing=0.12)
    a, Cl, Cd, LD = np.array(r["alpha"]), np.array(r["Cl"]), np.array(r["Cd"]), np.array(r["L_over_D"])
    fig.add_trace(go.Scatter(x=a, y=Cl, line=dict(color="#2563eb", width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=a, y=Cd, line=dict(color="#ef4444", width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=a, y=LD, line=dict(color="#22c55e", width=2.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=Cd, y=Cl, line=dict(color="#8b5cf6", width=2.5)), row=2, col=2)
    fig.update_layout(height=500, showlegend=False, **_PLOT_KW)
    return fig


def _chart_constraints(r):
    import numpy as np
    ws = np.array(r["W_S"])
    fig = go.Figure()
    for name, color in [("turn", "#8b5cf6"), ("climb", "#22c55e"), ("cruise", "#2563eb"),
                         ("ceiling", "#f59e0b"), ("takeoff", "#ef4444")]:
        fig.add_trace(go.Scatter(x=ws, y=np.array(r[name]), name=name.capitalize(),
                                  line=dict(color=color, width=2.5)))
    fig.add_trace(go.Scatter(x=ws, y=np.array(r["envelope"]), name="Envelope",
                              line=dict(color="#0f172a", width=3, dash="dot"),
                              fill="tozeroy", fillcolor="rgba(37,99,235,0.06)"))
    fig.add_trace(go.Scatter(x=[r["WS_opt"]], y=[r["TW_opt"]], mode="markers",
                              marker=dict(size=12, color="#ef4444", symbol="star"),
                              name="Optimum"))
    fig.update_layout(height=450, xaxis_title="W/S (N/m²)", yaxis_title="T/W", **_PLOT_KW)
    return fig


def _chart_climb(r):
    import numpy as np
    th = np.array(r["theta_deg"])
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Airspeed", "Thrust", "Power"))
    fig.add_trace(go.Scatter(x=th, y=np.array(r["v"]), line=dict(color="#2563eb", width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=th, y=np.array(r["thrust"]), line=dict(color="#f59e0b", width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=th, y=np.array(r["power"]), line=dict(color="#ef4444", width=2.5)), row=1, col=3)
    fig.update_xaxes(title_text="θ (°)")
    fig.update_layout(height=350, showlegend=False, **_PLOT_KW)
    return fig


def _chart_vn(r):
    import numpy as np
    v = np.array(r["v"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v, y=np.array(r["n_pos"]), name="n+ (pos)",
                              line=dict(color="#2563eb", width=2.5),
                              fill="tonexty" if False else None))
    fig.add_trace(go.Scatter(x=v, y=np.array(r["n_neg"]), name="n− (neg)",
                              line=dict(color="#ef4444", width=2.5)))
    fig.add_hline(y=r["n_limit_pos"], line_dash="dash", line_color="#2563eb",
                  annotation_text=f"n+ = {r['n_limit_pos']}")
    fig.add_hline(y=r["n_limit_neg"], line_dash="dash", line_color="#ef4444",
                  annotation_text=f"n− = {r['n_limit_neg']}")
    fig.add_hline(y=1.0, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(height=420, xaxis_title="Airspeed (m/s)", yaxis_title="Load Factor n",
                      title="V-n Diagram", **_PLOT_KW)
    return fig


def _chart_speed_lift(r):
    import numpy as np
    v = np.array(r["v"])
    alpha = np.array(r["alpha"])
    Lift = np.array(r["Lift_grid"])

    fig = go.Figure()

    # Lift contour
    fig.add_trace(go.Contour(
        x=v, y=alpha, z=Lift,
        colorscale="Blues", contours_coloring="heatmap",
        line_width=1,
        colorbar=dict(title="Lift (N)", len=0.8),
        name="Lift (N)",
    ))

    # Stall boundary
    stall_a = r["stall_alpha_deg"]
    fig.add_hline(y=stall_a, line_dash="dash", line_color="#ef4444", line_width=2,
                  annotation_text=f"Stall α = {stall_a}°", annotation_position="top right")

    # Level-flight alpha (L = W)
    lf_alpha = np.array(r["level_flight_alpha"])
    mask = (lf_alpha >= alpha.min()) & (lf_alpha <= alpha.max())
    fig.add_trace(go.Scatter(
        x=v[mask], y=lf_alpha[mask], mode="lines",
        line=dict(color="#22c55e", width=3, dash="dot"),
        name="Level flight (L=W)",
    ))

    # Stall speed marker
    v_stall = r["stall_speed_1g_ms"]
    if v_stall > 0:
        fig.add_vline(x=v_stall, line_dash="dash", line_color="#f59e0b", line_width=2,
                      annotation_text=f"V_stall = {v_stall:.1f} m/s")

    fig.update_layout(
        height=480,
        xaxis_title="Airspeed (m/s)",
        yaxis_title="Angle of Attack α (°)",
        title="Speed–Lift Contour",
        **_PLOT_KW,
    )
    return fig


def _chart_loads(r):
    import numpy as np
    y = np.array(r["y"])
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("Lift (N/m)", "Shear (N)", "Bending (N·m)"),
                        vertical_spacing=0.08)
    fig.add_trace(go.Scatter(x=y, y=np.array(r["lift_per_span"]),
                              line=dict(color="#2563eb", width=2.5),
                              fill="tozeroy", fillcolor="rgba(37,99,235,0.1)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=y, y=np.array(r["shear"]),
                              line=dict(color="#f59e0b", width=2.5),
                              fill="tozeroy", fillcolor="rgba(245,158,11,0.1)"), row=2, col=1)
    fig.add_trace(go.Scatter(x=y, y=np.array(r["bending"]),
                              line=dict(color="#ef4444", width=2.5),
                              fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"), row=3, col=1)
    fig.update_xaxes(title_text="y (m)", row=3, col=1)
    fig.update_layout(height=550, showlegend=False, **_PLOT_KW)
    return fig
