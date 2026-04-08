"""RC Aircraft Design Studio — Dash Web Application.

Launch: python app.py
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, callback, no_update

from components.sidebar import sidebar
from callbacks import register_callbacks

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="RC Aircraft Design Studio",
    update_title="Computing…",
)

server = app.server

# ── Layout ──────────────────────────────────────────────────────────────
app.layout = html.Div([
    # Hidden stores for shared state
    dcc.Store(id="store-design-result", storage_type="session"),
    dcc.Store(id="store-aircraft-config", storage_type="session"),
    dcc.Store(id="store-preset-name", storage_type="session"),
    dcc.Location(id="url", refresh=False),

    sidebar(),
    html.Div(dash.page_container, className="main-content"),
])

register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
