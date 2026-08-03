import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import requests
from utils.api import http_session
from auth import API_BASE_URL

dash.register_page(__name__, path='/admin-manage', name='Manage Users')

permissions_options = [
    {"label": " View Global Data (All Companies)", "value": "can_view_global"},
    {"label": " View Scoped Data (Company Only)", "value": "can_view_scoped"},
    {"label": " Upload Files", "value": "can_upload_files"}
]

layout = html.Div([
    html.H2("Company & Permissions Management", className="mt-0 mb-3 text-primary fw-bold"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div(html.H5("Add New Company", className="mb-0 fw-bold", style={"color": "var(--color-text-heading)"}), className="card-header"),
                html.Div([
                    dbc.Label("Company Name", className="small text-muted text-uppercase fw-bold"),
                    dbc.Input(id="page-new-company-name", placeholder="e.g. Acme Corp", type="text", className="mb-3", size="sm"),
                    
                    dbc.Label("Username", className="small text-muted text-uppercase fw-bold"),
                    dbc.Input(id="page-new-company-username", placeholder="Login username", type="text", className="mb-3", size="sm"),
                    
                    dbc.Label("Password", className="small text-muted text-uppercase fw-bold"),
                    dbc.Input(id="page-new-company-password", placeholder="Login password", type="password", className="mb-3", size="sm"),
                    
                    dbc.Label("Initial Permissions", className="small text-muted text-uppercase fw-bold"),
                    dbc.Checklist(
                        options=permissions_options,
                        value=["can_view_scoped"],
                        id="page-new-company-perms",
                        switch=True,
                        className="mb-4"
                    ),
                    
                    dbc.Button("Add Company", id="page-btn-add-company", color="primary", size="sm", className="w-100"),
                    html.Div(id="page-add-company-status", className="small mt-2")
                ], className="card-body")
            ], className="custom-card mb-4")
        ], md=5),
        
        dbc.Col([
            html.Div([
                html.Div(html.H5("Manage Existing Company", className="mb-0 fw-bold", style={"color": "var(--color-text-heading)"}), className="card-header"),
                html.Div([
                    dbc.Label("Select Company", className="small text-muted text-uppercase fw-bold"),
                    dcc.Dropdown(id="page-manage-perms-user-select", options=[], placeholder="Choose a company...", className="mb-4"),
                    
                    html.Div(id="manage-perms-container", style={"display": "none"}, children=[
                        dbc.Label("Granted Permissions", className="small text-muted text-uppercase fw-bold"),
                        dbc.Checklist(
                            options=permissions_options,
                            value=[],
                            id="page-manage-perms-switches",
                            switch=True,
                            className="mb-3"
                        ),
                        dbc.Button("Save Permissions", id="page-btn-save-permissions", color="primary", outline=True, size="sm", className="mb-4 w-100"),
                        html.Div(id="page-manage-perms-status", className="small mt-2 mb-4"),
                        
                        html.Hr(),
                        
                        # Danger Zone
                        html.Div([
                            html.H6("Danger Zone", className="text-danger fw-bold mb-3"),
                            html.Div([
                                html.Div([
                                    html.Strong("Deactivate Account", className="text-danger"),
                                    html.P("Revoke all access. Historical logs and uploaded files will be preserved.", className="small text-muted mb-0")
                                ], style={"flex": 1}),
                                dbc.Button("Deactivate", id="page-btn-remove-company", color="danger", outline=True, size="sm", className="align-self-center ms-3")
                            ], className="d-flex border border-danger rounded p-3 mb-2")
                        ], className="mt-2")
                    ])
                ], className="card-body")
            ], className="custom-card mb-4"),
            
            html.Div(id="page-remove-company-status", className="small mt-2")
        ], md=7)
    ])
])

@callback(
    Output("page-manage-perms-user-select", "options"),
    Input("auth-state", "data"),
    Input("page-btn-add-company", "n_clicks"),
    Input("page-btn-remove-company", "n_clicks")
)
def populate_dropdowns(auth_state, add_clicks, remove_clicks):
    if not auth_state:
        return []
    token = auth_state.get('token')
    if not token:
        return []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.get(f"{API_BASE_URL}/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            options = [
                {"label": u["user"], "value": key}
                for key, u in users.items()
                if u.get("user") != "Admin"
            ]
            return options
    except:
        pass
    return []

@callback(
    Output("page-add-company-status", "children"),
    Input("page-btn-add-company", "n_clicks"),
    State("page-new-company-name", "value"),
    State("page-new-company-username", "value"),
    State("page-new-company-password", "value"),
    State("page-new-company-perms", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def add_company(n_clicks, company_name, username, password, perms, auth_state):
    if not n_clicks: return dash.no_update
    if not company_name or not username or not password:
        return html.Span("All fields required.", className="text-danger")
    token = auth_state.get('token') if auth_state else None
    try:
        headers = {"Authorization": f"Bearer {token}"}
        req_data = {"username": username, "password": password, "company_name": company_name, "permissions": perms or []}
        response = http_session.post(f"{API_BASE_URL}/users/add", headers=headers, json=req_data)
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success fw-bold")
        return html.Span(response.json().get("detail", "Error"), className="text-danger")
    except:
        return html.Span("API Error", className="text-danger")

@callback(
    Output("manage-perms-container", "style"),
    Output("page-manage-perms-switches", "value"),
    Output("page-manage-perms-status", "children", allow_duplicate=True),
    Input("page-manage-perms-user-select", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def load_user_perms(username, auth_state):
    if not username:
        return {"display": "none"}, [], ""
    token = auth_state.get('token') if auth_state else None
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.get(f"{API_BASE_URL}/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            if username in users:
                perms = users[username].get("permissions", [])
                return {"display": "block"}, perms, ""
    except:
        pass
    return {"display": "block"}, [], html.Span("Error loading permissions", className="text-danger")

@callback(
    Output("page-remove-company-status", "children"),
    Input("page-btn-remove-company", "n_clicks"),
    State("page-manage-perms-user-select", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def remove_company(n_clicks, username, auth_state):
    if not n_clicks: return dash.no_update
    if not username:
        return html.Span("Select a company first.", className="text-danger")
    token = auth_state.get('token') if auth_state else None
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.post(f"{API_BASE_URL}/users/remove", headers=headers, json={"username": username})
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success fw-bold")
        return html.Span(response.json().get("detail", "Error"), className="text-danger")
    except:
        return html.Span("API Error", className="text-danger")

@callback(
    Output("page-manage-perms-status", "children"),
    Input("page-btn-save-permissions", "n_clicks"),
    State("page-manage-perms-user-select", "value"),
    State("page-manage-perms-switches", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def save_perms(n_clicks, username, switches, auth_state):
    if not n_clicks: return dash.no_update
    if not username:
        return html.Span("Select a company.", className="text-danger")
    token = auth_state.get('token') if auth_state else None
    try:
        headers = {"Authorization": f"Bearer {token}"}
        req_data = {"username": username, "permissions": switches or []}
        response = http_session.post(f"{API_BASE_URL}/users/permissions", headers=headers, json=req_data)
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success fw-bold")
        return html.Span(response.json().get("detail", "Error"), className="text-danger")
    except:
        return html.Span("API Error", className="text-danger")
