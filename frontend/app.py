import os
import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import requests
from utils.api import http_session
from datetime import datetime, timedelta
import numpy as np
from auth import login_page, handle_login, API_BASE_URL  # noqa: F401

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'),
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
    ],
    suppress_callback_exceptions=True
)
app.title = "UIDAI analytics Dashboard"

def get_history_options(token, user_role=None, permissions=None):
    if permissions is None: permissions = []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.get(f"{API_BASE_URL}/history", headers=headers)
        if response.status_code == 200:
            file_times = response.json()
        else:
            return []
    except Exception:
        return []

    now = datetime.now()
    today = now.date()
    options = []
    current_group = None

    for item in file_times:
        mtime = datetime.fromisoformat(item['time'])
        date = mtime.date()
        age_days = (today - date).days

        if age_days == 0:
            group_name = "Today"
        elif age_days == 1:
            group_name = "Yesterday"
        elif age_days <= 30:
            group_name = mtime.strftime("%b %d")
        elif age_days <= 90:
            group_name = mtime.strftime("%B")
        else:
            group_name = "Earlier"

        if group_name != current_group:
            options.append({
                'label': html.Div(group_name, className="history-group-header small text-muted fw-bold mt-3 mb-1 text-uppercase", style={'fontSize': '10px', 'letterSpacing': '1px'}),
                'value': f'HEADER_{group_name}',
                'disabled': True
            })
            current_group = group_name

        label = html.Span(item['name'], className="text-truncate ms-2")
        options.append({'label': label, 'value': item['name']})
        
    if user_role == 'Admin' or 'can_view_global' in permissions:
        # Prepend the aggregate option
        options.insert(0, {
            'label': html.Span("All Companies (Aggregated)", className="text-truncate ms-2 text-primary fw-bold"),
            'value': 'aggregate'
        })

    return options

def upload_file_to_api(contents, filename, token):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": (filename, decoded)}
        
        response = http_session.post(f"{API_BASE_URL}/upload", headers=headers, files=files)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Upload error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception during upload: {e}")
        return None

style_dropdown_toggle = {
    "backgroundColor": "var(--color-surface)",
    "color": "var(--color-text-heading)",
    "border": "1px solid var(--color-border)",
    "borderRadius": "8px",
    "padding": "8px 16px",
    "fontFamily": "'Inter', sans-serif",
    "fontSize": "14px",
    "fontWeight": "600",
    "boxShadow": "0 2px 4px -1px rgba(0,0,0,0.05)",
    "transition": "all 0.2s ease"
}

# --- FILTER DRAWER (Right Side) ---
filter_drawer = dbc.Offcanvas(
    html.Div([
        html.H6("TIME RANGE", className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date_placeholder_text="Start",
            end_date_placeholder_text="End",
            display_format='YYYY-MM-DD',
            className="mb-4 w-100"
        ),

        html.H6("COMPANY", className="text-muted text-uppercase mb-2 mt-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.Dropdown(
            id="company-filter",
            options=[],
            value=[],
            multi=True,
            placeholder="Search Companies...",
            className="mb-4",
            disabled=False
        ),

        html.H6("LANGUAGE", className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.Dropdown(
            id="language-filter",
            options=[],
            value=[],
            multi=True,
            placeholder="Search Languages...",
            className="mb-4"
        ),
    ]),
    id="filter-drawer",
    title="Dashboard Filters",
    is_open=False,
    placement="end",
    className="offcanvas border-0 shadow-lg"
)

def get_topbar(user_role):
    # Base topbar elements
    left_elements = [
        html.Img(src="/assets/aadhaar-logo.png", style={"height": "40px", "marginRight": "15px"}),
        html.H5("Unique Identification Authority of India", className="display-lg mb-0", style={"display": "inline-block", "fontWeight": "700"}),
    ]
    
    right_elements = [
        html.Button(
            html.I(className="bi bi-funnel-fill"),
            id="btn-filters",
            n_clicks=0,
            className="btn btn-light me-3 body-strong rounded-circle shadow-sm",
            style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
        ),
        html.Button(
            html.I(className="bi bi-box-arrow-right"),
            id="btn-logout",
            n_clicks=0,
            className="btn btn-primary me-3 body-strong rounded-circle shadow-sm",
            style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center"}
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Log Out")),
                dbc.ModalBody("Are you sure you want to log out?"),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="btn-logout-cancel", color="secondary", outline=True, size="sm", className="me-2"),
                        dbc.Button("Log Out", id="btn-logout-confirm", color="primary", size="sm"),
                    ]
                ),
            ],
            id="logout-confirm-modal",
            is_open=False,
            centered=True,
            backdrop=True,
        ),
        html.Button(
            html.I(className="bi bi-list fs-4"),
            id="btn-sidebar-toggle",
            n_clicks=0,
            className="btn btn-light body-strong rounded-circle shadow-sm",
            style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
        )
    ]
    
    return html.Div(
        [
            html.Div(left_elements, style={"display": "flex", "alignItems": "center"}),
            html.Div(right_elements, style={"display": "flex", "alignItems": "center"})
        ],
        className="topbar custom-card px-4",
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "right": 0,
            "height": "80px",
            "zIndex": 1000,
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between"
        }
    )

