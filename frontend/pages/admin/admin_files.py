import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
import requests
from frontend.shared.api_client import api_get, api_post, get_history_options, download_file
import pandas as pd
import base64
from datetime import datetime, date, timedelta

dash.register_page(__name__, path='/admin-files', name='File Repository')

layout = html.Div([
    html.Div([
        html.Div([
            html.H3("File Repository", className="display-xl mb-0"),
            html.P("Manage and export uploaded datasets.", className="text-muted mb-0 mt-2"),
        ]),
        html.Div([
            html.Span("Select Type:", className="me-2 text-muted fw-bold small text-uppercase"),
            dcc.Dropdown(
                id='file-type-filter',
                options=[{'label': 'CCF Data', 'value': 'CCF Data'}],
                value='CCF Data',
                clearable=False,
                style={'width': '220px'},
                className="shadow-sm d-inline-block"
            ),
            dcc.DatePickerRange(
                id='file-date-picker',
                # min_date_allowed=date(2023, 1, 1),
                max_date_allowed=date.today() + timedelta(days=1),
                initial_visible_month=date.today(),
                clearable=True,
                className="shadow-sm border-0 rounded"
            ),
            dbc.Button("Export List", id="btn-export-files", color="success", outline=True, size="sm", className="shadow-sm"),
            dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-files", color="primary", size="sm", className="shadow-sm"),
        ], className="d-flex align-items-center gap-3")
    ], className="d-flex justify-content-between align-items-center mb-4"),
    
    html.Div([
        html.H6("UPLOAD NEW DATA", className="section-title mb-3 mt-4"),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    html.I(className="bi bi-cloud-arrow-up text-primary mb-2 d-block", style={"fontSize": "2rem"}),
                    html.H6('Drag & Drop your Excel dataset here', className="text-dark fw-bold mb-1"),
                    html.Span(['or ', html.A('browse files', className="text-primary text-decoration-underline fw-medium")], className="text-muted small")
                ]),
                multiple=False,
                accept=".xlsx, .xls",
                className="upload-box mb-3 p-3 border border-2 border-primary rounded bg-light text-center shadow-sm",
                style={"borderStyle": "dashed", "cursor": "pointer"}
            )
        ]),
        
        html.Div(id='progress-container', children=[
            html.Div(id='upload-status', className="nav-link-text text-muted small mt-2"),
            dbc.Progress(id="upload-progress", value=0, striped=True, animated=True, style={"height": "10px", "marginTop": "8px", "display": "none"}),
        ]),
        
        dcc.Store(id='ws-client-id'),
        dcc.Input(id='ws-data', type='hidden', value=''),
        html.Button(id='ws-trigger', style={'display': 'none'})
        
    ], style={"display": "block", "marginBottom": "2rem", "maxWidth": "1500px"}),
    
    html.Div([
        html.Div(id="files-table-container")
    ], className="bg-transparent"),
    
    dcc.Download(id="download-raw-file"),
    dcc.Download(id="download-export-csv"),
], className="container-fluid py-4")

def get_time_group(iso_time_str):
    try:
        t = datetime.fromisoformat(iso_time_str)
        t_date = t.date()
        today = date.today()
        if t_date == today: return "1 - Today"
        elif t_date == today - timedelta(days=1): return "2 - Yesterday"
        elif t_date >= today - timedelta(days=7): return "3 - This Week"
        elif t_date.month == today.month and t_date.year == today.year: return "4 - This Month"
        else: return "5 - Older"
    except:
        return "5 - Older"

