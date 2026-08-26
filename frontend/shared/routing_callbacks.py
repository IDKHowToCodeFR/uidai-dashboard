import dash
from dash import Input, Output, State
from dash import html
from frontend.auth import login_page
from frontend.shared.api_client import api_get, api_post, get_history_options, download_file
from frontend.shared.permissions import has_permission
from frontend.shared.layout import get_topbar, get_sidebar, filter_drawer
import dash_bootstrap_components as dbc

def register_routing_callbacks(app, content_div):
    @app.callback(
        Output("filter-drawer", "is_open"),
        Input("btn-filters", "n_clicks"),
        State("filter-drawer", "is_open"),
    )
    def toggle_filter_drawer(n, is_open):
        if n:
            return not is_open
        return is_open

    @app.callback(
        Output("sidebar", "is_open"),
        Input("btn-sidebar-toggle", "n_clicks"),
        State("sidebar", "is_open"),
    )
    def toggle_left_sidebar(n, is_open):
        if n:
            return not is_open
        return is_open

    @app.callback(
        Output("app-container", "children"),
        Input("auth-state", "data"),
        Input("url", "pathname")
    )
    def render_page(auth_state, pathname):
        if pathname == '/login':
            return html.Div([content_div], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"})
            
        if auth_state and auth_state.get('user') and auth_state.get('token'):
            user_role = auth_state.get('user')
            token = auth_state.get('token')
            permissions = auth_state.get('permissions', [])
            sidebar = get_sidebar(user_role, token, permissions)
            topbar = get_topbar(user_role, permissions)
            
            return html.Div([
                topbar,
                sidebar,
                filter_drawer,
                content_div
            ], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"})
            
        return html.Div()

    @app.callback(
        Output("sidebar-nav-container", "children"),
        Output("file-history", "options"),
        Output("file-history", "value"),
        Output("data-store", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
        Input("context-switcher", "value"),
        State("auth-state", "data"),
        State("url", "pathname"),
        prevent_initial_call='initial_duplicate'
    )
    def switch_context(context, auth_state, current_path):
        if not auth_state or not auth_state.get('token'):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        user_role = auth_state.get('user')
        token = auth_state.get('token')
        permissions = auth_state.get('permissions', [])
        
        # Build Navigation
        if context == "UniMate Data":
            nav_content = [
                html.H6("UNIMATE", className="section-title mb-3"),
                dbc.Nav(
                    [
                        dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/unimate/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                        dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/unimate/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                    ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                )
            ]
            target_url = "/unimate/dashboard"
        elif context == "CDR Data":
            nav_content = [
                html.H6("CDR", className="section-title mb-3"),
                dbc.Nav(
                    [
                        dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/cdr/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                        dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/cdr/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                    ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                )
            ]
            target_url = "/cdr/dashboard"
        else:
            nav_content = [
                html.H6("CCF", className="section-title mb-3"),
                dbc.Nav(
                    [
                        dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/ccf/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                        dbc.NavLink([html.I(className="bi bi-calendar-range me-3"), html.Span("Date Comparison", className="nav-link-text")], href="/ccf/date_comparison", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                        dbc.NavLink([html.I(className="bi bi-clock-history me-3"), html.Span("Hourly Insights", className="nav-link-text")], href="/ccf/hourly", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                        dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/ccf/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                    ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                )
            ]
            target_url = "/ccf/dashboard"
            
        # Get History options filtered by data_type (context)
        opts = get_history_options(token, user_role, permissions, data_type=context)
        val = None
        data = []
        
        if has_permission(permissions, 'can_view_global') and any(opt.get('value') == 'aggregate' for opt in opts):
            val = 'aggregate'
        else:
            for opt in opts:
                if not opt['value'].startswith('HEADER_'):
                    val = opt['value']
                    break
                    
        if val:
            data = {"filename": val, "impersonate": None}
            
        # Decide if redirect is needed
        # We redirect if the user switches contexts explicitly
        url_update = dash.no_update
        ctx = dash.callback_context
        if ctx.triggered and ctx.triggered[0]['prop_id'] == 'context-switcher.value':
            if current_path != target_url:
                url_update = target_url
            
        return nav_content, opts, val, data, url_update
 
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input("auth-state", "data"),
        Input("url", "pathname"),
        prevent_initial_call='initial_duplicate'
    )
    def guard_routes(auth_state, pathname):
        if not auth_state or not auth_state.get('token'):
            if pathname != '/login':
                return '/login'
            return dash.no_update
            
        user_role = auth_state.get('user')
        if pathname == '/login' or pathname == '/':
            return '/admin/user_management' if user_role == 'Admin' else '/ccf/dashboard'
            
        admin_routes = ['/admin/user_management', '/admin/logs', '/admin/files', '/admin/settings']
        user_routes = ['/ccf/dashboard', '/ccf/date_comparison', '/ccf/hourly', '/ccf/raw_data', 
                       '/unimate/dashboard', '/unimate/raw_data', 
                       '/cdr/dashboard', '/cdr/raw_data']
                       
        if user_role == 'Admin':
            if pathname not in admin_routes:
                return '/admin/user_management'
        else:
            if pathname not in user_routes:
                return '/ccf/dashboard'
                
        return dash.no_update
