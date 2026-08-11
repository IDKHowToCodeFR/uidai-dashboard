import dash
from dash import Input, Output, State
from dash import html
from frontend.auth import login_page
from frontend.shared.api_client import api_client, get_history_options
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
        Output("data-store", "data", allow_duplicate=True),
        Input("auth-state", "data"),
        prevent_initial_call='initial_duplicate'
    )
    def render_page(auth_state):
        if auth_state and auth_state.get('user') and auth_state.get('token'):
            user_role = auth_state.get('user')
            token = auth_state.get('token')
            permissions = auth_state.get('permissions', [])
            sidebar = get_sidebar(user_role, token, permissions)
            
            opts = get_history_options(token, user_role, permissions)
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

            topbar = get_topbar(user_role, permissions)
            
            return html.Div([
                topbar,
                sidebar,
                filter_drawer,
                content_div
            ], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"}), data
            
        return login_page, []

    @app.callback(
        Output("url", "pathname"),
        Input("auth-state", "data"),
        Input("url", "pathname"),
        prevent_initial_call=True
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
