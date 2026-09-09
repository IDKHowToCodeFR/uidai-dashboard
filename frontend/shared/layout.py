import dash_bootstrap_components as dbc
from dash import dcc, html
from frontend.shared.permissions import has_permission
from frontend.shared.api_client import get_history_options

# --- FILTER DRAWER (Right Side) ---
filter_drawer = dbc.Offcanvas(
    html.Div([
        html.H6("TIME RANGE", className="section-title mb-2"),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date_placeholder_text="Start",
            end_date_placeholder_text="End",
            display_format='YYYY-MM-DD',
            minimum_nights=0,
            className="mb-4 w-100"
        ),

        html.H6("COMPANY", className="section-title mb-2 mt-2"),
        dcc.Dropdown(
            id="company-filter",
            options=[],
            value=[],
            multi=True,
            placeholder="Search Companies...",
            className="mb-4",
            disabled=False
        ),

        html.H6("LANGUAGE", className="section-title mb-2"),
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

def get_topbar(user_role, permissions, pathname=None, lookback_days=None):
    impersonate_div = html.Div(dcc.Dropdown(id="impersonate-dropdown"), style={"display": "none"})

    left_elements = []
    
    if pathname != '/select':
        left_elements.append(
            html.Button(
                html.I(className="bi bi-list fs-5"),
                id="btn-sidebar-toggle",
                n_clicks=0,
                className="btn btn-light me-3 body-strong rounded-circle",
                style={
                    "width": "36px", "height": "36px",
                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                    "border": "1px solid var(--color-border)",
                    "boxShadow": "0 1px 2px rgba(0,0,0,0.04)"
                }
            )
        )
        
    left_elements.extend([
        html.Img(src="/assets/aadhaar-logo.png", style={"height": "32px", "marginRight": "12px"}),
        html.Div([
            html.H5(
                "Unique Identification Authority of India",
                className="mb-0",
                style={
                    "fontWeight": "700",
                    "fontSize": "17px",
                    "lineHeight": "1.2",
                    "color": "#3b5b8c",
                    "fontFamily": "'Inter', sans-serif"
                }
            ),
            html.Span(
                "Internal Administrator Dashboard" if user_role == 'Admin' else "UIDAI Vendor Portal",
                style={
                    "fontSize": "11px",
                    "color": "var(--color-text-muted, #6c757d)",
                    "letterSpacing": "0.3px",
                    "fontFamily": "'Inter', sans-serif"
                }
            )
        ], style={"display": "flex", "flexDirection": "column", "justifyContent": "center"})
    ])

    right_elements = [
        impersonate_div,
    ]
    
    is_dashboard = pathname and any(pathname.startswith(p) for p in ['/ccf', '/cdr', '/unimate', '/apr'])
    visibility_class = "d-flex align-items-center" if is_dashboard else "d-none"
    
    pass
    
    right_elements.append(
        html.Div([
            dcc.Dropdown(
                id='sl-granularity',
                options=[
                    {'label': 'Auto', 'value': 'Auto'},
                    {'label': 'Daily', 'value': 'D'},
                    {'label': 'Weekly', 'value': 'W-MON'},
                    {'label': 'Monthly', 'value': 'M'},
                    {'label': 'Yearly', 'value': 'Y'}
                ],
                value='Auto',
                clearable=False,
                className="me-3",
                style={'width': '100px', 'marginRight': '24px'}
            ),
            dbc.Checklist(
                options=[{"label": "Dynamic Scale", "value": 1}],
                value=[1],
                id="sl-scale-toggle",
                switch=True,
                className="me-4 mb-0"
            )
        ], className=visibility_class)
    )
    
    right_elements.append(
        html.Button(
            html.I(className="bi bi-funnel-fill fs-6"),
            id="btn-filters",
            n_clicks=0,
            className=f"btn btn-light me-3 body-strong rounded-circle {'' if is_dashboard else 'd-none'}",
            style={
                "width": "36px", "height": "36px",
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "border": "1px solid var(--color-border)",
                "boxShadow": "0 1px 2px rgba(0,0,0,0.04)"
            }
        )
    )
        

    if pathname != '/select' and user_role != 'Admin':
        right_elements.append(
            dbc.Button(
                html.I(className="bi bi-house-fill fs-6"),
                href="/select",
                className="btn btn-light me-3 body-strong rounded-circle",
                style={
                    "width": "36px", "height": "36px",
                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                    "border": "1px solid var(--color-border)",
                    "boxShadow": "0 1px 2px rgba(0,0,0,0.04)"
                }
            )
        )
        
    right_elements.extend([
        html.Button(
            html.I(className="bi bi-box-arrow-right fs-6"),
            id="btn-logout",
            n_clicks=0,
            className="btn btn-light body-strong rounded-circle",
            style={
                "width": "36px", "height": "36px",
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "border": "1px solid var(--color-border)",
                "boxShadow": "0 1px 2px rgba(0,0,0,0.04)"
            }
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
    ])

    return html.Div(
        [
            html.Div(left_elements, style={"display": "flex", "alignItems": "center"}),
            html.Div(right_elements, style={"display": "flex", "alignItems": "center"})
        ],
        className="topbar px-4",
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "right": 0,
            "height": "64px",
            "zIndex": 1000,
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "backgroundColor": "var(--color-surface, #fff)",
            "borderBottom": "1px solid var(--color-border, #e2e8f0)",
            "borderRadius": "0 0 6px 6px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.04)"
        }
    )

def get_sidebar(user_role, token, permissions, nav_content=None, history_options=None, history_value=None):
    if user_role == 'Admin':
        sidebar_content = html.Div([
            html.H6("ADMINISTRATOR", className="section-title mb-3"),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="bi bi-people-fill me-3"), html.Span("Manage Users", className="nav-link-text")],
                        href="/admin/user_management",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-card-list me-3"), html.Span("System Logs", className="nav-link-text")],
                        href="/admin/logs",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-folder-fill me-3"), html.Span("File Repository", className="nav-link-text")],
                        href="/admin/files",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-gear-fill me-3"), html.Span("Global Settings", className="nav-link-text")],
                        href="/admin/settings",
                        active="exact",
                        className="body-strong mb-2 d-flex align-items-center"
                    ),
                ],
                vertical=True,
                pills=True,
                className="custom-sidebar-nav mb-5"
            ),
            html.Div(
                dbc.RadioItems(id="file-history", options=[], value=None),
                style={"display": "none"}
            )
        ], className="sidebar-content-wrapper")
        return dbc.Offcanvas(
            sidebar_content,
            id="sidebar",
            title="Admin Console",
            placement="start",
            is_open=False,
            className="premium-offcanvas sidebar-container border-0 shadow-lg"
        )
        
    

    sidebar_content = html.Div([
        # Context switcher removed per requirements. Context is selected via the /select landing page.
        html.Div(id="context-switcher", style={"display": "none"}),
        
        html.Div(nav_content, id="sidebar-nav-container"),

        html.Hr(style={"borderColor": "#e2e8f0"}),
        html.H6("HISTORY", className="section-title mb-3"),

        html.Div(
            dbc.RadioItems(
                id="file-history",
                options=history_options or [],
                value=history_value,
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
