import dash
from dash import Input, Output, State, ctx, html
from frontend.shared.api_client import api_get, api_post, get_history_options, download_file

def register_admin_callbacks(app):
    # --- ADMIN: OPEN ADD MODAL ---
    @app.callback(
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
    @app.callback(
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
            req_data = {"username": username, "password": password, "company_name": company_name}
            response = api_post("users/add", token=token, json=req_data)
            if response.status_code == 200:
                return html.Span(response.json().get("message"), className="text-success"), "", "", "", (version or 0) + 1, False
            else:
                return html.Span(response.json().get("detail", "Error"), className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True
        except Exception as e:
            return html.Span("API Error", className="text-danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, True

    # --- ADMIN: OPEN REMOVE MODAL ---
    @app.callback(
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
    @app.callback(
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
            response = api_get("users", token=token)
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
    @app.callback(
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
            response = api_post("users/remove", token=token, json={"username": username})
            if response.status_code == 200:
                return html.Span(response.json().get("message"), className="text-success"), None, (version or 0) + 1, False
            else:
                return html.Span(response.json().get("detail", "Error"), className="text-danger"), dash.no_update, dash.no_update, True
        except:
            return html.Span("API Error", className="text-danger"), dash.no_update, dash.no_update, True

    # --- ADMIN: MANAGE PERMISSIONS MODAL ---
    @app.callback(
        Output("manage-perms-modal", "is_open"),
        Input("btn-open-manage-permissions", "n_clicks"),
        State("manage-perms-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_manage_perms_modal(n, is_open):
        if n:
            return not is_open
        return is_open

    @app.callback(
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
            response = api_get("users", token=token)
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

    @app.callback(
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
            response = api_get("users", token=token)
            if response.status_code == 200:
                users = response.json()
                user_data = users.get(username, {})
                return user_data.get("permissions", [])
        except:
            pass
        return []

    @app.callback(
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
            payload = {"username": username, "permissions": switches}
            response = api_post("users/permissions", token=token, json=payload)
            if response.status_code == 200:
                return html.Span(response.json().get("message"), className="text-success"), False
            else:
                return html.Span(response.json().get("detail", "Error"), className="text-danger"), True
        except:
            return html.Span("API Error", className="text-danger"), True

    # --- LOGOUT: ASK CONFIRMATION ---
    @app.callback(
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
    @app.callback(
        Output("auth-state", "data", allow_duplicate=True),
        Output("auth-state-local", "data", allow_duplicate=True),
        Output("auth-state-session", "data", allow_duplicate=True),
        Output("data-store", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
        Output("logout-confirm-modal", "is_open", allow_duplicate=True),
        Input("btn-logout-confirm", "n_clicks"),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        if n_clicks:
            return None, None, None, None, '/', False
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
