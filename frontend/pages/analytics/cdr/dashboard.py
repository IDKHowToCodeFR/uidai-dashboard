import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO

from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state

dash.register_page(__name__, path='/cdr/dashboard', name='CDR Dashboard')

layout = html.Div([
    html.Div([
        html.H3("CDR Overview", className="display-xl mb-0"),
        html.P("Executive summary of CDR call performance.", className="text-muted mb-4 mt-2"),
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='cdr-kpi-row', className="mb-4 g-3")),

    dbc.Row([
        wrap_chart_card('cdr-volume', "Call Volume Over Time", "cdr")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-breakdown', "Talktime vs Hold Time vs ACW (Average Seconds)", "cdr")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('cdr-language', "Calls by Language", "cdr")
        ], width=12, lg=6, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-intraday-language', "Intraday Language Distribution (Avg 30-min Buckets)", "cdr")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-transfer-language', "Transfer Rate by Language", "cdr")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('cdr-talktime-language', "Average Talktime by Language (Seconds)", "cdr")
        ], width=12, lg=6, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('cdr-kpi-row', 'children'),
    Output('cdr-volume-container', 'children'),
    Output('cdr-breakdown-container', 'children'),
    Output('cdr-language-container', 'children'),
    Output('cdr-intraday-language-container', 'children'),
    Output('cdr-transfer-language-container', 'children'),
    Output('cdr-talktime-language-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('sl-granularity', 'value'),
    Input('sl-scale-toggle', 'value'),
    State('auth-state', 'data')
)
def update_cdr_dashboard(data_ref, companies, languages, start_date, end_date, sl_granularity, sl_scale, auth_state):
    empty_ui = render_empty_state()
    empty_kpi = dbc.Col(html.Div(empty_ui, style={"height": "120px"}), width=12)

    if not data_ref or 'filename' not in data_ref:
        return empty_kpi, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui

    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_kpi, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui

    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))

    if df is None or df.empty:
        return empty_kpi, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]

    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if 'segstart' in df.columns:
        # segstart format is dd-mm-YYYY HH:MM:SS
        df['Date'] = pd.to_datetime(df['segstart'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.date
        if df['Date'].isna().all():
            df['Date'] = pd.to_datetime(df['segstart'], errors='coerce').dt.date
    else:
        df['Date'] = pd.NaT

    if start_date and end_date:
        valid_mask = df['Date'].notna()
        df = df[valid_mask]
        if not df.empty:
            df = df[(df['Date'] >= pd.to_datetime(start_date).date()) & (df['Date'] <= pd.to_datetime(end_date).date())]

    if df.empty:
        return empty_kpi, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui, empty_ui

    # KPIs
    total_calls = len(df)
    
    avg_talk = df['talktime'].mean() if 'talktime' in df.columns else 0
    avg_hold = df['ansholdtime'].mean() if 'ansholdtime' in df.columns else 0
    
    transfer_rate = 0
    if 'transferred' in df.columns:
        transferred_calls = df[df['transferred'].astype(int) == 1].shape[0]
        transfer_rate = (transferred_calls / total_calls * 100) if total_calls > 0 else 0

    kpis = [
        dbc.Col(make_kpi_card("Total Calls", f"{total_calls:,}"), width=True),
        dbc.Col(make_kpi_card("Avg Speed to Answer", f"{avg_hold:.1f}s", "bad" if avg_hold > 30 else "neutral"), width=True),
        dbc.Col(make_kpi_card("Avg Talk Time", f"{avg_talk:.1f}s"), width=True),
        dbc.Col(make_kpi_card("Transfer Rate", f"{transfer_rate:.1f}%", "good" if transfer_rate < 10 else "neutral"), width=True),
    ]

    # Volume Trend
    if not df['Date'].isna().all():
        if sl_granularity and sl_granularity != 'Auto':
            freq = sl_granularity
        else:
            days_diff = (df['Date'].max() - df['Date'].min()).days if not df['Date'].empty else 0
            freq = 'M' if days_diff > 90 else ('W-MON' if days_diff > 31 else 'D')
            
        df['Date_Bucket'] = pd.to_datetime(df['Date'])
        if freq != 'D':
            df['Date_Bucket'] = df['Date_Bucket'].dt.to_period(freq).dt.to_timestamp()
            
        vol_df = df.groupby(df['Date_Bucket'].dt.date).size().reset_index(name='Calls')
        vol_df.rename(columns={'Date_Bucket': 'Date'}, inplace=True)
        fig_vol = px.bar(vol_df, x='Date', y='Calls', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY])
        fig_vol.update_traces(hovertemplate='<b>Date:</b> %{x}<br><b>Calls:</b> %{y:,}<extra></extra>')
        fig_vol.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_vol.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        vol_ui = dcc.Graph(figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = empty_ui

    # Talktime vs Hold Time vs ACW Stacked Bar
    metrics_to_chart = ['talktime', 'ansholdtime', 'acwtime']
    if all(m in df.columns for m in metrics_to_chart):
        avg_metrics = df[metrics_to_chart].mean().reset_index()
        avg_metrics.columns = ['Metric', 'Seconds']
        
        # Friendly names
        name_map = {'talktime': 'Talk Time', 'ansholdtime': 'Hold Time', 'acwtime': 'ACW Time'}
        avg_metrics['Metric'] = avg_metrics['Metric'].map(name_map)
        
        fig_breakdown = px.bar(avg_metrics, x='Metric', y='Seconds', template='plotly_white')
        colors = [COLOR_PRIMARY, COLOR_WARNING, COLOR_NEUTRAL]
        fig_breakdown.update_traces(marker_color=colors, hovertemplate='<b>%{x}:</b> %{y:.1f}s<extra></extra>')
        fig_breakdown.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_breakdown.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        breakdown_ui = dcc.Graph(figure=fig_breakdown, config={'displayModeBar': False})
    else:
        breakdown_ui = empty_ui

    # Language Donut Chart
    if 'Language' in df.columns:
        lang_df = df['Language'].value_counts().reset_index()
        lang_df.columns = ['Language', 'Count']
        fig_lang = px.pie(lang_df, names='Language', values='Count', template='plotly_white', hole=0.6,
                         color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Count: %{value:,}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_lang.update_layout(margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        lang_ui = dcc.Graph(figure=fig_lang, config={'displayModeBar': False})
    else:
        lang_ui = empty_ui

    # Intraday Language Distribution (line chart)
    if 'Date' in df.columns and not df['Date'].isna().all() and 'Language' in df.columns and 'segstart' in df.columns:
        df['Time'] = pd.to_datetime(df['segstart'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.floor('30min').dt.time
        if df['Time'].isna().all():
            df['Time'] = pd.to_datetime(df['segstart'], errors='coerce').dt.floor('30min').dt.time
            
        df['True_Day'] = df['Date']
        intra_grp = df.groupby(['True_Day', 'Time', 'Language']).size().reset_index(name='Calls')
        avg_intra = intra_grp.groupby(['Time', 'Language'])['Calls'].mean().reset_index()
        avg_intra['Calls'] = avg_intra['Calls'].round().astype(int)
        avg_intra['TimeStr'] = avg_intra['Time'].astype(str).str[:5]
        avg_intra = avg_intra.sort_values(['TimeStr', 'Language'])
        
        fig_intra = px.line(avg_intra, x='TimeStr', y='Calls', color='Language', template='plotly_white', color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_intra.update_traces(mode='lines', line_shape='spline', hovertemplate='<b>Time:</b> %{x}<br><b>Language:</b> %{data.name}<br><b>Calls:</b> %{y:d}<extra></extra>')
        fig_intra.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title="Time of Day", yaxis_title="Average Volume")
        fig_intra.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        intra_lang_ui = dcc.Graph(figure=fig_intra, config={'displayModeBar': False})
    else:
        intra_lang_ui = empty_ui

    # Transfer Rate by Language
    if 'Language' in df.columns and 'transferred' in df.columns:
        transfer_lang = df.groupby('Language')['transferred'].mean().reset_index()
        transfer_lang['Transfer Rate %'] = transfer_lang['transferred'] * 100
        transfer_lang = transfer_lang.sort_values(by='Transfer Rate %', ascending=False)
        
        fig_trans_lang = px.bar(transfer_lang, x='Language', y='Transfer Rate %', template='plotly_white', color_discrete_sequence=[COLOR_WARNING])
        fig_trans_lang.update_traces(hovertemplate='<b>%{x}</b><br>Transfer Rate: %{y:.1f}%<extra></extra>')
        fig_trans_lang.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_trans_lang.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        transfer_lang_ui = dcc.Graph(figure=fig_trans_lang, config={'displayModeBar': False})
    else:
        transfer_lang_ui = empty_ui

    # Avg Talktime by Language
    if 'Language' in df.columns and 'talktime' in df.columns:
        talk_lang = df.groupby('Language')['talktime'].mean().reset_index()
        talk_lang.columns = ['Language', 'Avg Talktime']
        talk_lang = talk_lang.sort_values(by='Avg Talktime', ascending=False)
        
        fig_talk_lang = px.bar(talk_lang, x='Language', y='Avg Talktime', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY])
        fig_talk_lang.update_traces(hovertemplate='<b>%{x}</b><br>Avg Talktime: %{y:.1f}s<extra></extra>')
        fig_talk_lang.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_talk_lang.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        talk_lang_ui = dcc.Graph(figure=fig_talk_lang, config={'displayModeBar': False})
    else:
        talk_lang_ui = empty_ui

    return kpis, vol_ui, breakdown_ui, lang_ui, intra_lang_ui, transfer_lang_ui, talk_lang_ui
