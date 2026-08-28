import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
import dash_bootstrap_components as dbc
import requests
import random
import string
from frontend.shared.api_client import api_get, api_post, get_history_options, download_file

dash.register_page(__name__, path='/admin/user_management', name='Manage Users')

layout = html.Div([
    html.Div([
        html.Div([
            html.H3("User Management", className="display-xl mb-0"),
            html.P("Manage system users, passwords, and access controls.", className="text-muted mb-0 mt-2"),
        ]),
        dbc.Button(
            [html.I(className="bi bi-person-plus-fill me-2"), "Add New User"],
            id="admin-btn-add-modal", color="primary"
        ),
    ], className="d-flex justify-content-between align-items-center mb-4"),
    
    html.Div(id="admin-manage-status", style={"display": "none"}), # Hidden trigger for reloads

    # Cards Grid
    html.Div(id="admin-cards-container", className="row g-4 mb-5"),

    # Manage User Modal
    dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(id="offcanvas-username", className="fw-bold mb-0", style={"color": "var(--color-text-heading)"})
            ),
            dbc.ModalBody([
                dbc.Tabs([
                    dbc.Tab(label="Access Control", children=[
                        html.Div([
                            html.Div([
                                dbc.Button("Select All Flags", id="btn-select-all-companies", color="primary", size="sm", outline=True, className="me-2"),
                                dbc.Button("Clear All Flags", id="btn-clear-all-companies", color="secondary", size="sm", outline=True),
                            ], className="d-flex justify-content-end mb-3 mt-1"),
                            
                            dbc.Label("Assigned Companies", className="small text-muted text-uppercase fw-bold mb-2 mt-0"),
                            dbc.Checklist(id="offcanvas-companies", options=[{"label": " Digitech", "value": "Digitech"}, {"label": " NSB", "value": "NSB"}], value=[], switch=True, className="mb-3"),
                            
                            html.Div([
                                dbc.Col([
                                    dbc.Label("Data Modules", className="small text-muted text-uppercase fw-bold"),
                                    dbc.Checklist(
                                        options=[
                                            {"label": " View CCF Data", "value": "can_view_ccf"},
                                            {"label": " View UniMate Data", "value": "can_view_unimate"},
                                            {"label": " View CDR Data", "value": "can_view_cdr"},
                                            {"label": " View APR Report", "value": "can_view_apr"}
                                        ],
                                        value=[], id="offcanvas-perms-data", switch=True, className="mb-3"
                                    ),
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("File Operations", className="small text-muted text-uppercase fw-bold"),
                                    dbc.Checklist(
                                        options = [
                                            {"label": " Download Files", "value": "can_download_files"},
                                        ],
                                        value=[], id="offcanvas-perms-files", switch=True, className="mb-3"
                                    ),
                                ], width=6)
                            ], className="row"),
                            
                            dbc.Button("Save Permissions", id="offcanvas-btn-save", color="primary", size="sm", className="w-100 mb-2 mt-2"),
                            html.Div(id="offcanvas-save-status", className="small mt-2 mb-2"),
                        ], className="p-3 border border-top-0 rounded-bottom")
                    ]),
                    dbc.Tab(label="Security", children=[
                        html.Div([
                            html.H6("Reset Password", className="fw-bold mb-3 mt-2"),
                            dbc.InputGroup([
                                dbc.Input(id="offcanvas-new-password", placeholder="New password...", type="text"),
                                dbc.Button("Generate", id="offcanvas-btn-random-password", color="secondary", outline=True)
                            ], className="mb-2"),
                            dbc.Button("Set Password", id="offcanvas-btn-set-password", color="warning", size="sm", className="w-100 mb-2"),
                            html.Div(id="offcanvas-password-status", className="small mt-2 mb-2"),
                        ], className="p-3 border border-top-0 rounded-bottom")
                    ]),
                    dbc.Tab(label="Danger Zone", children=[
                        html.Div([
                            html.H6("Deactivate Account", className="text-danger fw-bold mb-3 mt-2"),
                            html.P("This will immediately revoke access.", className="small text-muted"),
                            dbc.Button("Deactivate User", id="offcanvas-btn-deactivate", color="danger", outline=True, size="sm", className="w-100"),
                        ], className="p-3 border border-top-0 rounded-bottom")
                    ]),
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id="admin-manage-modal-close", color="secondary", outline=True)
            )
        ],
        id="admin-manage-modal",
        is_open=False,
        centered=True,
        size="lg"
    ),

    # Add Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add New User")),
        dbc.ModalBody([
            dbc.Label("Assigned Companies", className="small text-muted text-uppercase fw-bold"),
            dbc.Checklist(id="page-new-company-name", options=[{"label": " Digitech", "value": "Digitech"}, {"label": " NSB", "value": "NSB"}], value=[], switch=True, className="mb-3"),
            
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
                    {"label": " View CCF Data", "value": "can_view_ccf"},
                    {"label": " View UniMate Data", "value": "can_view_unimate"},
                    {"label": " View CDR Data", "value": "can_view_cdr"},
                    {"label": " View APR Report", "value": "can_view_apr"},
                    {"label": " Download Files", "value": "can_download_files"}
                ],
                value=["can_view_ccf", "can_view_unimate", "can_view_cdr"],
                id="page-new-company-perms",
                switch=True,
                className="mb-3"
            ),
            html.Div(id="page-add-company-status", className="small mt-2")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="page-btn-add-cancel", color="secondary", outline=True),
            dbc.Button("Add User", id="page-btn-add-company", color="primary")
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

