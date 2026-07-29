import os
import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
from datetime import datetime, timedelta
import numpy as np
from auth import login_page, handle_login, add_user, remove_user  # noqa: F401

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'),
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
    suppress_callback_exceptions=True
)
app.title = "UIDAI Dashboard"

# Directory for processed data
PROCESSED_DATA_DIR = "data/processed"

def get_history_options(user_role):
    if not os.path.exists(PROCESSED_DATA_DIR):
        return []
    
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    if user_role and user_role != 'Admin':
        prefix = f"{user_role}_"
        files = [f for f in files if f.startswith(prefix)]

    file_times = []
    for f in files:
        file_path = os.path.join(PROCESSED_DATA_DIR, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        file_times.append({'name': f, 'time': mtime})

    file_times.sort(key=lambda x: x['time'], reverse=True)

    now = datetime.now()
    today = now.date()

    options = []
    current_group = None

    for item in file_times:
        mtime = item['time']
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

    return options

def parse_contents(contents, filename, user_role):
    prefix = f"{user_role}_" if user_role and user_role != 'Admin' else "Admin_"
    out_filename = prefix + os.path.splitext(filename)[0] + "_processed.csv"
    save_path = os.path.join(PROCESSED_DATA_DIR, out_filename)

    if os.path.exists(save_path):
        try:
            df = pd.read_csv(save_path)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error reading existing file: {e}")

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            excel_file = pd.ExcelFile(io.BytesIO(decoded), engine='openpyxl')
            dfs = []
            for sheet_name in excel_file.sheet_names:
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if 'Company' not in sheet_df.columns:
                    sheet_df['Company'] = sheet_name
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
        else:
            return None

        numeric_cols = df.select_dtypes(include='number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        object_cols = df.select_dtypes(include=['object', 'string']).columns # type: ignore
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)

        # Save to processed directory for history
        if not os.path.exists(PROCESSED_DATA_DIR):
            os.makedirs(PROCESSED_DATA_DIR)
        df.to_csv(save_path, index=False)

        return df.to_dict('records')
    except Exception as e:
        print(e)
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

# --- TOPBAR ---
topbar = html.Div(
    [
        html.Div([
            # Hamburger Menu Button
            html.Button(
                html.I(className="bi bi-list fs-4"),
                id="btn-sidebar-toggle",
                n_clicks=0,
                className="btn btn-light me-3 body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
            ),
            html.H2("UIDAI", className="display-lg mb-0 me-4", style={"display": "inline-block"}),
        ], style={"display": "flex", "alignItems": "center"}),

        # Right aligned action buttons
        html.Div([
            # Filters Drawer Button
            html.Button(
                html.I(className="bi bi-funnel-fill"),
                id="btn-filters",
                n_clicks=0,
                className="btn btn-light me-3 body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
            ),
            # Export Data Button
            html.Button(
                html.I(className="bi bi-download"),
                id="btn-export",
                className="btn btn-primary body-strong rounded-circle shadow-sm me-3",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center"}
            ),
            # Logout Button
            html.Button(
                html.I(className="bi bi-box-arrow-right"),
                id="btn-logout",
                n_clicks=0,
                className="btn btn-light body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
            )
        ], style={"display": "flex", "alignItems": "center"})
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

def get_sidebar(user_role):
    opts = get_history_options(user_role)
    val = None
    for opt in opts:
        if not opt['value'].startswith('HEADER_'):
            val = opt['value']
            break

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

        html.H6("HISTORY", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
        html.Div(
            dbc.RadioItems(
                id="file-history",
                options=opts,
                value=val,
                className="mb-4 history-radio-group"
            )
        ),

        # --- ADMIN SECTION (hidden by default, shown via callback) ---
        html.Div(
            id="admin-section",
            style={"display": "block"} if user_role == 'Admin' else {"display": "none"},
            children=[
                html.Hr(style={"borderColor": "#e2e8f0"}),
                html.H6("ADMIN", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
                dbc.Button(
                    [html.I(className="bi bi-plus-circle me-2"), "Add New Company"],
                    id="btn-open-add-company",
                    color="primary",
                    size="sm",
                    className="w-100 mb-2"
                ),
                dbc.Button(
                    [html.I(className="bi bi-dash-circle me-2"), "Remove Company"],
                    id="btn-open-remove-company",
                    color="danger",
                    outline=True,
                    size="sm",
                    className="w-100"
                ),
            ]
        ),

        # --- ADD COMPANY MODAL ---
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Add New Company")),
            dbc.ModalBody([
                dbc.Label("Company Name", className="small text-muted text-uppercase", style={"fontSize": "10px", "letterSpacing": "1px"}),
                dbc.Input(id="new-company-name", placeholder="e.g. Acme Corp", type="text", className="mb-3", size="sm"),
                dbc.Label("Username", className="small text-muted text-uppercase", style={"fontSize": "10px", "letterSpacing": "1px"}),
                dbc.Input(id="new-company-username", placeholder="Login username", type="text", className="mb-3", size="sm"),
                dbc.Label("Password", className="small text-muted text-uppercase", style={"fontSize": "10px", "letterSpacing": "1px"}),
                dbc.Input(id="new-company-password", placeholder="Login password", type="password", className="mb-3", size="sm"),
                html.Div(id="add-company-status", className="small mt-1")
            ]),
            dbc.ModalFooter(
                dbc.Button("Add Company", id="btn-add-company", color="primary", size="sm")
            )
        ], id="add-company-modal", is_open=False, centered=True),

        # --- REMOVE COMPANY MODAL ---
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Remove Company")),
            dbc.ModalBody([
                dbc.Label("Select Company", className="small text-muted text-uppercase", style={"fontSize": "10px", "letterSpacing": "1px"}),
                dcc.Dropdown(id="remove-company-select", options=[], placeholder="Choose a company...", className="mb-3"),
                html.Div("This will permanently revoke the company's login access.", className="small text-muted mb-2"),
                html.Div(id="remove-company-status", className="small mt-1")
            ]),
            dbc.ModalFooter(
                dbc.Button("Remove Company", id="btn-remove-company", color="danger", size="sm")
            )
        ], id="remove-company-modal", is_open=False, centered=True)
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

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='data-store', data=[]),
    dcc.Store(id='auth-state', storage_type='session'),
    dcc.Store(id='company-list-version', data=0),
    dcc.Download(id="download-dataframe-csv"),
    html.Div(id="app-container")
])

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
    if auth_state and auth_state.get('user'):
        user_role = auth_state.get('user')
        sidebar = get_sidebar(user_role)
        
        # Determine initial data based on history
        opts = get_history_options(user_role)
        val = None
        data = []
        for opt in opts:
            if not opt['value'].startswith('HEADER_'):
                val = opt['value']
                break
                
        if val:
            file_path = os.path.join(PROCESSED_DATA_DIR, val)
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                data = df.to_dict('records')

        return html.Div([
            topbar,
            sidebar,
            filter_drawer,
            content
        ]), data
    return login_page, []

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
    prevent_initial_call=True
)
def handle_add_company(n_clicks, company_name, username, password, version):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not company_name or not username or not password:
        return html.Span("All fields required.", className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True
    ok, msg = add_user(username, password, company_name)
    if ok:
        return html.Span(msg, className="text-success"), "", "", "", (version or 0) + 1, False
    return html.Span(msg, className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True

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
    Input("company-list-version", "data")
)
def populate_remove_company_options(is_open, _version):
    from auth import load_users
    users = load_users()
    options = [
        {"label": u["user"], "value": key}
        for key, u in users.items()
        if u.get("user") != "Admin"
    ]
    return options

# --- ADMIN: REMOVE COMPANY ---
@callback(
    Output("remove-company-status", "children"),
    Output("remove-company-select", "value"),
    Output("company-list-version", "data", allow_duplicate=True),
    Output("remove-company-modal", "is_open", allow_duplicate=True),
    Input("btn-remove-company", "n_clicks"),
    State("remove-company-select", "value"),
    State("company-list-version", "data"),
    prevent_initial_call=True
)
def handle_remove_company(n_clicks, username, version):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not username:
        return html.Span("Select a company first.", className="text-danger"), dash.no_update, dash.no_update, True
    ok, msg = remove_user(username)
    if ok:
        return html.Span(msg, className="text-success"), None, (version or 0) + 1, False
    return html.Span(msg, className="text-danger"), dash.no_update, dash.no_update, True

@callback(
    Output("auth-state", "data", allow_duplicate=True),
    Input("btn-logout", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks:
        return None
    return dash.no_update

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

    if 'Company' in df.columns:
        companies = df['Company'].dropna().unique().tolist()
        # Admin sees all companies + any registered company names from users.json
        if user_role == 'Admin':
            from auth import load_users
            registered = [u['user'] for u in load_users().values() if u['user'] != 'Admin']
            all_companies = sorted(set(companies + registered))
            c_options = [{'label': c, 'value': c} for c in all_companies]
            c_values = companies  # default select only those with data
        else:
            # Non-admin: lock to their company
            c_options = [{'label': user_role, 'value': user_role}]
            c_values = [user_role]
            c_disabled = True

    if 'Language' in df.columns:
        langs = df['Language'].dropna().unique().tolist()
        l_options = [{'label': l, 'value': l} for l in langs]
        l_values = langs

    min_date = max_date = start_date = end_date = None
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
    elif 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()
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
        user_role = auth_state.get('user') if auth_state else None
        data = parse_contents(contents, filename, user_role)
        if data is not None:
            opts = get_history_options(user_role)
            return data, f"Loaded {filename} successfully.", opts, opts[1]['value'] if len(opts)>1 else dash.no_update
        return dash.no_update, "Error parsing file.", dash.no_update, dash.no_update
    return dash.no_update, "", dash.no_update, dash.no_update

@callback(
    Output('data-store', 'data', allow_duplicate=True),
    Input('file-history', 'value'),
    prevent_initial_call=True
)
def load_from_history(filename):
    if filename and not str(filename).startswith('HEADER_'):
        file_path = os.path.join(PROCESSED_DATA_DIR, filename)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            return df.to_dict('records')
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