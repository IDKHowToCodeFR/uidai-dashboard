import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

# --- LOGIN PAGE LAYOUT ---
login_page = html.Div(
    style={
        "minHeight": "100vh",
        "backgroundColor": "var(--color-bg)",
        "display": "flex",
        "flexDirection": "column",
        "position": "relative",
        "overflow": "hidden",
    },
    children=[
        # --- Top brand bar ---
        html.Div(
            className="d-flex align-items-center px-4",
            style={
                "height": "64px",
                "backgroundColor": "var(--color-surface)",
                "borderBottom": "1px solid var(--color-border)",
                "position": "relative",
                "zIndex": 2,
            },
            children=[
                html.I(className="bi bi-shield-lock-fill me-2", style={"fontSize": "20px", "color": "var(--bs-primary, #4f46e5)"}),
                html.Span("UIDAI", className="fw-bold", style={"fontSize": "16px", "letterSpacing": "0.5px", "color": "var(--color-text-heading)"}),
            ],
        ),

        # --- Centered card ---
        html.Div(
            className="d-flex align-items-center justify-content-center flex-grow-1",
            style={"position": "relative", "zIndex": 2, "padding": "40px 16px"},
            children=[
                html.Div(
                    className="shadow-lg",
                    style={
                        "width": "100%",
                        "maxWidth": "380px",
                        "borderRadius": "14px",
                        "backgroundColor": "var(--color-surface)",
                        "border": "1px solid var(--color-border)",
                        "padding": "36px 32px",
                    },
                    children=[
                        html.H4("Sign In", className="mb-4 fw-bold", style={"color": "var(--color-text-heading)"}),

                        html.Label("Username", className="text-muted text-uppercase small mb-1 d-block", style={"fontSize": "10px", "letterSpacing": "1px"}),
                        dbc.Input(
                            id="login-username",
                            type="text",
                            className="mb-3",
                            style={"borderRadius": "8px", "border": "1px solid var(--color-border)", "padding": "10px 12px"},
                        ),

                        html.Label("Password", className="text-muted text-uppercase small mb-1 d-block", style={"fontSize": "10px", "letterSpacing": "1px"}),
                        dbc.Input(
                            id="login-password",
                            type="password",
                            className="mb-2",
                            style={"borderRadius": "8px", "border": "1px solid var(--color-border)", "padding": "10px 12px"},
                        ),

                        html.Div(id="login-error", className="text-danger small mb-3", style={"minHeight": "18px"}),

                        dbc.Button(
                            "Sign In",
                            id="login-btn",
                            color="primary",
                            className="w-100 fw-bold",
                            style={"borderRadius": "8px", "padding": "10px 0", "border": "none"},
                        ),
                    ],
                )
            ],
        ),

        # --- Decorative skyline footer (pure CSS, theme-colored) ---
        html.Div(
            style={
                "position": "absolute",
                "bottom": 0,
                "left": 0,
                "right": 0,
                "height": "140px",
                "background": "linear-gradient(180deg, transparent 0%, var(--color-border) 100%)",
                "opacity": 0.35,
                "zIndex": 1,
                "clipPath": "polygon(0% 60%, 5% 55%, 10% 65%, 15% 40%, 20% 55%, 28% 45%, 35% 60%, 42% 35%, 50% 50%, 58% 30%, 65% 55%, 72% 40%, 80% 58%, 88% 45%, 95% 60%, 100% 50%, 100% 100%, 0% 100%)",
                "backgroundColor": "var(--color-border)",
            },
        ),
    ],
)

# --- CREDENTIALS (now managed by FastAPI backend) ---
import requests
import json
import os

API_BASE_URL = "http://localhost:8000"

# --- LOGIN CALLBACK ---
@callback(
    Output("auth-state", "data"),
    Output("login-error", "children"),
    Input("login-btn", "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
    State("auth-state", "data")
)
def handle_login(n_clicks, username, password, auth_state):
    if auth_state and auth_state.get('user'):
        return dash.no_update, ""

    if not n_clicks:
        return dash.no_update, ""

    try:
        response = requests.post(f"{API_BASE_URL}/login", data={"username": username, "password": password})
        if response.status_code == 200:
            data = response.json()
            return {'user': data['role'], 'token': data['access_token']}, ""
        else:
            return dash.no_update, "Invalid credentials."
    except requests.exceptions.RequestException:
        return dash.no_update, "Error connecting to backend API."


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