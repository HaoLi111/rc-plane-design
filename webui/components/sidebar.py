"""Sidebar navigation component."""

from dash import html, dcc
from dash_iconify import DashIconify


def _icon(name: str):
    return DashIconify(icon=name, width=18)


NAV_ITEMS = [
    ("OVERVIEW", None, None, None),
    ("Dashboard", "/", "mdi:view-dashboard-outline", "dashboard"),
    ("DESIGN", None, None, None),
    ("Configuration", "/config", "mdi:cog-outline", "config"),
    ("ANALYSIS", None, None, None),
    ("Aerodynamics", "/aero", "mdi:airplane", "aero"),
    ("Constraints", "/constraints", "mdi:chart-scatter-plot", "constraints"),
    ("Geometry", "/geometry", "mdi:cube-outline", "geometry"),
    ("Stability", "/stability", "mdi:scale-balance", "stability"),
    ("Power & Weight", "/power", "mdi:battery-charging", "power"),
    ("Loads", "/loads", "mdi:chart-bell-curve-cumulative", "loads"),
    ("OUTPUT", None, None, None),
    ("Manufacturing", "/manufacturing", "mdi:printer-3d-nozzle-outline", "manufacturing"),
    ("Export", "/export", "mdi:download-outline", "export"),
]


def sidebar():
    nav_children = []

    for label, href, icon, page_id in NAV_ITEMS:
        if href is None:
            # Section header
            nav_children.append(
                html.Div(label, className="sidebar-section")
            )
        else:
            nav_children.append(
                dcc.Link(
                    [_icon(icon), html.Span(label)],
                    href=href,
                    className="nav-link-sidebar",
                    id=f"nav-{page_id}",
                )
            )

    return html.Nav(
        [
            # ── Brand ──
            html.Div(
                [
                    html.H4(
                        [_icon("mdi:airplane-landing"), " Design Studio"],
                    ),
                    html.Small("RC Aircraft Design"),
                ],
                className="sidebar-brand",
            ),
            # ── Navigation ──
            html.Div(nav_children, className="sidebar-nav"),
            # ── Footer ──
            html.Div(
                [
                    html.Div("v0.1.0 · Python + Dash"),
                    html.Div("Ported from rAviExp (R)", style={"marginTop": "2px"}),
                ],
                className="sidebar-footer",
            ),
        ],
        className="sidebar",
    )