def get_sidebar(user_role, token, permissions):
    if user_role == 'Admin':
        sidebar_content = html.Div([
            html.H6("ADMINISTRATOR", className="sidebar-section-title text-muted text-uppercase mb-3", style={"fontSize": "11px", "letterSpacing": "1px"}),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="bi bi-people-fill me-3"), html.Span("Manage Users", className="nav-link-text")],
                        href="/admin-manage",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-card-list me-3"), html.Span("System Logs", className="nav-link-text")],
                        href="/admin-logs",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-folder-fill me-3"), html.Span("File Repository", className="nav-link-text")],
                        href="/admin-files",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                ],
                vertical=True,
                pills=True,
                className="custom-sidebar-nav mb-5"
            )
        ], className="sidebar-content-wrapper")
        return dbc.Offcanvas(
            sidebar_content,
            id="sidebar",
            title="Admin Console",
            placement="end",
            is_open=False,
            className="premium-offcanvas sidebar-container border-0 shadow-lg"
        )
        
    opts = get_history_options(token, user_role, permissions)
    val = None
    
    if (user_role == 'Admin' or (permissions and 'can_view_global' in permissions)) and any(opt.get('value') == 'aggregate' for opt in opts):
        val = 'aggregate'
    else:
        for opt in opts:
            if not opt['value'].startswith('HEADER_'):
                val = opt['value']
                break
            
    can_upload = 'can_upload' in permissions

    sidebar_content = html.Div([
        html.H6("MAIN", className="sidebar-section-title text-muted text-uppercase mb-3", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")],
                    href="/",
                    active="exact",
                    className="body-strong mb-2 d-flex align-items-center"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-calendar-range me-3"), html.Span("Date Comparison", className="nav-link-text")],
                    href="/date-comparison",
                    active="exact",
                    className="body-strong mb-2 d-flex align-items-center"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-clock-history me-3"), html.Span("Hourly Insights", className="nav-link-text")],
                    href="/hourly",
                    active="exact",
                    className="body-strong mb-2 d-flex align-items-center"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")],
                    href="/raw-data",
                    active="exact",
                    className="body-strong mb-2 d-flex align-items-center"
                ),
            ],
            vertical=True,
            pills=True,
            className="custom-sidebar-nav mb-5"
        ),

        html.Hr(style={"borderColor": "#e2e8f0"}),

        html.Div([
            html.H6("DATA", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
            html.Div([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        html.I(className="bi bi-cloud-arrow-up fs-4 mb-2 d-block"),
                        html.Span(['Drag and Drop or ', html.A('Select Files', className="text-primary text-decoration-none")], className="nav-link-text")
                    ]),
                    multiple=False,
                    className="upload-box mb-4"
                )
            ]),
            html.Div(id='upload-status', className="nav-link-text text-muted small mt-2"),
        ], style={"display": "block"} if can_upload else {"display": "none"}),

        html.H6("HISTORY", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
        html.Div(
            dbc.RadioItems(
                id="file-history",
                options=opts,
                value=val,
                className="mb-4 history-radio-group"
            )
        )
    ], className="sidebar-content-wrapper")

    return dbc.Offcanvas(
        sidebar_content,
        id="sidebar",
        title="Main Menu",
        placement="start",
        is_open=False,
        className="premium-offcanvas sidebar-container"
    )

