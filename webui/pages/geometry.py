"""Geometry page — 3D aircraft view + 2D planforms + MAC details."""

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state

dash.register_page(__name__, path="/geometry", title="Geometry", name="Geometry")

WING_COLORS = {"main": "#2563eb", "htail": "#22c55e", "vtail": "#f59e0b", "fuselage": "#94a3b8"}

def _rgba(hex_color: str, alpha: float = 0.09) -> str:
    """Convert '#RRGGBB' to 'rgba(r,g,b,a)' — Plotly 6 rejects 8-digit hex."""
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{alpha})"


# ── NACA 4-digit airfoil profile (inline to avoid import issues on Render) ──
def _naca4_profile(code: str, n: int = 40):
    """Return (x, yu, yl) arrays for a NACA 4-digit airfoil."""
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    t = int(code[2:]) / 100.0
    beta = np.linspace(0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    if m == 0 or p == 0:
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    else:
        yc = np.where(x < p, m / p**2 * (2 * p * x - x**2), m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2))
        dyc = np.where(x < p, 2 * m / p**2 * (p - x), 2 * m / (1 - p)**2 * (p - x))
    theta = np.arctan(dyc)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    return xu, yu, xl, yl


def _wing_surface_mesh(w, default_foil="2412", n_span=20, n_prof=40, mirror=True):
    """Build Plotly Mesh3d data for a wing with NACA airfoil cross-section.

    Returns list of (x, y, z, i, j, k, color) tuples (one or two for mirror).
    """
    foil = w.get("foil", default_foil) or default_foil
    # Only support 4-digit NACA; fall back to 0012 for anything else
    if len(foil) != 4 or not foil.isdigit():
        foil = "0012"

    xu, yu, xl, yl = _naca4_profile(foil, n_prof)
    # closed loop: upper surface forward, lower surface backward
    prof_x = np.concatenate([xu, xl[::-1]])
    prof_z = np.concatenate([yu, yl[::-1]])
    n_circ = len(prof_x)

    cr = w["chord_root"]
    ct = w["chord_tip"]
    half_b = w["span"] / 2
    sweep_rad = np.radians(w.get("sweep_deg", 0))
    dihedral_rad = np.radians(w.get("dihedral_deg", 0))
    x0 = w.get("x", 0)
    y0 = w.get("y", 0)
    z0 = w.get("z", 0)
    type_ = w.get("type_", 0)  # 0=full, 1=htail, 2=vtail

    spans = np.linspace(0, half_b, n_span + 1)
    surfaces = []

    def _build_half(span_positions, y_sign=1.0):
        verts_x, verts_y, verts_z = [], [], []
        for s in span_positions:
            frac = s / half_b if half_b > 0 else 0
            chord = cr + (ct - cr) * frac
            x_le = x0 + s * np.tan(sweep_rad)
            if type_ == 2:  # vertical tail: span goes in z
                y_pos = y0
                z_pos = z0 + s
            else:
                y_pos = y0 + y_sign * s
                z_pos = z0 + s * np.sin(dihedral_rad)
            for k in range(n_circ):
                verts_x.append(x_le + prof_x[k] * chord)
                verts_y.append(y_pos)
                verts_z.append(z_pos + prof_z[k] * chord)
        ns = len(span_positions)
        ii, jj, kk = [], [], []
        for si in range(ns - 1):
            for ci in range(n_circ):
                cn = (ci + 1) % n_circ
                v00 = si * n_circ + ci
                v01 = si * n_circ + cn
                v10 = (si + 1) * n_circ + ci
                v11 = (si + 1) * n_circ + cn
                ii += [v00, v01]
                jj += [v10, v10]
                kk += [v01, v11]
        return np.array(verts_x), np.array(verts_y), np.array(verts_z), ii, jj, kk

    # First half (positive y)
    vx, vy, vz, ii, jj, kk = _build_half(spans, y_sign=1.0)
    surfaces.append((vx, vy, vz, ii, jj, kk))

    # Mirror for full-span wings (type 0 or htail type 1 that is symmetric)
    if mirror and type_ != 2:
        vx2, vy2, vz2, ii2, jj2, kk2 = _build_half(spans, y_sign=-1.0)
        surfaces.append((vx2, vy2, vz2, ii2, jj2, kk2))

    return surfaces


