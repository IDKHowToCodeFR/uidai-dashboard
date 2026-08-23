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

dash.register_page(__name__, path='/unimate-dashboard', name='UniMate Dashboard')

layout = html.Div([
    html.Div([
        html.H3("UniMate Overview", className="display-xl mb-0"),
        html.P("Executive summary of UniMate call performance.", className="text-muted mb-4 mt-2"),
    ]),

    dbc.Row(id='unimate-kpi-row', className="mb-4 g-3"),

    dbc.Row([
        wrap_chart_card('unimate-volume', "Call Volume Over Time", "unimate")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-termination', "Termination Reasons", "unimate")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('unimate-language', "Calls by Language", "unimate")
        ], width=12, lg=6, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-intraday-language', "Intraday Language Distribution (Avg 30-min Buckets)", "unimate")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-term-language', "Termination Reasons by Language (100% Stacked)", "unimate")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('unimate-radar', "Language Performance Radar (Top 5)", "unimate")
        ], width=12, lg=6, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('unimate-kpi-row', 'children'),
    Output('unimate-volume-container', 'children'),
    Output('unimate-termination-container', 'children'),
    Output('unimate-language-container', 'children'),
    Output('unimate-intraday-language-container', 'children'),
    Output('unimate-term-language-container', 'children'),
    Output('unimate-radar-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_unimate_dashboard(data_ref, companies, languages, start_date, end_date, auth_state):
    empty_ui = render_empty_state()

    # Empty state for the KPI row
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

    if 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'], errors='coerce').dt.date
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

    auth_rate = 0
    if 'Authentication' in df.columns:
        auth_calls = df[df['Authentication'].astype(str).str.lower() == 'true'].shape[0]
        auth_rate = (auth_calls / total_calls * 100) if total_calls > 0 else 0

    system_term = 0
    if 'Termination Reason' in df.columns:
        sys_calls = df[df['Termination Reason'].astype(str).str.lower() == 'system'].shape[0]
        system_term = (sys_calls / total_calls * 100) if total_calls > 0 else 0

    avg_duration = 0
    if 'Call Duration' in df.columns:
        try:
            durations = pd.to_numeric(df['Call Duration'], errors='coerce')
            avg_duration = durations.mean() if not durations.isna().all() else 0
        except Exception:
            pass

    kpis = [
        dbc.Col(make_kpi_card("Total Calls", f"{total_calls:,}"), width=3),
        dbc.Col(make_kpi_card("Avg Duration (s)", f"{avg_duration:.1f}"), width=3),
        dbc.Col(make_kpi_card("Auth Rate", f"{auth_rate:.1f}%", "good" if auth_rate > 50 else "neutral"), width=3),
        dbc.Col(make_kpi_card("System Drops", f"{system_term:.1f}%", "bad" if system_term > 10 else "neutral"), width=3),
    ]

    # Volume Trend
    if not df['Date'].isna().all():
        vol_df = df.groupby('Date').size().reset_index(name='Calls')
        fig_vol = px.bar(vol_df, x='Date', y='Calls', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY])
        fig_vol.update_traces(hovertemplate='<b>Date:</b> %{x}<br><b>Calls:</b> %{y:,}<extra></extra>')
        fig_vol.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_vol.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        vol_ui = dcc.Graph(figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = empty_ui

    # Termination Chart
    if 'Termination Reason' in df.columns:
        term_df = df['Termination Reason'].value_counts().reset_index()
        term_df.columns = ['Reason', 'Count']
        fig_term = px.bar(term_df, x='Reason', y='Count', template='plotly_white')
        colors = [COLOR_DANGER if str(r).lower() in ['system', 'abandon'] else COLOR_NEUTRAL for r in term_df['Reason']]
        fig_term.update_traces(marker_color=colors, hovertemplate='<b>Reason:</b> %{x}<br><b>Count:</b> %{y:,}<extra></extra>')
        fig_term.update_layout(margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)')
        fig_term.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        term_ui = dcc.Graph(figure=fig_term, config={'displayModeBar': False})
    else:
        term_ui = empty_ui


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

    # 1. Intraday Language Distribution
    if 'Date' in df.columns and not df['Date'].isna().all() and 'Language' in df.columns:
        df['Time'] = pd.to_datetime(df['Call Start Time'], errors='coerce').dt.floor('30min').dt.time
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

    # 2. Language-wise Termination Breakdown (100% Stacked)
    if 'Language' in df.columns and 'Termination Reason' in df.columns:
        term_lang_df = df.groupby(['Language', 'Termination Reason']).size().reset_index(name='Count')
        lang_totals = term_lang_df.groupby('Language')['Count'].transform('sum')
        term_lang_df['Percentage'] = (term_lang_df['Count'] / lang_totals) * 100
        
        fig_term_lang = px.bar(term_lang_df, x='Language', y='Percentage', color='Termination Reason', hover_data=['Count'], template='plotly_white')
        
        color_map = {}
        for reason in term_lang_df['Termination Reason'].unique():
            rl = str(reason).lower()
            if rl in ['system', 'abandon']: color_map[reason] = COLOR_DANGER
            elif rl in ['agent disconnect', 'normal']: color_map[reason] = COLOR_SUCCESS
            elif rl in ['transfer', 'transferred']: color_map[reason] = COLOR_INFO
            else: color_map[reason] = COLOR_NEUTRAL
                
        fig_term_lang.for_each_trace(lambda t: t.update(marker_color=color_map.get(t.name, COLOR_NEUTRAL)))
        fig_term_lang.update_traces(hovertemplate='<b>%{x}</b><br>Reason: %{data.name}<br>Percentage: %{y:.1f}%<br>Count: %{customdata[0]:,}<extra></extra>')
        fig_term_lang.update_layout(barmode='stack', margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='rgba(0,0,0,0)', yaxis_title="% of Calls")
        fig_term_lang.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        term_lang_ui = dcc.Graph(figure=fig_term_lang, config={'displayModeBar': False})
    else:
        term_lang_ui = empty_ui

    # 3. Language Performance Radar
    if 'Language' in df.columns and 'Call Duration' in df.columns:
        top_langs = df['Language'].value_counts().nlargest(5).index
        radar_df = df[df['Language'].isin(top_langs)]
        
        def safe_mean(x):
            try: return pd.to_numeric(x, errors='coerce').mean()
            except: return 0
            
        radar_grp = radar_df.groupby('Language').agg(
            Volume=('Language', 'count'),
            Auth_True=('Authentication', lambda x: (x.astype(str).str.lower() == 'true').sum() if 'Authentication' in df.columns else 0),
            Sys_Drop=('Termination Reason', lambda x: (x.astype(str).str.lower() == 'system').sum() if 'Termination Reason' in df.columns else 0),
            Avg_Duration=('Call Duration', safe_mean)
        ).reset_index()
        
        radar_grp['Auth Rate'] = (radar_grp['Auth_True'] / radar_grp['Volume']) * 100
        radar_grp['Completion Rate'] = 100 - ((radar_grp['Sys_Drop'] / radar_grp['Volume']) * 100)
        radar_grp['Volume Share'] = (radar_grp['Volume'] / len(df)) * 100
        radar_grp['Duration Score'] = (300 / radar_grp['Avg_Duration'].replace(0, 1) * 100).clip(upper=100)
        
        categories = ['Volume Share', 'Auth Rate', 'Completion Rate', 'Duration Score']
        categories_closed = categories + [categories[0]]
        
        fig_radar = go.Figure()
        colors = [COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO]
        for i, row in radar_grp.iterrows():
            r_vals = [row['Volume Share'], row['Auth Rate'], row['Completion Rate'], row['Duration Score']]
            r_vals_closed = r_vals + [r_vals[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=r_vals_closed,
                theta=categories_closed, fill='toself', name=row['Language'], line_color=colors[i % len(colors)], opacity=0.6
            ))
            
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, template='plotly_white', margin=dict(t=40, b=40, l=90, r=90))
        radar_ui = dcc.Graph(figure=fig_radar, config={'displayModeBar': False})
    else:
        radar_ui = empty_ui

    return kpis, vol_ui, term_ui, lang_ui, intra_lang_ui, term_lang_ui, radar_ui
