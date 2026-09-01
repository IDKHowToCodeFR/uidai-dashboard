import dash
from dash import html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import pandas as pd
import numpy as np
from frontend.shared.api_client import api_get

dash.register_page(__name__, path='/apr/agent_explorer', name='Agent Explorer')

layout = html.Div([
    html.Div([
        html.H3("Agent Explorer", className="display-xl mb-0"),
        html.P("View, sort, and filter all agents and their aggregate performance metrics.", className="text-muted mb-4 mt-2"),
    ]),
    html.Div(
        id='apr-agent-explorer-table',
        className="custom-card shadow-sm bg-white p-4",
        style={"borderRadius": "16px", "border": "1px solid #e2e8f0"}
    )
], className="container-fluid py-4")

@callback(
    Output('apr-agent-explorer-table', 'children'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    State('auth-state', 'data')
)
def update_agent_explorer(companies, languages, auth_state):
    if not auth_state or not auth_state.get('token'):
        return html.Div("Unauthorized.", className="text-center p-5 text-muted")

    try:
        response = api_get('dashboards/apr/agents', token=auth_state['token'])
        agents = response.json()
    except Exception:
        return html.Div("Error fetching agents.", className="text-center p-5 text-muted")

    if not agents or isinstance(agents, dict):
        return html.Div("No agents found or unauthorized.", className="text-center p-5 text-muted")

    df = pd.DataFrame(agents)

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]
    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if df.empty:
        return html.Div("No agents match filters.", className="text-center p-5 text-muted")
        
    df = df.sort_values('Score', ascending=False)
    
    def format_seconds(seconds):
        if pd.isna(seconds): return "00:00:00"
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    df['Staffed Time'] = df['Total Staffed Time Sec'].apply(format_seconds)
    df['ACD Time'] = df['Total ACD Time Sec'].apply(format_seconds)
    df['ACW Time'] = df['Total ACW Time Sec'].apply(format_seconds)
    
    # Calculate AHT and CPH for explorer as well
    df['Calls Per Hour'] = np.where(df['Total Staffed Time Sec'] > 0, df['Total ACD Calls'] / (df['Total Staffed Time Sec'] / 3600), 0).round(1)
    df['AHT (sec)'] = np.where(df['Total ACD Calls'] > 0, (df['Total ACD Time Sec'] + df['Total ACW Time Sec']) / df['Total ACD Calls'], 0).round(0)
    df['AHT'] = df['AHT (sec)'].apply(format_seconds)
    
    display_cols = [
        'Login ID', 'Agent Name', 'Score', 'Total ACD Calls', 'Calls Per Hour', 
        'Occupancy %', 'AHT', 'Staffed Time', 'ACD Time', 'ACW Time', 'Language'
    ]

    # Round numerical columns
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    df[numeric_cols] = df[numeric_cols].round(2)

    return dag.AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=[{"field": i} for i in display_cols],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        dashGridOptions={"pagination": True, "paginationPageSize": 50},
        style={"height": "600px", "width": "100%"}
    )
