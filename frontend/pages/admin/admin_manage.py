import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
import dash_bootstrap_components as dbc
import requests
import random
import string
from frontend.shared.api_client import api_client

dash.register_page(__name__, path='/admin-manage', name='Manage Users')

layout = html.Div([
    html.Div([
        html.Div([
            html.H3("Company & Permissions", className="display-xl mb-0"),
            html.P("Manage system users, passwords, and access controls.", className="text-muted mb-0 mt-2"),
        ]),
        dbc.Button(
            [html.I(className="bi bi-person-plus-fill me-2"), "Add Company"],
            id="admin-btn-add-modal", color="primary"
        ),
    ], className="d-flex justify-content-between align-items-center mb-4"),
    
    html.Div(id="admin-manage-status", style={"display": "none"}), # Hidden trigger for reloads

    # Cards Grid
    html.Div(id="admin-cards-container", className="row g-4 mb-5"),

    # Offcanvas Side-Panel
    dbc.Offcanvas(
        [
            html.H4(id="offcanvas-username", className="fw-bold mb-4", style={"color": "var(--color-text-heading)"}),
            dbc.Label("Granted Permissions", className="small text-muted text-uppercase fw-bold"),
            dbc.Checklist(
                options=[
                    {"label": " View Global Data", "value": "can_view_global"},
                    {"label": " View Scoped Data", "value": "can_view_scoped"},
                    {"label": " Upload Files", "value": "can_upload_files"},
                    {"label": " Download Files", "value": "can_download_files"}
                ],
                value=[],
                id="offcanvas-perms-switches",
                switch=True,
                className="mb-4"
            ),
            dbc.Button("Save Permissions", id="offcanvas-btn-save", color="primary", size="sm", className="w-100 mb-2"),
            html.Div(id="offcanvas-save-status", className="small mt-2 mb-4"),
            
            html.Hr(),
            html.H6("Reset Password", className="fw-bold mb-3"),
            dbc.InputGroup([
                dbc.Input(id="offcanvas-new-password", placeholder="New password...", type="text"),
                dbc.Button("Generate", id="offcanvas-btn-random-password", color="secondary", outline=True)
            ], className="mb-2"),
            dbc.Button("Set Password", id="offcanvas-btn-set-password", color="warning", size="sm", className="w-100 mb-2"),
            html.Div(id="offcanvas-password-status", className="small mt-2 mb-4"),

            html.Hr(),
            html.H6("Danger Zone", className="text-danger fw-bold mb-3"),
            dbc.Button("Deactivate User", id="offcanvas-btn-deactivate", color="danger", outline=True, size="sm", className="w-100"),
        ],
        id="admin-offcanvas",
        is_open=False,
        placement="end",
        title="Manage User"
    ),

    # Add Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add New Company")),
        dbc.ModalBody([
            dbc.Label("Company Name", className="small text-muted text-uppercase fw-bold"),
            dbc.Input(id="page-new-company-name", placeholder="e.g. Acme Corp", type="text", className="mb-3"),
            
            dbc.Label("Username", className="small text-muted text-uppercase fw-bold"),
            dbc.Input(id="page-new-company-username", placeholder="Login username", type="text", className="mb-3"),
            
            dbc.Label("Password", className="small text-muted text-uppercase fw-bold"),
            dbc.InputGroup([
                dbc.Input(id="page-new-company-password", placeholder="Login password", type="text"),
                dbc.Button("Generate", id="page-btn-random-password", color="secondary", outline=True)
            ], className="mb-3"),
            
            dbc.Label("Initial Permissions", className="small text-muted text-uppercase fw-bold"),
            dbc.Checklist(
                options=[
                    {"label": " View Global Data", "value": "can_view_global"},
                    {"label": " View Scoped Data", "value": "can_view_scoped"},
                    {"label": " Upload Files", "value": "can_upload_files"},
                    {"label": " Download Files", "value": "can_download_files"}
                ],
                value=["can_view_scoped"],
                id="page-new-company-perms",
                switch=True,
                className="mb-3"
            ),
            html.Div(id="page-add-company-status", className="small mt-2")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="page-btn-add-cancel", color="secondary", outline=True),
            dbc.Button("Add Company", id="page-btn-add-company", color="primary")
        ])
    ], id="admin-add-modal", is_open=False),

    # Safe Deletion Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirm Deactivation", className="text-danger")),
        dbc.ModalBody([
            html.P("This action is destructive and will prevent the user from logging in or accessing the API."),
            html.P(["Please type the username ", html.Strong(id="deactivate-target-username"), " to confirm."]),
            dbc.Input(id="deactivate-confirm-input", placeholder="Type username here...", type="text", className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="modal-btn-deactivate-cancel", color="secondary", outline=True),
            dbc.Button("Deactivate User", id="modal-btn-deactivate-confirm", color="danger", disabled=True)
        ])
    ], id="admin-deactivate-modal", is_open=False)
])

