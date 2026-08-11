import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from frontend.shared.api_client import api_client

dash.register_page(__name__, path='/admin-logs', name='System Logs')

# Styling for Action Badges
action_cell_style = {
    "styleConditions": [
        {
            "condition": "params.value.includes('SUCCESS')", 
            "style": {"color": "#0f5132", "backgroundColor": "#d1e7dd", "fontWeight": "bold"}
        },
        {
            "condition": "params.value.includes('DEACTIVATED') || params.value.includes('FAIL')", 
            "style": {"color": "#842029", "backgroundColor": "#f8d7da", "fontWeight": "bold"}
        },
        {
            "condition": "params.value.includes('UPDATED')", 
            "style": {"color": "#084298", "backgroundColor": "#cfe2ff", "fontWeight": "bold"}
        },
        {
            "condition": "params.value.includes('LOADED') || params.value.includes('ADDED')", 
            "style": {"color": "#664d03", "backgroundColor": "#fff3cd", "fontWeight": "bold"}
        }
    ]
}

columnDefs = [
    {"field": "timestamp", "headerName": "Timestamp", "sortable": True, "filter": "agDateColumnFilter", "width": 220},
    {"field": "username", "headerName": "Username", "sortable": True, "filter": True, "width": 150},
    {"field": "action", "headerName": "Action", "sortable": True, "filter": True, "cellStyle": action_cell_style, "width": 220},
    {"field": "details", "headerName": "Details", "sortable": True, "filter": True, "flex": 1, "wrapText": True, "autoHeight": True}
]

layout = html.Div([
    html.Div([
        html.Div([
            html.H3("System Logs", className="display-xl mb-0"),
            html.P("View, sort, and filter audit and system events.", className="text-muted mb-0 mt-2"),
        ]),
        html.Div([
            dcc.DatePickerRange(
                id='logs-date-picker',
                display_format='YYYY-MM-DD',
                clearable=True,
                className="me-3"
            ),
            dbc.Button("Export CSV", id="btn-export-logs", color="success", outline=True, size="sm", className="me-2"),
            dbc.Button("Load All Logs", id="btn-load-all-logs", color="primary", outline=True, size="sm", className="me-2"),
            dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-logs", color="primary", size="sm"),
        ], className="d-flex align-items-center")
    ], className="d-flex justify-content-between align-items-center mb-4"),
    
    html.Div([
        dag.AgGrid(
            id="system-logs-grid",
            columnDefs=columnDefs,
            rowData=[],
            dashGridOptions={
                "pagination": True,
                "paginationPageSize": 20,
                "rowHeight": 40,
                "domLayout": "autoHeight"
            },
            className="ag-theme-alpine",
            style={"height": "650px", "width": "100%"}
        )
    ], className="custom-card shadow-sm bg-white p-4", style={"borderRadius": "16px", "border": "1px solid #e2e8f0"}),
    
    dcc.Store(id="store-load-all", data=False),
    html.Div(id="logs-error-msg", className="text-danger mt-2")
], className="container-fluid py-4")

@callback(
    Output("store-load-all", "data"),
    Input("btn-load-all-logs", "n_clicks"),
    prevent_initial_call=True
)
def toggle_load_all(n):
    return True

@callback(
    Output("system-logs-grid", "exportDataAsCsv"),
    Input("btn-export-logs", "n_clicks"),
    prevent_initial_call=True
)
def export_logs_csv(n_clicks):
    if n_clicks:
        return True
    return False

@callback(
    Output("system-logs-grid", "rowData"),
    Output("logs-error-msg", "children"),
    Input("auth-state", "data"),
    Input("btn-refresh-logs", "n_clicks"),
    Input("store-load-all", "data"),
    Input("logs-date-picker", "start_date"),
    Input("logs-date-picker", "end_date")
)
def fetch_and_populate_logs(auth_state, refresh_clicks, load_all, start_date, end_date):
    if not auth_state:
        return no_update, "Unauthorized"
        
    token = auth_state.get("token")
    if not token:
        return no_update, "Unauthorized"
        
    try:
        response = api_client.get_logs(token)
        
        if response.status_code == 200:
            logs = response.json()
            if not logs:
                return [], ""
                
            # Backend already returns newest first.
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Format timestamp for better readability
            for log in logs:
                raw_ts = log.get("timestamp", "")
                log["timestamp"] = raw_ts.replace("T", " ")[:19]
            
            if start_date and end_date:
                import pandas as pd
                start_dt = pd.to_datetime(start_date).date()
                end_dt = pd.to_datetime(end_date).date()
                filtered_logs = []
                for log in logs:
                    try:
                        log_dt = pd.to_datetime(log["timestamp"]).date()
                        if start_dt <= log_dt <= end_dt:
                            filtered_logs.append(log)
                    except Exception:
                        pass
                logs = filtered_logs
                
            if not load_all:
                logs = logs[:50] # Keep only latest 50 for performance if not load_all
                
            return logs, ""
            
        return no_update, f"Error fetching logs: {response.text}"
    except Exception as e:
        return no_update, f"API Error: {str(e)}"