content = html.Div(
    dash.page_container,
    id="main-content",
    className="main-content"
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=True),
        dcc.Store(id="auth-state", storage_type="session"),
        dcc.Store(id="company-list-version", data=0),
        dcc.Store(id="data-store", storage_type="memory"),
        dcc.Download(id="download-dataframe-csv"),
        html.Div(id="app-container")
    ]
)

@callback(
    Output("filter-drawer", "is_open"),
    Input("btn-filters", "n_clicks"),
    State("filter-drawer", "is_open"),
)
def toggle_filter_drawer(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output("sidebar", "is_open"),
    Input("btn-sidebar-toggle", "n_clicks"),
    State("sidebar", "is_open"),
)
def toggle_left_sidebar(n, is_open):
    if n:
        return not is_open
    return is_open

# --- ROUTING / AUTH RENDERING ---
@callback(
    Output("app-container", "children"),
    Output("data-store", "data", allow_duplicate=True),
    Input("auth-state", "data"),
    prevent_initial_call=True
)
def render_page(auth_state):
    if auth_state and auth_state.get('user') and auth_state.get('token'):
        user_role = auth_state.get('user')
        token = auth_state.get('token')
        permissions = auth_state.get('permissions', [])
        sidebar = get_sidebar(user_role, token, permissions)
        
        # Determine initial data based on history
        opts = get_history_options(token, user_role, permissions)
        val = None
        data = []
        
        if (user_role == 'Admin' or (permissions and 'can_view_global' in permissions)) and any(opt.get('value') == 'aggregate' for opt in opts):
            val = 'aggregate'
        else:
            for opt in opts:
                if not opt['value'].startswith('HEADER_'):
                    val = opt['value']
                    break
                
        if val:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = http_session.get(f"{API_BASE_URL}/data/{val}", headers=headers)
                if response.status_code == 200:
                    data = response.json()
            except Exception:
                pass

        topbar = get_topbar(user_role)
        
        # Everyone gets the same layout structure now! 
        # The sidebar on the right handles everything (nav, filters, logout).
        return html.Div([
            topbar,
            sidebar,
            filter_drawer,
            content
        ], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"}), data
        
    return login_page, []

@callback(
    Output("url", "pathname"),
    Input("auth-state", "data"),
    Input("url", "pathname")
)
def guard_routes(auth_state, pathname):
    if not auth_state or not pathname:
        return dash.no_update
        
    user_role = auth_state.get('user')
    if user_role == 'Admin':
        if pathname in ['/', '/date-comparison', '/hourly', '/raw-data']:
            return '/admin-manage'
    elif user_role:
        if pathname.startswith('/admin'):
            return '/'
            
    return dash.no_update

# --- ADMIN: OPEN ADD MODAL ---
@callback(
    Output("add-company-modal", "is_open"),
    Input("btn-open-add-company", "n_clicks"),
    State("add-company-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_add_company_modal(n, is_open):
    if n:
        return not is_open
    return is_open

# --- ADMIN: ADD COMPANY ---
@callback(
    Output("add-company-status", "children"),
    Output("new-company-name", "value"),
    Output("new-company-username", "value"),
    Output("new-company-password", "value"),
    Output("company-list-version", "data"),
    Output("add-company-modal", "is_open", allow_duplicate=True),
    Input("btn-add-company", "n_clicks"),
    State("new-company-name", "value"),
    State("new-company-username", "value"),
    State("new-company-password", "value"),
    State("company-list-version", "data"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def handle_add_company(n_clicks, company_name, username, password, version, auth_state):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not company_name or not username or not password:
        return html.Span("All fields required.", className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True
    
    token = auth_state.get('token') if auth_state else None
    if not token:
        return html.Span("Unauthorized.", className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True
        
    try:
        headers = {"Authorization": f"Bearer {token}"}
        req_data = {"username": username, "password": password, "company_name": company_name}
        response = http_session.post(f"{API_BASE_URL}/users/add", headers=headers, json=req_data)
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success"), "", "", "", (version or 0) + 1, False
        else:
            return html.Span(response.json().get("detail", "Error"), className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True
    except Exception as e:
        return html.Span("API Error", className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True

# --- ADMIN: OPEN REMOVE MODAL ---
@callback(
    Output("remove-company-modal", "is_open"),
    Input("btn-open-remove-company", "n_clicks"),
    State("remove-company-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_remove_company_modal(n, is_open):
    if n:
        return not is_open
    return is_open

# --- ADMIN: POPULATE REMOVE-COMPANY DROPDOWN ---
@callback(
    Output("remove-company-select", "options"),
    Input("remove-company-modal", "is_open"),
    Input("company-list-version", "data"),
    State("auth-state", "data")
)
def populate_remove_company_options(is_open, _version, auth_state):
    if not is_open or not auth_state:
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

# --- ADMIN: REMOVE COMPANY ---
@callback(
    Output("remove-company-status", "children"),
    Output("remove-company-select", "value"),
    Output("company-list-version", "data", allow_duplicate=True),
    Output("remove-company-modal", "is_open", allow_duplicate=True),
    Input("btn-remove-company", "n_clicks"),
    State("remove-company-select", "value"),
    State("company-list-version", "data"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def handle_remove_company(n_clicks, username, version, auth_state):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not username:
        return html.Span("Select a company first.", className="text-danger"), dash.no_update, dash.no_update, True
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return html.Span("Unauthorized.", className="text-danger"), dash.no_update, dash.no_update, True
        
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.post(f"{API_BASE_URL}/users/remove", headers=headers, json={"username": username})
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success"), None, (version or 0) + 1, False
        else:
            return html.Span(response.json().get("detail", "Error"), className="text-danger"), dash.no_update, dash.no_update, True
    except:
        return html.Span("API Error", className="text-danger"), dash.no_update, dash.no_update, True

# --- ADMIN: MANAGE PERMISSIONS MODAL ---
@callback(
    Output("manage-perms-modal", "is_open"),
    Input("btn-open-manage-permissions", "n_clicks"),
    State("manage-perms-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_manage_perms_modal(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output("manage-perms-user-select", "options"),
    Input("manage-perms-modal", "is_open"),
    State("auth-state", "data")
)
def populate_manage_perms_options(is_open, auth_state):
    if not is_open or not auth_state:
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
    Output("manage-perms-switches", "value"),
    Input("manage-perms-user-select", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def update_switches_for_user(username, auth_state):
    if not username or not auth_state:
        return []
    token = auth_state.get('token')
    if not token:
        return []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = http_session.get(f"{API_BASE_URL}/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            user_data = users.get(username, {})
            return user_data.get("permissions", [])
    except:
        pass
    return []

@callback(
    Output("manage-perms-status", "children"),
    Output("manage-perms-modal", "is_open", allow_duplicate=True),
    Input("btn-save-permissions", "n_clicks"),
    State("manage-perms-user-select", "value"),
    State("manage-perms-switches", "value"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def handle_save_permissions(n_clicks, username, switches, auth_state):
    if not n_clicks:
        return dash.no_update, dash.no_update
    if not username:
        return html.Span("Select a user first.", className="text-danger"), True
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return html.Span("Unauthorized.", className="text-danger"), True
        
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"username": username, "permissions": switches}
        response = http_session.post(f"{API_BASE_URL}/users/permissions", headers=headers, json=payload)
        if response.status_code == 200:
            return html.Span(response.json().get("message"), className="text-success"), False
        else:
            return html.Span(response.json().get("detail", "Error"), className="text-danger"), True
    except:
        return html.Span("API Error", className="text-danger"), True

# --- LOGOUT: ASK CONFIRMATION ---
@callback(
    Output("logout-confirm-modal", "is_open"),
    Input("btn-logout", "n_clicks"),
    Input("btn-logout-cancel", "n_clicks"),
    State("logout-confirm-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_logout_modal(open_clicks, cancel_clicks, is_open):
    if ctx.triggered_id in ("btn-logout", "btn-logout-cancel"):
        return not is_open
    return is_open

# --- LOGOUT: CONFIRMED ---
@callback(
    Output("auth-state", "data", allow_duplicate=True),
    Output("logout-confirm-modal", "is_open", allow_duplicate=True),
    Input("btn-logout-confirm", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks:
        return None, False
    return dash.no_update, dash.no_update

@callback(
    Output('company-filter', 'options'),
    Output('company-filter', 'value'),
    Output('company-filter', 'disabled'),
    Output('language-filter', 'options'),
    Output('language-filter', 'value'),
    Output('date-picker-range', 'min_date_allowed'),
    Output('date-picker-range', 'max_date_allowed'),
    Output('date-picker-range', 'start_date'),
    Output('date-picker-range', 'end_date'),
    Input('data-store', 'data'),
    Input('auth-state', 'data'),
    Input('company-list-version', 'data')
)
def sync_filters(data, auth_state, _version):
    if not data:
        return dash.no_update

    df = pd.DataFrame(data)

    c_options, c_values = [], []
    l_options, l_values = [], []
    c_disabled = False
    user_role = auth_state.get('user') if auth_state else None
    token = auth_state.get('token') if auth_state else None

    if 'Company' in df.columns:
        companies = df['Company'].dropna().unique().tolist()
        if user_role == 'Admin' and token:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = http_session.get(f"{API_BASE_URL}/users", headers=headers)
                if response.status_code == 200:
                    registered = [u['user'] for u in response.json().values() if u['user'] != 'Admin']
                    all_companies = sorted(set(companies + registered))
                else:
                    all_companies = sorted(set(companies))
            except:
                all_companies = sorted(set(companies))
            
            c_options = [{'label': c, 'value': c} for c in all_companies]
            c_values = companies
        else:
            c_options = [{'label': user_role, 'value': user_role}]
            c_values = [user_role]
            c_disabled = True

    if 'Language' in df.columns:
        langs = df['Language'].dropna().unique().tolist()
        l_options = [{'label': l, 'value': l} for l in langs]
        l_values = langs

    min_date = max_date = start_date = end_date = None
    
    date_candidates = ['Timestamp', 'Call Timestamp', 'Date', 'Call Start Time']
    df['ParsedDate'] = pd.NaT
    for col in date_candidates:
        if col in df.columns:
            df['ParsedDate'] = df['ParsedDate'].fillna(pd.to_datetime(df[col], errors='coerce'))
            
    if not df['ParsedDate'].isna().all():
        min_date = df['ParsedDate'].min().date()
        max_date = df['ParsedDate'].max().date()
        start_date = min_date
        end_date = max_date

    return c_options, c_values, c_disabled, l_options, l_values, min_date, max_date, start_date, end_date

@callback(
    Output('data-store', 'data', allow_duplicate=True),
    Output('upload-status', 'children'),
    Output('file-history', 'options', allow_duplicate=True),
    Output('file-history', 'value', allow_duplicate=True),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def update_output(contents, filename, auth_state):
    if contents is not None:
        token = auth_state.get('token') if auth_state else None
        if not token:
            return dash.no_update, "Unauthorized", dash.no_update, dash.no_update
            
        data = upload_file_to_api(contents, filename, token)
        if data is not None:
            opts = get_history_options(token, auth_state.get('user'), auth_state.get('permissions', []))
            return data, f"Loaded {filename} successfully.", opts, opts[1]['value'] if len(opts)>1 else dash.no_update
        return dash.no_update, "Error parsing file.", dash.no_update, dash.no_update
    return dash.no_update, "", dash.no_update, dash.no_update

@callback(
    Output('data-store', 'data', allow_duplicate=True),
    Input('file-history', 'value'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def load_from_history(filename, auth_state):
    if filename and not str(filename).startswith('HEADER_'):
        token = auth_state.get('token') if auth_state else None
        if token:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = http_session.get(f"{API_BASE_URL}/data/{filename}", headers=headers)
                if response.status_code == 200:
                    return response.json()
            except:
                pass
    return dash.no_update

@callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-export", "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True
)
def export_data(n_clicks, data, companies, languages, start_date, end_date):
    if not n_clicks or not data:
        return dash.no_update
    if ctx.triggered_id != "btn-export":
        return dash.no_update

    df = pd.DataFrame(data)

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]
    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if start_date and end_date:
        date_col = None
        if 'Timestamp' in df.columns:
            date_col = 'Timestamp'
        elif 'Date' in df.columns:
            date_col = 'Date'
        elif 'Call Start Time' in df.columns:
            date_col = 'Call Start Time'

        if date_col in df.columns:
            temp_date = pd.to_datetime(df[date_col]).dt.date
            df = df[(temp_date >= pd.to_datetime(start_date).date()) &
                    (temp_date <= pd.to_datetime(end_date).date())]

    return dcc.send_data_frame(df.to_csv, "export.csv", index=False)

if __name__ == '__main__':
    app.run(debug=True, port=8050)