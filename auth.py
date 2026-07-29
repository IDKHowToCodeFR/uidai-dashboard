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

# --- CREDENTIALS (persisted to JSON) ---
import json
import os

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.json')

DEFAULT_USERS = {
    "admin": {"password": "admin", "user": "Admin"},
    "digitech": {"password": "digitech", "user": "Digitech"},
    "nsb": {"password": "nsb", "user": "NSB"},
}

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    save_users(DEFAULT_USERS)
    return DEFAULT_USERS.copy()

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def add_user(username, password, company_name):
    users = load_users()
    key = username.lower().strip()
    if key in users:
        return False, "Username already exists."
    users[key] = {"password": password, "user": company_name}
    save_users(users)
    return True, f"Company '{company_name}' added."

def remove_user(username):
    users = load_users()
    key = username.lower().strip()
    if key not in users:
        return False, "Company not found."
    if users[key].get("user") == "Admin":
        return False, "Cannot remove an Admin account."
    company_name = users[key].get("user", key)
    del users[key]
    save_users(users)
    return True, f"Company '{company_name}' removed."

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

    users = load_users()
    entry = users.get(username)
    if entry and entry["password"] == password:
        return {'user': entry["user"]}, ""

    return dash.no_update, "Invalid credentials."


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