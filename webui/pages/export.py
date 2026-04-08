"""Export page — download DXF, JSON config, summary report."""

import json
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
from dash_iconify import DashIconify

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/export", title="Export", name="Export")


def layout(**kwargs):
    return html.Div([
        page_header("Export & Download", "Download design files: DXF planforms, JSON configuration, and summary reports"),

        dcc.Loading(html.Div(id="export-content"), type="dot", color="#2563eb"),

        # Hidden download components
        dcc.Download(id="download-json"),
        dcc.Download(id="download-dxf"),
        dcc.Download(id="download-report"),
    ])


@callback(Output("export-content", "children"), Input("store-design-result", "data"))
def update_export(result):
    if not result:
        return empty_state("mdi:download-outline", "Nothing to Export", "Run the design pipeline first.")

    preset = result.get("preset_name", "custom_design")

    return dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    DashIconify(icon="mdi:code-json", width=40, color="#f59e0b"),
                ], className="text-center mb-3"),
                html.H5("Design Configuration", className="text-center"),
                html.P("Full aircraft parameters as JSON — re-import later or share with others.",
                    className="text-muted text-center", style={"fontSize": "13px"}),
                dbc.Button(
                    [DashIconify(icon="mdi:download", width=16), " Download JSON"],
                    id="btn-export-json", color="primary", outline=True, className="w-100",
                ),
            ]),
        ]), md=4),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    DashIconify(icon="mdi:file-cad-box", width=40, color="#2563eb"),
                ], className="text-center mb-3"),
                html.H5("DXF Planforms", className="text-center"),
                html.P("Wing, tail, and airfoil planform outlines in DXF R12 format for CAD/laser cutting.",
                    className="text-muted text-center", style={"fontSize": "13px"}),
                dbc.Button(
                    [DashIconify(icon="mdi:download", width=16), " Download DXF"],
                    id="btn-export-dxf", color="primary", outline=True, className="w-100",
                ),
            ]),
        ]), md=4),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    DashIconify(icon="mdi:file-document-outline", width=40, color="#22c55e"),
                ], className="text-center mb-3"),
                html.H5("Summary Report", className="text-center"),
                html.P("Plain-text summary of all design parameters, performance metrics, and stability checks.",
                    className="text-muted text-center", style={"fontSize": "13px"}),
                dbc.Button(
                    [DashIconify(icon="mdi:download", width=16), " Download Report"],
                    id="btn-export-report", color="primary", outline=True, className="w-100",
                ),
            ]),
        ]), md=4),
    ], className="g-4")


@callback(
    Output("download-json", "data"),
    Input("btn-export-json", "n_clicks"),
    State("store-design-result", "data"),
    prevent_initial_call=True,
)
def export_json(n, result):
    if not result:
        return dash.no_update
    return dict(
        content=json.dumps(result, indent=2, default=str),
        filename="aircraft_design.json",
        type="application/json",
    )


@callback(
    Output("download-dxf", "data"),
    Input("btn-export-dxf", "n_clicks"),
    State("store-design-result", "data"),
    prevent_initial_call=True,
)
def export_dxf(n, result):
    if not result or "concept" not in result:
        return dash.no_update

    from rc_aircraft_design.cad.dxf_writer import DxfWriter
    from rc_aircraft_design.wing.geometry import Wing, planform_coords

    concept = result["concept"]
    dxf = DxfWriter()
    dxf.add_layer("WING", 1)
    dxf.add_layer("HTAIL", 3)
    dxf.add_layer("VTAIL", 2)

    for key, layer in [("wing_main", "WING"), ("wing_horiz", "HTAIL"), ("wing_vert", "VTAIL")]:
        w = concept[key]
        wing = Wing(
            chord_root=w["chord_root"], chord_tip=w["chord_tip"], span=w["span"],
            sweep_deg=w.get("sweep_deg", 0), dihedral_deg=w.get("dihedral_deg", 0),
            foil=w.get("foil", "0012"), type_=w.get("type_", 0),
            x=w.get("x", 0), y=w.get("y", 0), z=w.get("z", 0),
        )
        px, py = planform_coords(wing)
        # Scale to mm
        dxf.add_planform(px * 1000, py * 1000, layer=layer)

    return dict(content=dxf.to_string(), filename="aircraft_planforms.dxf", type="text/plain")


@callback(
    Output("download-report", "data"),
    Input("btn-export-report", "n_clicks"),
    State("store-design-result", "data"),
    prevent_initial_call=True,
)
def export_report(n, result):
    if not result:
        return dash.no_update

    lines = [
        "=" * 60,
        "  RC AIRCRAFT DESIGN — SUMMARY REPORT",
        "=" * 60,
        "",
        f"Design: {result.get('preset_name', 'Custom')}",
        "",
        "── Weight & Power ──",
        f"  Gross mass:     {result.get('m_gross_kg', 0):.3f} kg",
        f"  Gross weight:   {result.get('W_gross_N', 0):.2f} N",
        f"  Shaft power:    {result.get('shaft_power_W', 0):.1f} W",
        f"  Thrust req.:    {result.get('thrust_req_N', 0):.2f} N",
        "",
        "── Constraint Optimum ──",
        f"  T/W optimum:    {result.get('TW_opt', 0):.4f}",
        f"  W/S optimum:    {result.get('WS_opt', 0):.1f} N/m²",
        f"  Wing area:      {result.get('S_wing', 0)*1e4:.0f} cm²",
        "",
        "── Aerodynamics ──",
        f"  L/D max:        {result.get('LDmax', 0):.2f}",
        f"  Cd min:         {result.get('Cd_min', 0):.5f}",
        f"  k (induced):    {result.get('k', 0):.5f}",
        "",
        "── Stability ──",
    ]

    stab = result.get("stability", {})
    for k in ["Vh", "Vv", "static_margin", "X_cg", "X_np", "B", "M_de"]:
        v = stab.get(k, "N/A")
        if isinstance(v, float):
            v = f"{v:.4f}"
        lines.append(f"  {k:16s} {v}")

    lines.append("")
    lines.append("── Stability Checks ──")
    for k, v in result.get("stability_checks", {}).items():
        lines.append(f"  {k:8s}  {'PASS' if v else 'FAIL'}")

    lines += ["", "=" * 60]

    return dict(
        content="\n".join(lines),
        filename="aircraft_design_report.txt",
        type="text/plain",
    )