def _fuselage_mesh3d(concept, n_circ=16):
    """Build Plotly Mesh3d data for a fuselage."""
    stations = concept.get("fuselage_stations")
    radii = concept.get("fuselage_radii")
    if not stations or not radii:
        fuse_len = concept.get("fuselage_length", 1.0)
        # Synthetic stations: nose → max → taper → tail
        stations = [0, fuse_len * 0.1, fuse_len * 0.3, fuse_len * 0.7, fuse_len]
        r_max = fuse_len * 0.04
        radii = [0, r_max * 0.7, r_max, r_max * 0.8, 0.001]

    st = np.array(stations)
    ra = np.array(radii)
    ns = len(st)
    t = np.linspace(0, 2 * np.pi, n_circ, endpoint=False)
    cy, cz = np.cos(t), np.sin(t)

    verts_x, verts_y, verts_z = [], [], []
    for i in range(ns):
        for j in range(n_circ):
            verts_x.append(st[i])
            verts_y.append(ra[i] * cy[j])
            verts_z.append(ra[i] * cz[j])

    ii, jj, kk = [], [], []
    for i in range(ns - 1):
        for j in range(n_circ):
            jn = (j + 1) % n_circ
            v00 = i * n_circ + j
            v01 = i * n_circ + jn
            v10 = (i + 1) * n_circ + j
            v11 = (i + 1) * n_circ + jn
            ii += [v00, v01]
            jj += [v10, v10]
            kk += [v01, v11]
    return np.array(verts_x), np.array(verts_y), np.array(verts_z), ii, jj, kk


def _build_3d_figure(result):
    """Return a Plotly figure with full 3D aircraft mesh."""
    concept = result["concept"]
    naca_code = result.get("naca_code", "2412")
    fig = go.Figure()

    # Fuselage
    fx, fy, fz, fi, fj, fk = _fuselage_mesh3d(concept)
    fig.add_trace(go.Mesh3d(
        x=fx, y=fy, z=fz, i=fi, j=fj, k=fk,
        color=WING_COLORS["fuselage"], opacity=0.45,
        name="Fuselage", flatshading=True,
    ))

    # Wings
    wing_specs = [
        ("wing_main", "Main Wing", WING_COLORS["main"], naca_code, True),
        ("wing_horiz", "H-Tail", WING_COLORS["htail"], "0009", True),
        ("wing_vert", "V-Tail", WING_COLORS["vtail"], "0009", False),
    ]
    for key, name, color, default_foil, mirror in wing_specs:
        w = concept[key]
        surfaces = _wing_surface_mesh(w, default_foil=default_foil, mirror=mirror)
        for idx, (sx, sy, sz, si, sj, sk) in enumerate(surfaces):
            fig.add_trace(go.Mesh3d(
                x=sx, y=sy, z=sz, i=si, j=sj, k=sk,
                color=color, opacity=0.7,
                name=name if idx == 0 else None,
                showlegend=(idx == 0),
                flatshading=True,
            ))

    # CG / NP markers
    x_cg = result.get("X_cg", 0)
    x_np = result.get("X_np", 0)
    if x_cg:
        fig.add_trace(go.Scatter3d(
            x=[x_cg], y=[0], z=[0], mode="markers+text",
            marker=dict(size=6, color="#ef4444", symbol="x"),
            text=["CG"], textposition="top center", name="CG",
        ))
    if x_np:
        fig.add_trace(go.Scatter3d(
            x=[x_np], y=[0], z=[0], mode="markers+text",
            marker=dict(size=6, color="#8b5cf6", symbol="diamond"),
            text=["NP"], textposition="top center", name="NP",
        ))

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        height=550,
        scene=dict(
            aspectmode="data",
            xaxis=dict(title="x (m)", backgroundcolor="rgba(0,0,0,0)", gridcolor="#e2e8f0"),
            yaxis=dict(title="y (m)", backgroundcolor="rgba(0,0,0,0)", gridcolor="#e2e8f0"),
            zaxis=dict(title="z (m)", backgroundcolor="rgba(0,0,0,0)", gridcolor="#e2e8f0"),
            camera=dict(eye=dict(x=1.5, y=1.0, z=0.6)),
        ),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def layout(**kwargs):
    return html.Div([
        page_header("Geometry & Planform", "3D aircraft visualization with NACA airfoil-morphed surfaces"),
        dbc.Tabs([
            dbc.Tab(label="3D Aircraft", tab_id="tab-3d"),
            dbc.Tab(label="Top View", tab_id="tab-top"),
            dbc.Tab(label="Side View", tab_id="tab-side"),
        ], id="geometry-tabs", active_tab="tab-3d", className="mb-3"),
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


@callback(
    Output("geometry-content", "children"),
    Input("store-design-result", "data"),
    Input("geometry-tabs", "active_tab"),
)
def update_geometry(result, active_tab):
    if not result or "concept" not in result:
        return empty_state("mdi:cube-outline", "No Geometry Data", "Run the design pipeline or click a preset on the Dashboard.")

    concept = result["concept"]
    wm = concept["wing_main"]
    wh = concept["wing_horiz"]
    wv = concept["wing_vert"]

    # ── 3D Aircraft tab ──
    if active_tab == "tab-3d":
        fig_3d = _build_3d_figure(result)
        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    "3D Aircraft — NACA ",
                    html.Code(result.get("naca_code", "2412")),
                    " airfoil profile",
                ]),
                dbc.CardBody(dcc.Graph(
                    figure=fig_3d,
                    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}},
                    style={"height": "560px"},
                )),
            ], className="mb-4"),
            _mac_tables(result),
        ])

    # ── Top View tab ──
    if active_tab == "tab-top":
        fig_top = _build_top_view(result, concept, wm, wh, wv)
        return html.Div([
            dbc.Card([
                dbc.CardHeader("Top View — Planform"),
                dbc.CardBody(dcc.Graph(figure=fig_top, config={"displaylogo": False})),
            ], className="mb-4"),
            _mac_tables(result),
        ])

    # ── Side View tab ──
    fig_side = _build_side_view(result, concept, wm, wh, wv)
    return html.Div([
        dbc.Card([
            dbc.CardHeader("Side View"),
            dbc.CardBody(dcc.Graph(figure=fig_side, config={"displaylogo": False})),
        ], className="mb-4"),
        _mac_tables(result),
    ])


