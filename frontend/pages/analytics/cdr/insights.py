import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import get_plotly_template, make_export_dropdown, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.components.cards import wrap_chart_card, make_kpi_card
from frontend.components.empty_state import render_empty_state
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

dash.register_page(__name__, path='/cdr/insights', name='CDR Insights')

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3("Operational Insights", className="display-xl mb-0"),
                html.P("Deep dive into CDR call durations, hold time correlations, and intraday volume.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        dbc.Col([
            html.Div([
                make_export_dropdown("cdr-insights"),
                dcc.Download(id={'type': 'download-data-cdr-insights', 'index': 'cdr-insights'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='cdr-insights-kpi', className="mb-4 g-3")),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-insights-histogram', "Call Talk Time Distribution (s)", "cdr-insights")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-insights-hold', "Hold & ACW Time by Hour", "cdr-insights")
        ], width=12, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('cdr-insights-kpi', 'children'),
    Output('cdr-insights-histogram-container', 'children'),
    Output('cdr-insights-hold-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_cdr_insights(data_ref, companies, languages, start_date, end_date, auth_state):
    def e_ui(gid=None):
        return render_empty_state(graph_id=gid)

    empty_kpi = dbc.Col(html.Div(e_ui(), style={"height": "120px"}), width=12)
    outs = [empty_kpi] + [e_ui(gid) for gid in ['cdr-insights-histogram', 'cdr-insights-hold']]

    if not data_ref or 'filename' not in data_ref: return outs
    token = auth_state.get('token') if auth_state else None
    if not token: return outs
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df is None or df.empty: return outs

    if 'segstart' in df.columns:
        df['Date'] = pd.to_datetime(df['segstart'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
        if df['Date'].isna().all():
            df['Date'] = pd.to_datetime(df['segstart'], errors='coerce')
    else:
        df['Date'] = pd.NaT

    mask = pd.Series(True, index=df.index)
    if companies and 'Company' in df.columns:
        mask = mask & df['Company'].isin(companies)
    if languages and 'Language' in df.columns:
        mask = mask & df['Language'].isin(languages)

    if start_date and end_date and not df['Date'].isna().all():
        s = pd.to_datetime(start_date)
        e = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        mask = mask & (df['Date'] >= s) & (df['Date'] < e)

    df = df[mask].copy()
    if df.empty: return outs
    
    total_calls = len(df)
    
    if 'acwtime' in df.columns: df['acwtime'] = pd.to_numeric(df['acwtime'], errors='coerce')
    if 'ansholdtime' in df.columns: df['ansholdtime'] = pd.to_numeric(df['ansholdtime'], errors='coerce')
    if 'talktime' in df.columns: df['talktime'] = pd.to_numeric(df['talktime'], errors='coerce')

    avg_acw = df['acwtime'].mean() if 'acwtime' in df.columns else 0
    avg_hold = df['ansholdtime'].mean() if 'ansholdtime' in df.columns else 0
    
    kpis = [
        dbc.Col(make_kpi_card("Avg ACW Time", f"{avg_acw:.1f}s"), width=True),
        dbc.Col(make_kpi_card("Avg Hold Time", f"{avg_hold:.1f}s"), width=True),
    ]

    # Histogram: Call Talk Time Distribution
    if 'talktime' in df.columns:
        fig_hist = px.histogram(df, x="talktime", nbins=20, template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY])
        fig_hist.update_layout(margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Talk Time (s)", yaxis_title="Call Count", bargap=0.1)
        
        counts, edges = np.histogram(df['talktime'].dropna(), bins=20)
        if len(counts) > 0:
            fig_hist.update_yaxes(type="log")
            
        hist_ui = dcc.Graph(id='cdr-insights-histogram', figure=fig_hist, config={'displayModeBar': False})
    else:
        hist_ui = e_ui('cdr-insights-histogram')

    # Correlation Heatmap: Wait/Hold Time by Hour
    if not df['Date'].isna().all() and 'ansholdtime' in df.columns:
        df['Hour'] = df['Date'].dt.hour
        hour_grp = df.groupby('Hour').agg(
            Avg_Hold=('ansholdtime', 'mean'),
            Avg_ACW=('acwtime', 'mean') if 'acwtime' in df.columns else ('ansholdtime', lambda x: 0)
        ).reset_index()
        
        if not hour_grp.empty:
            hour_grp = hour_grp.set_index('Hour')
            for h in range(24):
                if h not in hour_grp.index:
                    hour_grp.loc[h] = [0, 0]
            hour_grp = hour_grp.sort_index().reset_index()
            hour_grp['Time'] = hour_grp['Hour'].apply(lambda x: f"{int(x):02d}:00")
            
            fig_hold = go.Figure()
            fig_hold.add_trace(go.Scatter(x=hour_grp['Time'], y=hour_grp['Avg_Hold'], mode='lines+markers', name='Avg Hold Time (s)', line=dict(color=COLOR_WARNING, width=3)))
            fig_hold.add_trace(go.Scatter(x=hour_grp['Time'], y=hour_grp['Avg_ACW'], mode='lines+markers', name='Avg ACW Time (s)', line=dict(color=COLOR_SUCCESS, width=3)))
            
            fig_hold.update_layout(
                template=get_plotly_template(), 
                margin=dict(t=10, b=10, l=10, r=10), 
                xaxis_title="Hour of Day", 
                yaxis_title="Average Seconds",
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            hold_ui = dcc.Graph(id='cdr-insights-hold', figure=fig_hold, config={'displayModeBar': False})
        else:
            hold_ui = e_ui('cdr-insights-hold')
    else:
        hold_ui = e_ui('cdr-insights-hold')

    return kpis, hist_ui, hold_ui


# ---------------- EXPORT CALLBACKS ----------------
@callback(
    Output({'type': 'download-data-cdr-insights', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-cdr-insights', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-insights-histogram', 'figure'),
    State('cdr-insights-hold', 'figure'),
    prevent_initial_call=True
)
def export_pdf(n_clicks, hist, hold):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-insights-histogram': hist, 'cdr-insights-hold': hold}
    
    if index == 'cdr-insights':
        pdf_bytes = generate_dashboard_pdf(figures, "CDR Insights")
        return dcc.send_bytes(pdf_bytes, "cdr_insights.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")

@callback(
    Output({'type': 'download-data-cdr-insights', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-cdr-insights', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-insights-histogram', 'figure'),
    State('cdr-insights-hold', 'figure'),
    prevent_initial_call=True
)
def export_png(n_clicks, hist, hold):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-insights-histogram': hist, 'cdr-insights-hold': hold}
    
    if index == 'cdr-insights':
        pdf_bytes = generate_dashboard_pdf(figures, "CDR Insights")
        return dcc.send_bytes(pdf_bytes, "cdr_insights.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-cdr-insights', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-cdr-insights', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-insights-histogram', 'figure'),
    State('cdr-insights-hold', 'figure'),
    prevent_initial_call=True
)
def export_html(n_clicks, hist, hold):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-insights-histogram': hist, 'cdr-insights-hold': hold}
    
    if index == 'cdr-insights':
        html_str = generate_dashboard_html(figures, "CDR Insights")
        return dcc.send_string(html_str, "cdr_insights.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
