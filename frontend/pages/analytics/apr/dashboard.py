import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import COLOR_PRIMARY, COLOR_WARNING, COLOR_NEUTRAL

from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state

dash.register_page(__name__, path='/apr/dashboard', name='APR Dashboard')

layout = html.Div([
    html.Div([
        html.H3("APR Analytics Overview", className="display-xl mb-0"),
        html.P("Executive summary of Agent Performance Reports.", className="text-muted mb-4 mt-2"),
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='apr-kpi-row', className="mb-4 g-3")),

    dbc.Row([
        wrap_chart_card('apr-volume', "ACD Calls Over Time", "apr")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('apr-occupancy', "Agent Occupancy with ACW (Average %)", "apr")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('apr-aht', "Average Handle Time (ACD + ACW Seconds)", "apr")
        ], width=12, lg=6, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('apr-kpi-row', 'children'),
    Output('apr-volume-container', 'children'),
    Output('apr-occupancy-container', 'children'),
    Output('apr-aht-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_apr_dashboard(data_ref, companies, languages, start_date, end_date, auth_state):
    empty_ui = render_empty_state()
    empty_kpi = dbc.Col(html.Div(empty_ui, style={"height": "120px"}), width=12)

    if not data_ref or 'filename' not in data_ref:
        return empty_kpi, empty_ui, empty_ui, empty_ui

    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_kpi, empty_ui, empty_ui, empty_ui

    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))

    if df is None or df.empty:
        return empty_kpi, empty_ui, empty_ui, empty_ui

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]

    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date

    if start_date and end_date:
        valid_mask = df['Date'].notna()
        df = df[valid_mask]
        if not df.empty:
            df = df[(df['Date'] >= pd.to_datetime(start_date).date()) & (df['Date'] <= pd.to_datetime(end_date).date())]

    if df.empty:
        return empty_kpi, empty_ui, empty_ui, empty_ui

    total_acd_calls = df['ACD Calls'].sum() if 'ACD Calls' in df.columns else 0
    avg_occ = df['% Agent Occupancy with ACW'].mean() if '% Agent Occupancy with ACW' in df.columns else 0
    
    df['aht'] = df['Avg ACD Time'] + df['Avg ACW Time'] if 'Avg ACD Time' in df.columns and 'Avg ACW Time' in df.columns else 0
    avg_aht = df['aht'].mean() if 'aht' in df.columns else 0
    
    kpis = [
        dbc.Col(make_kpi_card("Total ACD Calls", f"{total_acd_calls:,}"), width=4),
        dbc.Col(make_kpi_card("Avg Occupancy", f"{avg_occ:.1f}%", "good" if avg_occ > 70 else "neutral"), width=4),
        dbc.Col(make_kpi_card("Avg Handle Time", f"{avg_aht:.0f}s", "bad" if avg_aht > 240 else "good"), width=4),
    ]

    if not df['Date'].isna().all() and 'ACD Calls' in df.columns:
        vol_df = df.groupby('Date')['ACD Calls'].sum().reset_index()
        fig_vol = px.bar(vol_df, x='Date', y='ACD Calls', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY])
        fig_vol.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        vol_ui = dcc.Graph(figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = empty_ui

    if not df['Date'].isna().all() and '% Agent Occupancy with ACW' in df.columns:
        occ_df = df.groupby('Date')['% Agent Occupancy with ACW'].mean().reset_index()
        fig_occ = px.line(occ_df, x='Date', y='% Agent Occupancy with ACW', template='plotly_white', color_discrete_sequence=[COLOR_WARNING])
        fig_occ.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        occ_ui = dcc.Graph(figure=fig_occ, config={'displayModeBar': False})
    else:
        occ_ui = empty_ui
        
    if not df['Date'].isna().all() and 'aht' in df.columns:
        aht_df = df.groupby('Date')['aht'].mean().reset_index()
        fig_aht = px.line(aht_df, x='Date', y='aht', template='plotly_white', color_discrete_sequence=[COLOR_NEUTRAL])
        fig_aht.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        aht_ui = dcc.Graph(figure=fig_aht, config={'displayModeBar': False})
    else:
        aht_ui = empty_ui

    return kpis, vol_ui, occ_ui, aht_ui
