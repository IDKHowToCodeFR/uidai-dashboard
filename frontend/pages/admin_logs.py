import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import requests
from auth import API_BASE_URL

dash.register_page(__name__, path='/admin-logs', name='System Logs')

layout = html.Div([
    html.Div([
        html.Div([
            html.H5("System Logs", className="mb-0 fw-bold", style={"color": "var(--color-text-heading)"}),
            html.Div([
                dbc.Button("Load All Logs", id="btn-load-all-logs", color="primary", outline=True, size="sm", className="me-2"),
                dbc.Button(html.I(className="bi bi-arrow-clockwise"), id="btn-refresh-logs", color="primary", size="sm"),
            ])
        ], className="card-header d-flex justify-content-between align-items-center"),
        
        html.Div([
            html.Div(
                id="system-logs",
                className="bg-light text-dark p-3 rounded",
                style={
                    "height": "650px", 
                    "overflowY": "auto", 
                    "fontFamily": "monospace", 
                    "whiteSpace": "pre-wrap",
                    "border": "1px solid var(--color-border-light)",
                    "fontSize": "13px"
                }
            )
        ], className="card-body")
    ], className="custom-card mb-4"),
    
    # Hidden store to track if we should load all
    dcc.Store(id="store-load-all", data=False)
])

@callback(
    Output("store-load-all", "data"),
    Input("btn-load-all-logs", "n_clicks"),
    prevent_initial_call=True
)
def toggle_load_all(n):
    return True

@callback(
    Output("logs-terminal-container", "children"),
    Input("auth-state", "data"),
    Input("btn-refresh-logs", "n_clicks"),
    Input("store-load-all", "data")
)
def load_logs(auth_state, refresh_clicks, load_all):
    if not auth_state:
        return "Unauthorized"
    token = auth_state.get("token")
    if not token:
        return "Unauthorized"
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE_URL}/logs", headers=headers)
        if response.status_code == 200:
            logs = response.json()
            if not logs:
                return "> No logs available."
                
            # Sort chronological for terminal feel (oldest top, newest bottom)
            # Actually, main.py sorts descending (newest first). Let's keep it that way, or maybe ascending?
            # A terminal usually has the newest at the bottom.
            # main.py returns newest first. Let's reverse it to have newest at bottom.
            logs.reverse()
            
            if not load_all:
                logs = logs[-50:] # Keep last 50
                
            terminal_lines = []
            if not load_all and len(response.json()) > 50:
                terminal_lines.append(f"--- Showing last 50 logs of {len(response.json())}. Click 'Load All Logs' to see full history ---\n")
                
            for log in logs:
                ts = log.get("timestamp", "").replace("T", " ")[:19]
                action = log.get("action", "").ljust(20)
                user = log.get("username", "").ljust(15)
                details = log.get("details", "")
                line = f"[{ts}] {action} | {user} | {details}"
                terminal_lines.append(line)
                
            return "\n".join(terminal_lines)
            
        return f"Error fetching logs: {response.text}"
    except Exception as e:
        return f"API Error: {str(e)}"