def _mac_tables(result):
    """Build MAC info cards row."""
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
    return dbc.Row(mac_tables, className="g-3") if mac_tables else html.Div()


def _build_top_view(result, concept, wm, wh, wv):
    """Build 2D top-view planform figure."""
    fig_top = go.Figure()

    for w, name, color in [(wm, "Main Wing", WING_COLORS["main"]),
                            (wh, "H-Tail", WING_COLORS["htail"])]:
        coords = _planform_xy(w)
        if coords:
            xs, ys = coords
            fig_top.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", fill="toself",
                fillcolor=_rgba(color), line=dict(color=color, width=2),
                name=name,
            ))

    vx = wv.get("x", 0)
    vcr, vct = wv["chord_root"], wv["chord_tip"]
    vspan = wv["span"]
    fig_top.add_trace(go.Scatter(
        x=[vx, vx + vcr], y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["vtail"], width=3, dash="dash"),
        name="V-Tail (root chord)",
    ))

    fuse_len = concept.get("fuselage_length", 1.0)
    stations = concept.get("fuselage_stations")
    radii = concept.get("fuselage_radii")
    if stations and radii:
        st, ra = np.array(stations), np.array(radii)
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
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=500,
        xaxis=dict(title="x (m)", scaleanchor="y", scaleratio=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="y (m)", gridcolor="#e2e8f0"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig_top


def _build_side_view(result, concept, wm, wh, wv):
    """Build 2D side-view figure."""
    fig_side = go.Figure()
    stations = concept.get("fuselage_stations")
    radii = concept.get("fuselage_radii")
    if stations and radii:
        st, ra = np.array(stations), np.array(radii)
        fig_side.add_trace(go.Scatter(
            x=np.concatenate([st, st[::-1]]),
            y=np.concatenate([ra, -ra[::-1]]),
            mode="lines", fill="toself",
            fillcolor="rgba(148,163,184,0.12)",
            line=dict(color=WING_COLORS["fuselage"], width=1.5),
            name="Fuselage",
        ))

    fig_side.add_trace(go.Scatter(
        x=[wm["x"], wm["x"] + wm["chord_root"]], y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["main"], width=4),
        name="Wing Root",
    ))
    fig_side.add_trace(go.Scatter(
        x=[wh["x"], wh["x"] + wh["chord_root"]], y=[0, 0],
        mode="lines", line=dict(color=WING_COLORS["htail"], width=3),
        name="H-Tail Root",
    ))

    vx = wv.get("x", 0)
    vcr, vct = wv["chord_root"], wv["chord_tip"]
    vspan = wv["span"]
    vsweep = np.radians(wv.get("sweep_deg", 0))
    vx_tip = vx + vspan * np.tan(vsweep)
    fig_side.add_trace(go.Scatter(
        x=[vx, vx + vcr, vx_tip + vct, vx_tip, vx],
        y=[0, 0, vspan, vspan, 0],
        mode="lines", fill="toself",
        fillcolor=_rgba(WING_COLORS["vtail"]),
        line=dict(color=WING_COLORS["vtail"], width=2),
        name="V-Tail",
    ))

    fig_side.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=40, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        xaxis=dict(title="x (m)", scaleanchor="y", scaleratio=1, gridcolor="#e2e8f0"),
        yaxis=dict(title="z (m)", gridcolor="#e2e8f0"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig_side