def create_card(username, company_name, perms, login_count=0, last_login="Never"):
    initials = company_name[:2].upper() if company_name else username[:2].upper()
    total_perms = 4
    granted_perms = len([p for p in perms if p in ["can_view_global", "can_view_scoped", "can_upload_files", "can_download_files"]])
    percentage = int((granted_perms / total_perms) * 100)
    
    if last_login is None:
        last_login = "Never"
        
    if last_login != "Never" and "T" in str(last_login):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(last_login)
            last_login = dt.strftime("%b %d, %Y %H:%M")
        except:
            pass

    return dbc.Col([
        html.Div([
            html.Div([
                html.Div(initials, className="initials-bubble mx-auto mb-3"),
                html.H5(company_name, className="fw-bold mb-1", style={"color": "var(--color-text-heading)"}),
                html.P(f"User: {username} | Access: {percentage}%", className="small text-muted mb-2 fw-bold"),
                
                html.Div([
                    html.Span(f"Logins: ", className="text-muted small"),
                    html.Span(f"{login_count}", className="fw-bold small me-3"),
                    html.Span(f"Last: ", className="text-muted small"),
                    html.Span(f"{last_login}", className="fw-bold small"),
                ], className="mb-3"),

                dbc.Progress(value=percentage, color="primary", className="mb-4", style={"height": "6px", "borderRadius": "4px"}),
                dbc.Button("Manage", id={"type": "manage-btn", "index": username}, color="primary", outline=True, size="sm", className="w-100 fw-bold")
            ], className="card-body text-center p-4")
        ], className="custom-card shadow-sm h-100 hover-lift")
    ], xs=12, sm=6, md=4, lg=3)


@callback(
    Output("admin-cards-container", "children"),
    Input("auth-state", "data"),
    Input("admin-manage-status", "children"),
    prevent_initial_call=False
)
def load_cards(auth_state, status):
    if not auth_state:
        return []
    token = auth_state.get('token')
    if not token:
        return []
    try:
        response = api_client.get_users(token)
        if response.status_code == 200:
            users = response.json()
            cards = []
            for username, data in users.items():
                if data.get("user") == "Admin":
                    continue
                perms = data.get("permissions", [])
                company_name = data.get("user", username)
                login_count = data.get("login_count", 0)
                last_login = data.get("last_login", "Never")
                cards.append(create_card(username, company_name, perms, login_count, last_login))
            return cards
    except:
        pass
    return []

# Open Offcanvas when Manage is clicked
@callback(
    Output("admin-offcanvas", "is_open"),
    Output("offcanvas-username", "children"),
    Output("offcanvas-perms-switches", "value"),
    Output("offcanvas-save-status", "children", allow_duplicate=True),
    Input({"type": "manage-btn", "index": ALL}, "n_clicks"),
    State("auth-state", "data"),
    State("admin-offcanvas", "is_open"),
    prevent_initial_call=True
)
def open_offcanvas(manage_clicks, auth_state, is_open):
    if not ctx.triggered_id:
        return is_open, no_update, no_update, no_update
    
    # If all clicks are None (initial load of elements), do not open
    if not any(manage_clicks):
        return is_open, no_update, no_update, no_update
        
    username = ctx.triggered_id["index"]
    token = auth_state.get('token') if auth_state else None
    
    # Fetch specific user permissions
    perms = []
    try:
        response = api_client.get_users(token)
        if response.status_code == 200:
            users = response.json()
            if username in users:
                perms = users[username].get("permissions", [])
    except:
        pass

    return True, username, perms, ""