@callback(
    Output("files-table-container", "children"),
    Input("auth-state", "data"),
    Input("btn-refresh-files", "n_clicks"),
    Input("file-date-picker", "start_date"),
    Input("file-date-picker", "end_date"),
    Input("file-type-filter", "value"),
    State("impersonate-dropdown", "value")
)
def load_files(auth_state, n_clicks, start_date, end_date, selected_type, impersonate):
    if not auth_state:
        return html.Div("Unauthorized")
    token = auth_state.get("token")
    if not token:
        return html.Div("Unauthorized")
    try:
        response = api_get("history", token=token, params={"impersonate": impersonate})
        if response.status_code == 200:
            files = response.json()
            if not files:
                return html.Div("No files uploaded yet.", className="text-muted")
                
            df = pd.DataFrame(files)
            
            # Filter by data type
            if selected_type and 'data_type' in df.columns:
                df = df[df['data_type'].str.lower() == selected_type.lower()]
                
            if df.empty:
                return html.Div(f"No {selected_type} files found.", className="text-muted")
            
            # Filter by date
            if 'time' in df.columns:
                df['parsed_time'] = pd.to_datetime(df['time'])
                
                if start_date:
                    start_dt = pd.to_datetime(start_date, utc=True).tz_localize(None)
                    df = df[df['parsed_time'] >= start_dt]
                    
                if end_date:
                    end_dt = pd.to_datetime(end_date, utc=True).tz_localize(None) + pd.Timedelta(days=1)
                    df = df[df['parsed_time'] < end_dt]
                    
                df['Date Category'] = df['time'].apply(get_time_group)
                df['time'] = df['parsed_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                df = df.drop(columns=['parsed_time'])
            
            if df.empty:
                return html.Div("No files match the selected date range.", className="text-muted")
            
            # Format size nicely
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
                    
            if 'size' in df.columns:
                df['size'] = df['size'].apply(format_size)
                
            # Build List View
            sections = []
            
            # Group by Date Category
            grouped = df.groupby('Date Category')
            
            # Sort categories (1 - Today, 2 - Yesterday, etc.)
            sorted_categories = sorted(grouped.groups.keys())
            
            for category in sorted_categories:
                category_name = category.split(' - ')[1] if ' - ' in category else category
                
                group_df = grouped.get_group(category)
                
                sections.append(
                    html.H5(f"{category_name} ({len(group_df)} files)", className="section-title mt-4 mb-3")
                )
                
                # Sort newest first inside group
                group_df = group_df.sort_values(by='time', ascending=False)
                
                cards = []
                for _, row in group_df.iterrows():
                    filename = row.get('name', 'Unknown')
                    upload_time = row.get('time', '')
                    uploader = row.get('uploader', 'Unknown')
                    size = row.get('size', '0 B')
                    
                    card = dbc.Col([
                        dbc.Card(
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="bi bi-file-earmark-spreadsheet text-primary mb-3 d-block text-center", style={"fontSize": "3rem"}),
                                    html.H6(filename, className="fw-bold text-dark text-truncate text-center mb-1", title=filename),
                                    html.P(f"By {uploader}", className="small text-muted text-center mb-3"),
                                    
                                    html.Div([
                                        html.Span(upload_time, className="small text-muted"),
                                        html.Span(size, className="small text-muted fw-bold"),
                                    ], className="d-flex justify-content-between align-items-center mb-3"),
                                    
                                    dbc.Button("Download", id={'type': 'btn-download-file', 'index': filename}, color="primary", outline=True, size="sm", className="w-100 fw-bold rounded-pill")
                                ], className="d-flex flex-column h-100 justify-content-between")
                            ], className="d-flex flex-column h-100"),
                            className="shadow-sm border-0 h-100 hover-lift custom-card",
                            style={"borderRadius": "12px"}
                        )
                    ], xs=12, sm=6, md=4, lg=3, className="mb-4")
                    cards.append(card)
                    
                sections.append(dbc.Row(cards, className="g-3"))
                
            return html.Div(sections)
        return html.Div(f"Error fetching files: {response.text}", className="text-danger")
    except Exception as e:
        return html.Div(f"API Error: {str(e)}", className="text-danger")

@callback(
    Output("download-raw-file", "data"),
    Input({'type': 'btn-download-file', 'index': ALL}, 'n_clicks'),
    State("auth-state", "data"),
    State("impersonate-dropdown", "value"),
    prevent_initial_call=True
)
def handle_download_click(n_clicks_list, auth_state, impersonate):
    if not any(n_clicks_list):
        return dash.no_update
        
    ctx = dash.ctx
    if not ctx.triggered or not auth_state:
        return dash.no_update
        
    triggered_id = ctx.triggered_id
    if not triggered_id or not isinstance(triggered_id, dict) or triggered_id.get('type') != 'btn-download-file':
        return dash.no_update
        
    filename = triggered_id.get('index')
    if not filename:
        return dash.no_update
        
    token = auth_state.get("token")
    try:
        result = download_file(token, filename, impersonate)
        if result:
            return result
    except:
        pass
        
    return dash.no_update

# We keep this just so btn-export-files has a callback, but since we removed Ag-Grid, 
# we can remove the callback entirely, or change it to download the raw list if we want.
# Actually, since we removed the grid, `files-grid` exportDataAsCsv doesn't exist.
@callback(
    Output("download-export-csv", "data"),
    Input("btn-export-files", "n_clicks"),
    State("auth-state", "data"),
    State("file-date-picker", "start_date"),
    State("file-date-picker", "end_date"),
    State("file-type-filter", "value"),
    State("impersonate-dropdown", "value"),
    prevent_initial_call=True
)
def export_file_list(n_clicks, auth_state, start_date, end_date, selected_type, impersonate):
    if not n_clicks or not auth_state:
        return dash.no_update
    token = auth_state.get("token")
    if not token:
        return dash.no_update
        
    try:
        response = api_get("history", token=token, params={"impersonate": impersonate})
        if response.status_code == 200:
            files = response.json()
            if not files:
                return dash.no_update
                
            df = pd.DataFrame(files)
            if selected_type and 'data_type' in df.columns:
                df = df[df['data_type'].str.lower() == selected_type.lower()]
                
            if 'time' in df.columns:
                df['parsed_time'] = pd.to_datetime(df['time'])
                if start_date:
                    start_dt = pd.to_datetime(start_date, utc=True).tz_localize(None)
                    df = df[df['parsed_time'] >= start_dt]
                if end_date:
                    end_dt = pd.to_datetime(end_date, utc=True).tz_localize(None) + pd.Timedelta(days=1)
                    df = df[df['parsed_time'] < end_dt]
                df = df.drop(columns=['parsed_time'])
                
            return dcc.send_data_frame(df.to_csv, "file_repository_export.csv", index=False)
    except:
        pass
        
    return dash.no_update

@callback(
    Output("file-type-filter", "options"),
    Input("auth-state", "data")
)
def populate_data_types(auth_state):
    default_options = [{'label': 'CCF Data', 'value': 'CCF Data'}]
    if not auth_state:
        return default_options
    token = auth_state.get('token')
    if not token:
        return default_options
    try:
        response = api_get("data_types", token=token)
        if response.status_code == 200:
            types = response.json()
            options = [{'label': t, 'value': t} for t in types]
            return options
    except:
        pass
    return default_options
