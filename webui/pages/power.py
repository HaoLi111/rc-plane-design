"""Power & Weight page — electric system sizing, weight breakdown."""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from components.cards import page_header, empty_state, stat_card

dash.register_page(__name__, path="/power", title="Power & Weight", name="Power & Weight")


def layout(**kwargs):
    return html.Div([
        page_header("Power & Weight", "Electric power system sizing, weight budget, and endurance estimate"),
        dcc.Loading(html.Div(id="power-content"), type="dot", color="#2563eb"),
    ])


@callback(Output("power-content", "children"), Input("store-design-result", "data"))
def update_power(result):
    if not result:
        return empty_state("mdi:battery-charging", "No Power Data", "Run the design pipeline first.")

    ps = result.get("power_system")
    m_gross = result.get("m_gross_kg", 0)
    W_gross = result.get("W_gross_N", 0)
    shaft_power = result.get("shaft_power_W", 0)
    thrust_req = result.get("thrust_req_N", 0)

    if not ps:
        # No power system (glider)
        return html.Div([
            dbc.Row([
                dbc.Col(stat_card("Gross Mass", f"{m_gross:.3f} kg", "accent-cyan"), md=4),
                dbc.Col(stat_card("Gross Weight", f"{W_gross:.2f} N", ""), md=4),
                dbc.Col(stat_card("Shaft Power", f"{shaft_power:.1f} W", "accent-amber"), md=4),
            ], className="mb-4 g-3"),
            dbc.Alert("No electric power system defined (glider or rubber-powered).", color="info"),
        ])

    motor_p = ps.get("motor_power_W", 0)
    motor_eff = ps.get("motor_efficiency", 0)
    prop_eff = ps.get("prop_efficiency", 0)
    batt_v = ps.get("battery_voltage", 0)
    batt_ah = ps.get("battery_capacity_Ah", 0)
    input_p = ps.get("input_power_W", 0)
    current = ps.get("current_A", 0)
    endurance = ps.get("endurance_min", 0)
    thrust = ps.get("thrust_N", 0)

    # Stats row
    stats = dbc.Row([
        dbc.Col(stat_card("Gross Mass", f"{m_gross:.3f} kg", "accent-cyan"), md=3),
        dbc.Col(stat_card("Motor Power", f"{motor_p:.0f} W", "accent-amber"), md=3),
        dbc.Col(stat_card("Endurance", f"{endurance:.1f} min", "accent-green"), md=3),
        dbc.Col(stat_card("Thrust", f"{thrust:.2f} N", "accent-red"), md=3),
    ], className="mb-4 g-3")

    # Power flow Sankey
    fig_sankey = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color="#e2e8f0", width=1),
            label=["Battery", "ESC/Motor", "Propeller", "Thrust", "Motor Loss", "Prop Loss"],
            color=["#f59e0b", "#2563eb", "#22c55e", "#06b6d4", "#ef4444", "#ef4444"],
        ),
        link=dict(
            source=[0, 1, 1, 2, 2],
            target=[1, 2, 4, 3, 5],
            value=[
                input_p,
                motor_p,
                input_p - motor_p,
                motor_p * prop_eff,
                motor_p * (1 - prop_eff),
            ],
            color=[
                "rgba(245,158,11,0.3)",
                "rgba(37,99,235,0.3)",
                "rgba(239,68,68,0.2)",
                "rgba(34,197,94,0.3)",
                "rgba(239,68,68,0.2)",
            ],
        ),
    ))
    fig_sankey.update_layout(
        title=dict(text="Power Flow", font=dict(size=14)),
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
    )

    # Detail table
    detail = dbc.Table([
        html.Thead(html.Tr([html.Th("Parameter"), html.Th("Value")])),
        html.Tbody([
            html.Tr([html.Td("Motor Output Power"), html.Td(f"{motor_p:.1f} W")]),
            html.Tr([html.Td("Motor Efficiency"), html.Td(f"{motor_eff*100:.0f}%")]),
            html.Tr([html.Td("Propeller Efficiency"), html.Td(f"{prop_eff*100:.0f}%")]),
            html.Tr([html.Td("System Efficiency"), html.Td(f"{motor_eff*prop_eff*100:.1f}%")]),
            html.Tr([html.Td("Battery Voltage"), html.Td(f"{batt_v:.1f} V")]),
            html.Tr([html.Td("Battery Capacity"), html.Td(f"{batt_ah:.1f} Ah ({batt_ah*batt_v:.1f} Wh)")]),
            html.Tr([html.Td("Input Power (from battery)"), html.Td(f"{input_p:.1f} W")]),
            html.Tr([html.Td("Current Draw"), html.Td(f"{current:.1f} A")]),
            html.Tr([html.Td("Required Shaft Power"), html.Td(f"{shaft_power:.1f} W")]),
            html.Tr([html.Td("Required Thrust"), html.Td(f"{thrust_req:.2f} N")]),
            html.Tr([html.Td("Available Thrust"), html.Td(f"{thrust:.2f} N")]),
            html.Tr([html.Td("Endurance"), html.Td(f"{endurance:.1f} min")]),
        ]),
    ], bordered=True, hover=True, size="sm")

    return html.Div([
        stats,
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Power Flow Diagram"),
                dbc.CardBody(dcc.Graph(figure=fig_sankey, config={"displayModeBar": False})),
            ]), lg=7),
            dbc.Col(dbc.Card([
                dbc.CardHeader("System Parameters"),
                dbc.CardBody(detail),
            ]), lg=5),
        ], className="g-3"),
    ])
