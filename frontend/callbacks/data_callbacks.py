import dash
from dash import Input, Output, State, ctx
import pandas as pd
from frontend.utils.api import api_client, upload_file_to_api, get_history_options, get_dataframe

def register_data_callbacks(app):
    @app.callback(
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
        State('auth-state', 'data'),
        prevent_initial_call=True
    )
    def populate_filters(data_ref, auth_state):
        if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
            return [], [], False, [], [], None, None, None, None
            
        token = auth_state.get('token') if auth_state else None
        if not token:
            return [], [], False, [], [], None, None, None, None
            
        df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
        if df.empty:
            return [], [], False, [], [], None, None, None, None
        
        c_options, c_values, c_disabled = [], [], False
        l_options, l_values = [], []
        
        user_role = auth_state.get('user') if auth_state else None
        
        if 'Company' in df.columns:
            companies = df['Company'].dropna().unique().tolist()
            c_options = [{'label': c, 'value': c} for c in companies]
            if user_role in ['Admin', 'UIDAI']:
                c_values = companies
            else:
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

    @app.callback(
        Output('upload-status', 'children'),
        Output('upload-progress', 'style'),
        Output('upload-progress', 'value'),
        Output('upload-progress', 'label'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('auth-state', 'data'),
        State('ws-client-id', 'data'),
        prevent_initial_call=True
    )
    def update_output(contents, filename, auth_state, client_id):
        if contents is not None:
            token = auth_state.get('token') if auth_state else None
            if not token:
                return "Unauthorized", dash.no_update, dash.no_update, dash.no_update
                
            data = upload_file_to_api(contents, filename, token, client_id=client_id)
            if data and data.get("status") == "processing":
                return "Upload started, processing in background...", {"height": "16px", "marginTop": "8px", "display": "block"}, 5, "Initializing..."
            return "Error starting upload.", dash.no_update, dash.no_update, dash.no_update
        return "", {"display": "none"}, 0, ""

    @app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Output('file-history', 'options', allow_duplicate=True),
        Output('file-history', 'value', allow_duplicate=True),
        Output('upload-status', 'children', allow_duplicate=True),
        Output('upload-progress', 'style', allow_duplicate=True),
        Input('ws-trigger', 'n_clicks'),
        State('ws-data', 'value'),
        State('auth-state', 'data'),
        State('impersonate-dropdown', 'value'),
        prevent_initial_call=True
    )
    def on_upload_complete(n_clicks, ws_data_str, auth_state, impersonate):
        import json
        if not ws_data_str:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        try:
            ws_data = json.loads(ws_data_str)
        except:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        if not ws_data or ws_data.get('status') != 'complete':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        token = auth_state.get('token') if auth_state else None
        if not token:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        filename = ws_data.get('filename')
        # We no longer fetch data into the client, we just pass the reference
        opts = get_history_options(token, auth_state.get('user'), auth_state.get('permissions', []), impersonate)
        return {"filename": filename, "impersonate": impersonate}, opts, filename, f"Upload complete: {filename}", {"display": "none"}

    @app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('file-history', 'value'),
        State('auth-state', 'data'),
        State('impersonate-dropdown', 'value'),
        prevent_initial_call=True
    )
    def load_from_history(filename, auth_state, impersonate):
        if filename and not str(filename).startswith('HEADER_'):
            token = auth_state.get('token') if auth_state else None
            if token:
                return {"filename": filename, "impersonate": impersonate}
        return dash.no_update

    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("btn-export", "n_clicks"),
        State('data-store', 'data'),
        State('company-filter', 'value'),
        State('language-filter', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        State('auth-state', 'data'),
        prevent_initial_call=True
    )
    def export_data(n_clicks, data_ref, companies, languages, start_date, end_date, auth_state):
        if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
            return dash.no_update
        if ctx.triggered_id != "btn-export":
            return dash.no_update

        token = auth_state.get('token') if auth_state else None
        if not token: return dash.no_update
        
        df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
        if df.empty: return dash.no_update

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

        return dash.dcc.send_data_frame(df.to_csv, "export.csv", index=False)

    @app.callback(
        Output('impersonate-dropdown', 'options'),
        Input('auth-state', 'data')
    )
    def populate_impersonate(auth_state):
        if not auth_state:
            return dash.no_update
        permissions = auth_state.get('permissions', [])
        token = auth_state.get('token')
        if 'can_view_global' in permissions:
            response = api_client.get_users(token)
            if response.status_code == 200:
                users = response.json()
                return [{'label': k, 'value': k} for k in users.keys() if k != 'Admin']
        return dash.no_update

    @app.callback(
        Output('file-history', 'options', allow_duplicate=True),
        Output('file-history', 'value', allow_duplicate=True),
        Input('impersonate-dropdown', 'value'),
        State('auth-state', 'data'),
        prevent_initial_call=True
    )
    def update_history_on_impersonate(impersonate_val, auth_state):
        if not auth_state:
            return dash.no_update, dash.no_update
        token = auth_state.get('token')
        user_role = auth_state.get('user')
        permissions = auth_state.get('permissions', [])
        opts = get_history_options(token, user_role, permissions, impersonate=impersonate_val)
        val = None
        if 'can_view_global' in permissions and any(opt.get('value') == 'aggregate' for opt in opts):
            val = 'aggregate'
        else:
            for opt in opts:
                if not opt['value'].startswith('HEADER_'):
                    val = opt['value']
                    break
        return opts, val

