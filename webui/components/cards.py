"""Reusable UI components."""

from dash import html
from dash_iconify import DashIconify
import dash_bootstrap_components as dbc


def page_header(title: str, subtitle: str = ""):
    children = [html.H2(title)]
    if subtitle:
        children.append(html.P(subtitle))
    return html.Div(children, className="page-header")


def stat_card(label: str, value: str, accent: str = "", icon: str = ""):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.Div(value, className="stat-value"),
                html.Div(label, className="stat-label"),
            ]),
        ]),
        className=f"stat-card {accent}",
    )


def info_card(title: str, children, icon: str = "mdi:information-outline"):
    return dbc.Card([
        dbc.CardHeader([DashIconify(icon=icon, width=16), title]),
        dbc.CardBody(children),
    ])


def empty_state(icon: str, title: str, text: str):
    return html.Div(
        [
            DashIconify(icon=icon, width=48),
            html.H5(title),
            html.P(text),
        ],
        className="empty-state",
    )


def param_input(label: str, id: str, value, type_="number", **kwargs):
    return html.Div(
        [
            dbc.Label(label),
            dbc.Input(id=id, type=type_, value=value, size="sm", **kwargs),
        ],
        className="param-group",
    )


def param_row(*inputs):
    cols = [dbc.Col(inp, md=12 // len(inputs)) for inp in inputs]
    return dbc.Row(cols, className="g-2")
