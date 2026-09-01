import dash
from dash import html, dcc, callback, Input, Output, State
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import COLOR_PRIMARY, COLOR_DANGER
from frontend.components.empty_state import render_empty_state

dash.register_page(__name__, path='/apr/agent-performance', name='Agent Performance')

layout = html.Div([
    html.Div([
        html.H3("Agent Performance Rankings", className="display-xl mb-0"),
        html.P("Top 20 and Bottom 20 agents by composite performance score.", className="text-muted mb-4 mt-2"),
        dbc.Alert([
            html.H5([html.I(className="bi bi-info-circle me-2"), " Performance Score Formula"], className="alert-heading"),
            html.P("The composite score evaluates agents based on three key metrics: Calls Per Hour (CPH), Occupancy, and Average Handle Time (AHT)."),
            html.Hr(),
            html.Div([
                html.Strong("Score = "),
                html.Code("(CPH / 15) * 40 + (Occupancy / 100) * 30 + (240 / AHT) * 30", className="bg-white p-1 rounded text-primary border")
            ], className="mb-0")
        ], color="info", className="shadow-sm mb-4 rounded-3")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=html.Div(id='apr-ranking-content'))
], className="container-fluid py-4")

def format_seconds(seconds):
    if pd.isna(seconds): return "00:00:00"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def hhmmss_to_seconds(time_str):
    if pd.isna(time_str):
        return 0
    try:
        parts = str(time_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    except:
        return 0

@callback(
    Output('apr-ranking-content', 'children'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    State('auth-state', 'data')
)
def update_agent_rankings(companies, languages, auth_state):
    empty_ui = render_empty_state()
    
    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_ui

    # Note: Currently impersonate is not available in agent_performance view directly,
    # but we can pass it if we add it to the state.
    from frontend.shared.api_client import api_get
    try:
        response = api_get('dashboards/apr/agents', token=token)
        agents = response.json()
    except Exception:
        return empty_ui
        
    if not agents or isinstance(agents, dict):
        return empty_ui

    df = pd.DataFrame(agents)
    
    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]
    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if df.empty:
        return empty_ui
        
    # Exclude agents with less than 20 staffed hours (72000 seconds)
    # The user asked to make sure "some new person might have less calls which will show them bad so make it time depened too"
    df = df[df['Total Staffed Time Sec'] >= 72000]
    
    if df.empty:
        return html.Div([
            html.H4("No agents found with at least 20 hours of staffed time.", className="text-center text-muted mt-5")
        ])

    df['Calls Per Hour'] = np.where(df['Total Staffed Time Sec'] > 0, df['Total ACD Calls'] / (df['Total Staffed Time Sec'] / 3600), 0)
    df['AHT (sec)'] = np.where(df['Total ACD Calls'] > 0, (df['Total ACD Time Sec'] + df['Total ACW Time Sec']) / df['Total ACD Calls'], 0)
    df['AHT'] = df['AHT (sec)'].apply(format_seconds)
    
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    df[numeric_cols] = df[numeric_cols].round(2)
    
    display_cols = ['Login ID', 'Agent Name', 'Score', 'Total ACD Calls', 'Calls Per Hour', 'Occupancy %', 'AHT']

    tables = []
    for company in df['Company'].unique():
        company_df = df[df['Company'] == company].sort_values('Score', ascending=False)
        top_20 = company_df.head(20).to_dict('records')
        bottom_20 = company_df.tail(20).sort_values('Score', ascending=True).to_dict('records')

        tables.append(html.Div([
            html.H4(f"{company} - Top 20 Best Performing Agents", className="mt-4 mb-3 text-success"),
            dag.AgGrid(
                rowData=top_20,
                columnDefs=[{"field": i} for i in display_cols],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                className="ag-theme-alpine",
                dashGridOptions={"pagination": True, "paginationPageSize": 10, "paginationPageSizeSelector": [10, 20, 50, 100], "domLayout": "autoHeight"},
                style={"width": "100%"}
            ),
            html.H4(f"{company} - Top 20 Worst Performing Agents (Needs Improvement)", className="mt-5 mb-3 text-danger"),
            dag.AgGrid(
                rowData=bottom_20,
                columnDefs=[{"field": i} for i in display_cols],
                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                className="ag-theme-alpine",
                dashGridOptions={"pagination": True, "paginationPageSize": 10, "paginationPageSizeSelector": [10, 20, 50, 100], "domLayout": "autoHeight"},
                style={"width": "100%"}
            )
        ], className="card p-4 shadow-sm mb-4"))

    return html.Div(tables)
