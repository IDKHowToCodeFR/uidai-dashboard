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
        Output("auth-state", "data", allow_duplicate=True),
        Input("auth-state", "data"),
        Input("url", "pathname"),
        prevent_initial_call='initial_duplicate'
    )
    def render_page(auth_state, pathname):
        page_container_div = html.Div(dash.page_container, id="main-content", className="p-0 m-0" if pathname == '/login' else "main-content")
        
        if pathname == '/login':
            return html.Div([page_container_div], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"}), dash.no_update
            
        if auth_state and auth_state.get('user') and auth_state.get('token'):
            user_role = auth_state.get('user')
            token = auth_state.get('token')
            permissions = auth_state.get('permissions', [])
            
            nav_content, opts, val = None, [], None
            
            if pathname and pathname != '/select':
                if pathname.startswith('/unimate'):
                    context = "UniMate Data"
                    nav_content = [
                        html.H6("UNIMATE", className="section-title mb-3"),
                        dbc.Nav(
                            [
                                dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/unimate/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                                dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/unimate/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                            ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                        )
                    ]
                elif pathname.startswith('/cdr'):
                    context = "CDR Data"
                    nav_content = [
                        html.H6("CDR", className="section-title mb-3"),
                        dbc.Nav(
                            [
                                dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/cdr/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                                dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/cdr/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                            ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                        )
                    ]
                elif pathname.startswith('/apr'):
                    context = "APR Data"
                    nav_content = [
                        html.H6("APR", className="section-title mb-3"),
                        dbc.Nav(
                            [
                                dbc.NavLink([html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")], href="/apr/dashboard", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                                dbc.NavLink([html.I(className="bi bi-person-lines-fill me-3"), html.Span("Agent Performance", className="nav-link-text")], href="/apr/agent-performance", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                                dbc.NavLink([html.I(className="bi bi-person-badge me-3"), html.Span("Agent Explorer", className="nav-link-text")], href="/apr/agent_explorer", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                                dbc.NavLink([html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")], href="/apr/raw_data", active="exact", className="body-strong mb-2 d-flex align-items-center"),
                            ], vertical=True, pills=True, className="custom-sidebar-nav mb-4"
                        )
                    ]
                else:
                    context = "CCF Data"
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
                    
                opts = get_history_options(token, user_role, permissions, data_type=context)
                
                if opts == "UNAUTHORIZED":
                    return html.Div(), None
                    
                if has_permission(permissions, 'can_view_global') and any(opt.get('value') == 'aggregate' for opt in opts):
                    val = 'aggregate'
                else:
                    for opt in opts:
                        if not opt['value'].startswith('HEADER_'):
                            val = opt['value']
                            break
            
            sidebar = get_sidebar(user_role, token, permissions, nav_content, opts, val)
            topbar = get_topbar(user_role, permissions, pathname)
            
            try:
                api_post("logs/page_view", token=token, json={"pathname": pathname})
            except:
                pass
            
            return html.Div([
                topbar,
                sidebar,
                filter_drawer,
                page_container_div
            ], style={"backgroundColor": "var(--color-background)", "minHeight": "100vh"}), dash.no_update
            
        return html.Div(), dash.no_update


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
            
        permissions = auth_state.get('permissions', [])
        
        if pathname == '/login' or pathname == '/':
            if 'can_manage_users' in permissions:
                return '/admin/user_management'
            return '/select'
            
        if pathname == '/select' and auth_state.get('user') == 'Admin':
            return '/admin/user_management'
            
        if pathname.startswith('/admin/user_management') and 'can_manage_users' not in permissions:
            return '/select'
        if pathname.startswith('/admin/logs') and 'can_view_logs' not in permissions:
            return '/select'
        if pathname.startswith('/admin/settings') and 'can_edit_settings' not in permissions:
            return '/select'
            
        if pathname.startswith('/ccf') and 'can_view_ccf' not in permissions:
            return '/select'
        if pathname.startswith('/unimate') and 'can_view_unimate' not in permissions:
            return '/select'
        if pathname.startswith('/cdr') and 'can_view_cdr' not in permissions:
            return '/select'
        if pathname.startswith('/apr') and 'can_view_apr' not in permissions:
            return '/select'
                
        return dash.no_update