@callback(
    Output("offcanvas-save-status", "children"),
    Output("admin-manage-status", "children", allow_duplicate=True),
    Input("offcanvas-btn-save", "n_clicks"),
    State("offcanvas-username", "children"),
    State("offcanvas-perms-switches", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def save_perms(n_clicks, username, switches, auth_state):
    if not n_clicks: return no_update, no_update
    token = auth_state.get('token') if auth_state else None
    try:
        req_data = {"username": username, "permissions": switches or []}
        response = api_client.update_permissions(token, req_data)
        if response.status_code == 200:
            return html.Span("Permissions saved successfully.", className="text-success"), "reload"
        return html.Span("Error saving permissions.", className="text-danger"), no_update
    except:
        return html.Span("Error.", className="text-danger"), no_update

def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@callback(
    Output("page-new-company-password", "value"),
    Input("page-btn-random-password", "n_clicks"),
    prevent_initial_call=True
)
def generate_add_user_password(n_clicks):
    if n_clicks:
        return generate_random_password()
    return no_update

@callback(
    Output("offcanvas-new-password", "value"),
    Output("offcanvas-password-status", "children", allow_duplicate=True),
    Input("offcanvas-btn-random-password", "n_clicks"),
    prevent_initial_call=True
)
def generate_reset_password(n_clicks):
    if n_clicks:
        return generate_random_password(), ""
    return no_update, no_update

@callback(
    Output("offcanvas-password-status", "children"),
    Input("offcanvas-btn-set-password", "n_clicks"),
    State("offcanvas-username", "children"),
    State("offcanvas-new-password", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def reset_user_password(n_clicks, username, new_password, auth_state):
    if not n_clicks: return no_update
    if not new_password or len(new_password.strip()) < 4:
        return html.Span("Password must be at least 4 characters.", className="text-danger")
        
    token = auth_state.get('token') if auth_state else None
    try:
        req_data = {"username": username, "new_password": new_password.strip()}
        response = api_client.reset_password(token, req_data)
        if response.status_code == 200:
            return html.Span("Password updated successfully.", className="text-success")
        return html.Span("Error updating password.", className="text-danger")
    except:
        return html.Span("API Error.", className="text-danger")

@callback(
    Output("admin-deactivate-modal", "is_open"),
    Output("deactivate-target-username", "children"),
    Input("offcanvas-btn-deactivate", "n_clicks"),
    Input("modal-btn-deactivate-cancel", "n_clicks"),
    State("offcanvas-username", "children"),
    State("admin-deactivate-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_deactivate_modal(n_open, n_close, username, is_open):
    if ctx.triggered_id == "offcanvas-btn-deactivate":
        return True, username
    return False, no_update

@callback(
    Output("modal-btn-deactivate-confirm", "disabled"),
    Input("deactivate-confirm-input", "value"),
    State("deactivate-target-username", "children"),
    prevent_initial_call=True
)
def validate_deactivate(typed_val, target_val):
    if typed_val and target_val and typed_val.strip() == target_val.strip():
        return False
    return True

@callback(
    Output("admin-deactivate-modal", "is_open", allow_duplicate=True),
    Output("admin-offcanvas", "is_open", allow_duplicate=True),
    Output("admin-manage-status", "children", allow_duplicate=True),
    Input("modal-btn-deactivate-confirm", "n_clicks"),
    State("deactivate-target-username", "children"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def deactivate_user(n_clicks, username, auth_state):
    if not n_clicks: return no_update, no_update, no_update
    token = auth_state.get('token') if auth_state else None
    try:
        response = api_client.remove_user(token, username)
        if response.status_code == 200:
            return False, False, "reload"
    except:
        pass
    return no_update, no_update, no_update

@callback(
    Output("admin-add-modal", "is_open"),
    Input("admin-btn-add-modal", "n_clicks"),
    Input("page-btn-add-cancel", "n_clicks"),
    Input("page-btn-add-company", "n_clicks"),
    State("admin-add-modal", "is_open"),
    State("page-new-company-name", "value"),
    State("page-new-company-username", "value"),
    State("page-new-company-password", "value"),
)
def toggle_modal(btn1, btn2, btn3, is_open, name, user, pwd):
    ctx_id = ctx.triggered_id
    if not ctx_id:
        return is_open
    if ctx_id == "page-btn-add-company":
        if not name or not user or not pwd:
            return True
        return False
    return not is_open

@callback(
    Output("page-add-company-status", "children"),
    Output("admin-manage-status", "children", allow_duplicate=True),
    Input("page-btn-add-company", "n_clicks"),
    State("page-new-company-name", "value"),
    State("page-new-company-username", "value"),
    State("page-new-company-password", "value"),
    State("page-new-company-perms", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def add_company(n_clicks, company_name, username, password, perms, auth_state):
    if not n_clicks: return no_update, no_update
    if not company_name or not username or not password:
        return html.Span("All fields required.", className="text-danger"), no_update
    token = auth_state.get('token') if auth_state else None
    try:
        req_data = {"username": username, "password": password, "company_name": company_name, "permissions": perms or []}
        response = api_client.add_user(token, req_data)
        if response.status_code == 200:
            return "", "reload"
        return html.Span(response.json().get("detail", "Error"), className="text-danger"), no_update
    except:
        return html.Span("API Error", className="text-danger"), no_update
