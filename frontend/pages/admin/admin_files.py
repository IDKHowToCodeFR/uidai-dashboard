import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
import requests
from frontend.shared.api_client import api_client
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
            dcc.DatePickerRange(
                id='file-date-picker',
                min_date_allowed=date(2023, 1, 1),
                max_date_allowed=date.today() + timedelta(days=1),
                initial_visible_month=date.today(),
                clearable=True,
                className="me-3"
            ),
            dbc.Button("Export List", id="btn-export-files", color="success", outline=True, size="sm", className="me-2"),
            dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-files", color="primary", size="sm"),
        ], className="d-flex align-items-center")
    ], className="d-flex justify-content-between align-items-center mb-4"),
    
    html.Div([
        html.Div(id="files-table-container")
    ], className="bg-transparent"),
    
    dcc.Download(id="download-raw-file"),
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
    State("impersonate-dropdown", "value")
)
def load_files(auth_state, n_clicks, start_date, end_date, impersonate):
    if not auth_state:
        return html.Div("Unauthorized")
    token = auth_state.get("token")
    if not token:
        return html.Div("Unauthorized")
    try:
        response = api_client.get_history(token, impersonate)
        if response.status_code == 200:
            files = response.json()
            if not files:
                return html.Div("No files uploaded yet.", className="text-muted")
                
            df = pd.DataFrame(files)
            
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
                
                # Header for the group
                sections.append(
                    html.H5(category_name, className="section-title mt-4 mb-3")
                )
                
                group_df = grouped.get_group(category)
                
                # Sort newest first inside group
                group_df = group_df.sort_values(by='time', ascending=False)
                
                cards = []
                for _, row in group_df.iterrows():
                    filename = row.get('name', 'Unknown')
                    upload_time = row.get('time', '')
                    uploader = row.get('uploader', 'Unknown')
                    size = row.get('size', '0 B')
                    
                    card = dbc.Card(
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="bi bi-file-earmark-spreadsheet text-primary fs-3 me-3"),
                                    html.Div([
                                        html.H6(filename, className="mb-1 fw-bold text-dark"),
                                        html.Small(f"Uploaded by {uploader} • {upload_time}", className="text-muted")
                                    ])
                                ], className="d-flex align-items-center"),
                                
                                html.Div([
                                    html.Span(size, className="text-muted me-4 fw-medium"),
                                    dbc.Button(
                                        "Download", 
                                        id={'type': 'btn-download-file', 'index': filename}, 
                                        color="primary", 
                                        outline=True, 
                                        size="sm",
                                        className="rounded-pill px-3 fw-bold"
                                    )
                                ], className="d-flex align-items-center")
                                
                            ], className="d-flex justify-content-between align-items-center")
                        ]),
                        className="mb-2 shadow-sm border-0",
                        style={"borderRadius": "12px", "transition": "transform 0.2s, box-shadow 0.2s"}
                    )
                    cards.append(card)
                    
                sections.append(html.Div(cards))
                
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
        result = api_client.download_file(token, filename, impersonate)
        if result:
            return result
    except:
        pass
        
    return dash.no_update

# We keep this just so btn-export-files has a callback, but since we removed Ag-Grid, 
# we can remove the callback entirely, or change it to download the raw list if we want.
# Actually, since we removed the grid, `files-grid` exportDataAsCsv doesn't exist.
# Let's completely remove the export callback since we don't have a grid to export from anymore.
