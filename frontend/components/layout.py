import dash_bootstrap_components as dbc
from dash import dcc, html
from frontend.utils.permissions import has_permission
from frontend.utils.api import get_history_options

# --- FILTER DRAWER (Right Side) ---
filter_drawer = dbc.Offcanvas(
    html.Div([
        html.H6("TIME RANGE", className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date_placeholder_text="Start",
            end_date_placeholder_text="End",
            display_format='YYYY-MM-DD',
            minimum_nights=0,
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

def get_topbar(user_role, permissions):
    impersonate_div = html.Div(dcc.Dropdown(id="impersonate-dropdown"), style={"display": "none"})

    left_elements = [
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
        ),
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
                "Internal Administrator Dashboard",
                style={
                    "fontSize": "11px",
                    "color": "var(--color-text-muted, #6c757d)",
                    "letterSpacing": "0.3px",
                    "fontFamily": "'Inter', sans-serif"
                }
            )
        ], style={"display": "flex", "flexDirection": "column", "justifyContent": "center"})
    ]

    right_elements = [
        impersonate_div,
    ]
    
    if user_role != 'Admin':
        right_elements.append(
            html.Button(
                html.I(className="bi bi-funnel-fill fs-6"),
                id="btn-filters",
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
                    dbc.NavLink(
                        [html.I(className="bi bi-gear-fill me-3"), html.Span("Global Settings", className="nav-link-text")],
                        href="/admin-settings",
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
            placement="start",
            is_open=False,
            className="premium-offcanvas sidebar-container border-0 shadow-lg"
        )
        
    opts = get_history_options(token, user_role, permissions)
    val = None
    
    if has_permission(permissions, 'can_view_global') and any(opt.get('value') == 'aggregate' for opt in opts):
        val = 'aggregate'
    else:
        for opt in opts:
            if not opt['value'].startswith('HEADER_'):
                val = opt['value']
                break
            
    can_upload = 'can_upload_files' in permissions

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
            
            html.Div(id='progress-container', children=[
                html.Div(id='upload-status', className="nav-link-text text-muted small mt-2"),
                dbc.Progress(id="upload-progress", value=0, striped=True, animated=True, style={"height": "10px", "marginTop": "8px", "display": "none"}),
            ]),
            
            dcc.Store(id='ws-client-id'),
            dcc.Input(id='ws-data', type='hidden', value=''),
            html.Button(id='ws-trigger', style={'display': 'none'})
            
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
