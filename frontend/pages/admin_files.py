import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import requests
import pandas as pd
import base64
from datetime import datetime, date, timedelta
from auth import API_BASE_URL

dash.register_page(__name__, path='/admin-files', name='File Repository')

layout = html.Div([
    html.H2("File Repository", className="mb-4 text-primary fw-bold"),
    html.Div([
        dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-files", color="light", className="me-2 mb-3"),
        dbc.Button([html.I(className="bi bi-download me-2"), "Export List"], id="btn-export-files", color="primary", outline=True, className="mb-3"),
        html.Div(id="files-table-container")
    ]),
    dcc.Download(id="download-raw-file")
])

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
    Input("btn-refresh-files", "n_clicks")
)
def load_files(auth_state, n_clicks):
    if not auth_state:
        return html.Div("Unauthorized")
    token = auth_state.get("token")
    if not token:
        return html.Div("Unauthorized")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE_URL}/history", headers=headers)
        if response.status_code == 200:
            files = response.json()
            if not files:
                return html.Div("No files uploaded yet.", className="text-muted")
                
            df = pd.DataFrame(files)
            
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
                
            if 'time' in df.columns:
                df['Date Category'] = df['time'].apply(get_time_group)
                
            # Add action button
            df['action'] = "⬇ Download File"
                
            grid = dag.AgGrid(
                id="files-grid",
                rowData=df.to_dict("records"),
                columnDefs=[
                    {"field": "Date Category", "sortable": True, "filter": True},
                    {"field": "name", "headerName": "File Name", "sortable": True, "filter": True, "flex": 1},
                    {"field": "time", "headerName": "Upload Time", "sortable": True, "filter": True},
                    {"field": "uploader", "headerName": "Uploader", "sortable": True, "filter": True},
                    {"field": "size", "headerName": "Size", "sortable": True},
                    {
                        "field": "action", 
                        "headerName": "Action", 
                        "cellStyle": {"color": "blue", "cursor": "pointer", "textDecoration": "underline", "fontWeight": "bold"}
                    }
                ],
                defaultColDef={"resizable": True},
                dashGridOptions={"pagination": True, "paginationPageSize": 20},
                csvExportParams={"fileName": "uploaded_files_list.csv"},
                className="ag-theme-alpine",
                style={"height": "650px"}
            )
            return grid
        return html.Div(f"Error fetching files: {response.text}", className="text-danger")
    except Exception as e:
        return html.Div(f"API Error: {str(e)}", className="text-danger")

@callback(
    Output("download-raw-file", "data"),
    Input("files-grid", "cellClicked"),
    State("auth-state", "data"),
    prevent_initial_call=True
)
def download_individual_file(cell_data, auth_state):
    if not cell_data or not auth_state:
        return dash.no_update
        
    if cell_data.get('colId') == 'action':
        row_data = cell_data.get('data', {})
        filename = row_data.get('name')
        if not filename:
            return dash.no_update
            
        token = auth_state.get("token")
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{API_BASE_URL}/download/{filename}", headers=headers)
            if response.status_code == 200:
                encoded = base64.b64encode(response.content).decode()
                return dict(content=encoded, filename=filename, base64=True)
        except:
            pass
            
    return dash.no_update

@callback(
    Output("files-grid", "exportDataAsCsv"),
    Input("btn-export-files", "n_clicks"),
    prevent_initial_call=True
)
def export_files_grid(n):
    if n:
        return True
    return False
