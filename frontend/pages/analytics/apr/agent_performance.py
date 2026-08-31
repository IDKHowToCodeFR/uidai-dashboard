import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
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
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=html.Div(id='apr-ranking-content'))
], className="container-fluid py-4")

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
        
    if not agents:
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

    df['Calls Per Hour'] = np.where(df['Total Staffed Time Sec'] > 0, df['Total ACD Calls'] / (df['Total Staffed Time Sec'] / 3600), 0).round(1)
    df['AHT (sec)'] = np.where(df['Total ACD Calls'] > 0, (df['Total ACD Time Sec'] + df['Total ACW Time Sec']) / df['Total ACD Calls'], 0).round(0)
    
    display_cols = ['Company', 'Agent Name', 'Login ID', 'Total ACD Calls', 'Calls Per Hour', 'Occupancy %', 'AHT (sec)', 'Score']

    tables = []
    for company in df['Company'].unique():
        company_df = df[df['Company'] == company].sort_values('Score', ascending=False)
        top_20 = company_df.head(20).to_dict('records')
        bottom_20 = company_df.tail(20).sort_values('Score', ascending=True).to_dict('records')

        tables.append(html.Div([
            html.H4(f"{company} - Top 20 Best Performing Agents", className="mt-4 mb-3 text-success"),
            dash_table.DataTable(
                data=top_20,
                columns=[{"name": i, "id": i} for i in display_cols],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
            ),
            html.H4(f"{company} - Top 20 Worst Performing Agents (Needs Improvement)", className="mt-5 mb-3 text-danger"),
            dash_table.DataTable(
                data=bottom_20,
                columns=[{"name": i, "id": i} for i in display_cols],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
            )
        ], className="card p-4 shadow-sm mb-4"))

    return html.Div(tables)
