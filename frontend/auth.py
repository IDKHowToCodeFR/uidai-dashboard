import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

# --- LOGIN PAGE LAYOUT ---
login_page = dbc.Row(
    className="g-0",
    style={"minHeight": "100vh", "overflow": "hidden"},
    children=[
        # --- LEFT PANE (Branding) ---
        dbc.Col(
            xs=0, sm=0, md=5, lg=6,
            className="d-none d-md-flex flex-column align-items-center justify-content-center position-relative",
            style={
                "backgroundColor": "var(--color-bg)",
                "color": "var(--color-text-heading)",
                "padding": "40px"
            },
            children=[
                html.Div(
                    style={"zIndex": 2, "textAlign": "center"},
                    children=[
                        html.Img(src="/assets/aadhaar-logo.png", height="120px", className="mb-2"),
                        html.H3("Unique Identification Authority of India", className="fw-bold mb-2", style={"color": "var(--color-text-heading)"}),
                        html.P("Internal Administrator Dashboard", className="text-muted")
                    ]
                ),

            ]
        ),
        
        # --- RIGHT PANE (Auth Form) ---
        dbc.Col(
            xs=12, sm=12, md=7, lg=6,
            className="d-flex align-items-center justify-content-center",
            style={"backgroundColor": "var(--color-surface)", "padding": "40px"},
            children=[
                html.Div(
                    style={"width": "100%", "maxWidth": "360px"},
                    children=[
                        # Show logo on mobile only
                        html.Div(
                            className="d-md-none text-center mb-5",
                            children=[
                                html.Img(src="/assets/aadhaar-logo.png", height="48px", className="mb-3"),
                                html.H5("UIDAI Dashboard", className="fw-bold", style={"color": "var(--color-text-heading)"})
                            ]
                        ),
                        
                        html.H3("Welcome Back", className="fw-bold mb-1", style={"color": "var(--color-text-heading)"}),
                        html.P("Please sign in to your account", className="text-muted mb-4 small"),

                        html.Label("Username", className="text-muted text-uppercase small mb-1 d-block", style={"fontSize": "10px", "letterSpacing": "1px"}),
                        dbc.Input(
                            id="login-username",
                            autofocus=True,
                            type="text",
                            className="mb-3",
                            style={"borderRadius": "8px", "border": "1px solid var(--color-border)", "padding": "10px 12px"},
                        ),

                        html.Label("Password", className="text-muted text-uppercase small mb-1 d-block", style={"fontSize": "10px", "letterSpacing": "1px"}),
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="login-password",
                                    type="password",
                                    style={"borderRight": "none", "borderRadius": "8px 0 0 8px", "padding": "10px 12px"}
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-eye-slash", id="toggle-password-icon"),
                                    id="toggle-password-btn",
                                    color="light",
                                    style={"border": "1px solid var(--color-border)", "borderLeft": "none", "borderRadius": "0 8px 8px 0", "backgroundColor": "transparent"}
                                ),
                            ],
                            className="mb-4"
                        ),

                        dcc.Loading(
                            type="circle",
                            color="var(--bs-primary)",
                            children=[
                                html.Div(id="login-error", className="text-danger small mb-3", style={"minHeight": "18px"}),
                                dbc.Button(
                                    "Sign In",
                                    id="login-btn",
                                    color="primary",
                                    className="w-100 fw-bold",
                                    style={"borderRadius": "8px", "padding": "12px 0", "border": "none"},
                                )
                            ]
                        ),
                    ]
                )
            ]
        )
    ]
)

# --- CREDENTIALS (now managed by FastAPI backend) ---
import requests
from utils.api import http_session
import json
import os

API_BASE_URL = "http://localhost:8000"

# --- LOGIN CALLBACK ---
@callback(
    Output("auth-state", "data"),
    Output("login-error", "children"),
    Output("login-error", "className"),
    Input("login-btn", "n_clicks"),
    Input("login-username", "n_submit"),
    Input("login-password", "n_submit"),
    State("login-username", "value"),
    State("login-password", "value"),
    State("auth-state", "data")
)
def handle_login(n_clicks, n_submit_u, n_submit_p, username, password, auth_state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
        
    if auth_state and auth_state.get('user'):
        return dash.no_update, "", "text-danger small mb-3"

    error_class = "text-danger small mb-3 shake"

    try:
        response = http_session.post(f"{API_BASE_URL}/login", data={"username": username, "password": password})
        if response.status_code == 200:
            data = response.json()
            return {'user': data['role'], 'token': data['access_token'], 'permissions': data.get('permissions', [])}, "", "text-danger small mb-3"
        else:
            return dash.no_update, "Invalid credentials.", error_class
    except requests.exceptions.RequestException:
        return dash.no_update, "Error connecting to backend API.", error_class


# --- CLEAR LOGIN FORM ON LOGOUT ---
@callback(
    Output("login-username", "value"),
    Output("login-password", "value"),
    Input("auth-state", "data")
)
def clear_login_form(auth_state):
    if not auth_state:
        return "", ""
    return dash.no_update, dash.no_update
dash.clientside_callback(
    """
    function(n_clicks, type) {
        if (!n_clicks) return [dash_clientside.no_update, dash_clientside.no_update];
        if (type === 'password') {
            return ['text', 'bi bi-eye'];
        }
        return ['password', 'bi bi-eye-slash'];
    }
    """,
    Output('login-password', 'type'),
    Output('toggle-password-icon', 'className'),
    Input('toggle-password-btn', 'n_clicks'),
    State('login-password', 'type'),
    prevent_initial_call=True
)