def create_card(username, companies, perms, login_count=0, last_login="Never"):
    initials = username[:2].upper()
    
    if last_login is None:
        last_login = "Never"
        
    if last_login != "Never" and "T" in str(last_login):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(last_login)
            last_login = dt.strftime("%b %d, %Y %H:%M")
        except:
            pass

    company_badges = []
    if companies:
        for c in companies:
            company_badges.append(html.Span(c, style={"backgroundColor": "#6366f1", "color": "white"}, className="badge me-1 mb-1 px-2 py-1 rounded-pill shadow-sm"))

    data_module_perms = ["can_view_ccf", "can_view_unimate", "can_view_cdr", "can_view_apr"]
    file_op_perms = ["can_download_files"]
    admin_perms = ["can_manage_users", "can_view_logs", "can_edit_settings"]
    
    badge_labels = {
        "can_view_ccf": "CCF",
        "can_view_unimate": "UniMate",
        "can_view_cdr": "CDR",
        "can_view_apr": "APR",
        "can_download_files": "Download",
        "can_manage_users": "Manage Users",
        "can_view_logs": "Logs",
        "can_edit_settings": "Settings",
    }
    
    data_badges = []
    file_badges = []
    admin_badges = []
    
    seen = set()
    for p in perms:
        if p in seen: continue
        seen.add(p)
        
        if p in data_module_perms:
            data_badges.append(html.Span(badge_labels.get(p, p), style={"backgroundColor": "#10b981", "color": "white"}, className="badge me-1 mb-1 px-2 py-1 rounded-pill shadow-sm"))
        elif p in file_op_perms:
            file_badges.append(html.Span(badge_labels.get(p, p), style={"backgroundColor": "#f59e0b", "color": "white"}, className="badge me-1 mb-1 px-2 py-1 rounded-pill shadow-sm"))
        elif p in admin_perms:
            admin_badges.append(html.Span(badge_labels.get(p, p), style={"backgroundColor": "#f43f5e", "color": "white"}, className="badge me-1 mb-1 px-2 py-1 rounded-pill shadow-sm"))
            
    badge_rows = []
    if company_badges:
        badge_rows.append(html.Div(company_badges, className="mb-1 d-flex flex-wrap justify-content-center"))
    if data_badges:
        badge_rows.append(html.Div(data_badges, className="mb-1 d-flex flex-wrap justify-content-center"))
    if file_badges:
        badge_rows.append(html.Div(file_badges, className="mb-1 d-flex flex-wrap justify-content-center"))
    if admin_badges:
        badge_rows.append(html.Div(admin_badges, className="mb-1 d-flex flex-wrap justify-content-center"))
        
    if not badge_rows:
        badge_rows = [html.Span("No Access", className="small text-muted mb-3 d-block")]

    return dbc.Col([
        html.Div([
            html.Div([
                html.Div(initials, className="initials-bubble mx-auto mb-3"),
                html.H5(username, className="fw-bold mb-3", style={"color": "var(--color-text-heading)", "textTransform": "capitalize"}),
                
                html.Div([
                    html.Span(f"Logins: ", className="text-muted small"),
                    html.Span(f"{login_count}", className="fw-bold small me-3"),
                    html.Span(f"Last: ", className="text-muted small"),
                    html.Span(f"{last_login}", className="fw-bold small"),
                ], className="mb-3"),

                html.Div(badge_rows, className="mb-4"),
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
        response = api_get("users", token=token)
        if response.status_code == 200:
            users = response.json()
            cards = []
            for username, data in users.items():
                if username.lower() == "admin":
                    continue
                companies = data.get("companies", [])
                perms = data.get("permissions", [])
                login_count = data.get("login_count", 0)
                last_login = data.get("last_login", "Never")
                cards.append(create_card(username, companies, perms, login_count, last_login))
            return cards
    except:
        pass
    return []

# Open Modal when Manage is clicked
@callback(
    Output("admin-manage-modal", "is_open"),
    Output("offcanvas-username", "children"),
    Output("offcanvas-companies", "value"),
    Output("offcanvas-companies", "disabled"),
    Output("offcanvas-perms-data", "value"),
    Output("offcanvas-perms-files", "value"),
    Output("offcanvas-btn-save", "disabled"),
    Output("offcanvas-btn-deactivate", "disabled"),
    Output("offcanvas-save-status", "children", allow_duplicate=True),
    Input({"type": "manage-btn", "index": ALL}, "n_clicks"),
    Input("admin-manage-modal-close", "n_clicks"),
    State("auth-state", "data"),
    State("admin-manage-modal", "is_open"),
    prevent_initial_call=True
)
def open_manage_modal(manage_clicks, close_clicks, auth_state, is_open):
    if not ctx.triggered_id:
        return is_open, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    if ctx.triggered_id == "admin-manage-modal-close":
        return False, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    # If all clicks are None (initial load of elements), do not open
    if not any(manage_clicks):
        return is_open, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
    username = ctx.triggered_id["index"]
    token = auth_state.get('token') if auth_state else None
    
    # Fetch specific user permissions
    perms = []
    companies = []
    try:
        response = api_get("users", token=token)
        if response.status_code == 200:
            users = response.json()
            if username in users:
                perms = users[username].get("permissions", [])
                companies = users[username].get("companies", [])
    except:
        pass

    is_admin = username.lower() == "admin"
    if is_admin:
        perms = ["can_download_files", "can_view_ccf", "can_view_unimate", "can_view_cdr", "can_manage_users", "can_view_logs", "can_edit_settings"]

    return True, username, companies, is_admin, perms, perms, is_admin, is_admin, ""

@callback(
    Output("offcanvas-save-status", "children"),
    Output("admin-manage-status", "children", allow_duplicate=True),
    Input("offcanvas-btn-save", "n_clicks"),
    State("offcanvas-username", "children"),
    State("offcanvas-perms-data", "value"),
    State("offcanvas-perms-files", "value"),
    State("offcanvas-companies", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def save_perms(n_clicks, username, data_switches, file_switches, companies, auth_state):
    if not n_clicks: return no_update, no_update
    token = auth_state.get('token') if auth_state else None
    try:
        # Deduplicate all_perms using set
        all_perms = list(set((data_switches or []) + (file_switches or [])))
        req_data = {"username": username, "permissions": all_perms, "companies": companies or []}
        response = api_post("users/permissions", token=token, json=req_data)
        if response.status_code == 200:
            return html.Span("Permissions saved successfully.", className="text-success"), "reload"
        return html.Span("Error saving permissions.", className="text-danger"), no_update
    except:
        return html.Span("Error.", className="text-danger"), no_update

@callback(
    Output("offcanvas-companies", "value", allow_duplicate=True),
    Output("offcanvas-perms-data", "value", allow_duplicate=True),
    Output("offcanvas-perms-files", "value", allow_duplicate=True),
    Input("btn-select-all-companies", "n_clicks"),
    Input("btn-clear-all-companies", "n_clicks"),
    State("offcanvas-companies", "options"),
    State("offcanvas-perms-data", "options"),
    State("offcanvas-perms-files", "options"),
    prevent_initial_call=True
)
def toggle_all_companies(select_all, clear_all, comp_opts, data_opts, file_opts):
    if not ctx.triggered_id:
        return no_update, no_update, no_update
    if ctx.triggered_id == "btn-select-all-companies":
        return [opt["value"] for opt in comp_opts], [opt["value"] for opt in data_opts], [opt["value"] for opt in file_opts]
    return [], [], []

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
        response = api_post("users/reset-password", token=token, json=req_data)
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
    Output("admin-manage-modal", "is_open", allow_duplicate=True),
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
        response = api_post("users/remove", token=token, json={"username": username})
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
    
    companies = company_name if isinstance(company_name, list) else []
    
    token = auth_state.get('token') if auth_state else None
    try:
        req_data = {"username": username, "password": password, "companies": companies, "permissions": perms or []}
        response = api_post("users/add", token=token, json=req_data)
        if response.status_code == 200:
            return "", "reload"
        return html.Span(response.json().get("detail", "Error"), className="text-danger"), no_update
    except:
        return html.Span("API Error", className="text-danger"), no_update
@callback(
    Output("offcanvas-companies", "options"),
    Output("page-new-company-name", "options"),
    Input("admin-manage-status", "children"),
    Input("admin-btn-add-modal", "n_clicks"),
    State("auth-state", "data")
)
def populate_company_dropdowns(status, add_clicks, auth_state):
    from frontend.shared.api_client import get_all_companies
    token = auth_state.get('token') if auth_state else None
    companies = get_all_companies(token)
    opts = [{"label": c, "value": c} for c in companies]
    return opts, opts
