import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from frontend.shared.api_client import api_get, api_post, get_history_options, download_file

dash.register_page(__name__, path='/admin-settings', name='Global Settings')

# Default SLA Categories matching dashboard.py
SLA_CATEGORIES = [
    {"id": "sl-pct", "label": "Service Level % (Target)"},
    {"id": "ans-rate", "label": "Answer Rate % (Target)"},
    {"id": "no-aban", "label": "No Abandon % (Target)"},
    {"id": "talk-score", "label": "Talk Score (Target)"},
    {"id": "wrap-score", "label": "Wrap Score (Target)"},
    {"id": "hold-score", "label": "Hold Score (Target)"}
]

def layout():
    return dbc.Container([
        html.Div([
            html.H3("Global Settings & SLAs", className="display-xl mb-0"),
            html.P("Configure SLA targets used across the platform for KPI visualizations.", className="text-muted mb-4 mt-2"),
        ]),
        dbc.Card([
            dbc.CardHeader(html.H5("Radar Chart SLA Targets", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label(cat["label"], className="form-label"),
                        dbc.Input(id=f"input-{cat['id']}", type="number", min=0, max=100, step=1)
                    ], width=4, className="mb-3") for cat in SLA_CATEGORIES
                ]),
                html.Hr(),
                dbc.Button("Save Settings", id="btn-save-settings", color="primary", className="mt-2"),
                html.Div(id="settings-msg", className="mt-3")
            ])
        ], className="shadow-sm mb-4")
    ], fluid=True, className="p-4")

@callback(
    [Output(f"input-{cat['id']}", "value") for cat in SLA_CATEGORIES],
    Input("auth-state", "data")
)
def load_settings_ui(auth_state):
    if not auth_state:
        return [dash.no_update] * len(SLA_CATEGORIES)
    token = auth_state.get('token')
    if not token:
        return [dash.no_update] * len(SLA_CATEGORIES)
    try:
        response = api_get("settings", token=token)
        if response.status_code == 200:
            data = response.json()
            targets = data.get("radar_sla_targets", [85, 95, 95, 85, 85, 85])
            if len(targets) == len(SLA_CATEGORIES):
                return targets
    except:
        pass
    return [85, 95, 95, 85, 85, 85]

@callback(
    Output("settings-msg", "children"),
    Input("btn-save-settings", "n_clicks"),
    [State(f"input-{cat['id']}", "value") for cat in SLA_CATEGORIES],
    State("auth-state", "data"),
    prevent_initial_call=True
)
def save_settings_ui(n_clicks, v1, v2, v3, v4, v5, v6, auth_state):
    if not n_clicks:
        return dash.no_update
    if not auth_state:
        return html.Span("Unauthorized", className="text-danger")
    token = auth_state.get("token")
    
    vals = [v1, v2, v3, v4, v5, v6]
    # Check for None
    if None in vals:
        return html.Span("All fields must have a value.", className="text-danger")
        
    settings = {
        "radar_sla_targets": vals
    }
    try:
        response = api_post("settings", token=token, json=settings)
        if response.status_code == 200:
            return html.Span("Settings saved successfully.", className="text-success")
        return html.Span("Failed to save settings.", className="text-danger")
    except Exception as e:
        return html.Span(f"Error: {str(e)}", className="text-danger")
