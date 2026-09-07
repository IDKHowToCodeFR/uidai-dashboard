import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import get_plotly_template, make_export_dropdown, should_use_log, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.components.cards import wrap_chart_card, make_kpi_card
from frontend.components.empty_state import render_empty_state
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

dash.register_page(__name__, path='/cdr/agent-performance', name='CDR Agent Performance')

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3("Agent Performance", className="display-xl mb-0"),
                html.P("Analyze agent-level metrics, call handling times, and transfer rates.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        dbc.Col([
            html.Div([
                make_export_dropdown("cdr-agent"),
                dcc.Download(id={'type': 'download-data-cdr-agent', 'index': 'cdr-agent'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='cdr-agent-kpi', className="mb-4 g-3")),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-agent-volume', "Top 10 Agents by Call Volume", "cdr-agent")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('cdr-agent-transfer', "Top 10 Agents by Transfer Rate (%)", "cdr-agent")
        ], width=12, lg=6, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('cdr-agent-scatter', "Talktime vs Hold Time per Agent", "cdr-agent")
        ], width=12, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('cdr-agent-kpi', 'children'),
    Output('cdr-agent-volume-container', 'children'),
    Output('cdr-agent-transfer-container', 'children'),
    Output('cdr-agent-scatter-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_agent_performance(data_ref, companies, languages, start_date, end_date, auth_state):
    def e_ui(gid=None):
        return render_empty_state(graph_id=gid)

    empty_kpi = dbc.Col(html.Div(e_ui(), style={"height": "120px"}), width=12)
    outs = [empty_kpi] + [e_ui(gid) for gid in ['cdr-agent-volume', 'cdr-agent-transfer', 'cdr-agent-scatter']]

    if not data_ref or 'filename' not in data_ref: return outs
    token = auth_state.get('token') if auth_state else None
    if not token: return outs
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df is None or df.empty: return outs

    if 'segstart' in df.columns:
        df['Date'] = pd.to_datetime(df['segstart'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.date
        if df['Date'].isna().all():
            df['Date'] = pd.to_datetime(df['segstart'], errors='coerce').dt.date
    else:
        df['Date'] = pd.NaT

    mask = pd.Series(True, index=df.index)
    if companies and 'Company' in df.columns:
        mask = mask & df['Company'].isin(companies)
    if languages and 'Language' in df.columns:
        mask = mask & df['Language'].isin(languages)

    if start_date and end_date and not df['Date'].isna().all():
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
        mask = mask & (df['Date'] >= s) & (df['Date'] <= e)

    df = df[mask].copy()
    if df.empty: return outs
    
    total_calls = len(df)
    
    if 'anslogin' not in df.columns:
        return outs
        
    df['anslogin'] = df['anslogin'].fillna('Unknown')
    active_agents = df['anslogin'].nunique()
    calls_per_agent = total_calls / active_agents if active_agents > 0 else 0
    
    kpis = [
        dbc.Col(make_kpi_card("Active Agents", f"{active_agents:,}"), width=True),
        dbc.Col(make_kpi_card("Avg Calls per Agent", f"{calls_per_agent:.1f}"), width=True),
    ]

    # Group by anslogin and Company
    group_cols = ['anslogin']
    if 'Company' in df.columns:
        group_cols.append('Company')
        
    agent_grp = df.groupby(group_cols).agg(
        Calls=('call_id', 'count') if 'call_id' in df.columns else ('anslogin', 'size'),
        Avg_Talktime=('talktime', 'mean') if 'talktime' in df.columns else ('anslogin', lambda x: 0),
        Avg_Holdtime=('ansholdtime', 'mean') if 'ansholdtime' in df.columns else ('anslogin', lambda x: 0),
        Transfers=('transferred', 'sum') if 'transferred' in df.columns else ('anslogin', lambda x: 0)
    ).reset_index()
    
    agent_grp['Transfer_Rate'] = (agent_grp['Transfers'] / agent_grp['Calls']) * 100

    # Top 10 by Volume
    top_vol = agent_grp.sort_values(by='Calls', ascending=False).head(10)
    if not top_vol.empty:
        min_val = top_vol['Calls'].min()
        max_val = top_vol['Calls'].max()
        use_log = should_use_log(min_val, max_val)
        
        hover_data = ['Company'] if 'Company' in top_vol.columns else None
        
        fig_vol = px.bar(top_vol, x='Calls', y='anslogin', orientation='h', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY], log_x=use_log, hover_data=hover_data)
        fig_vol.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10), yaxis_title="Agent ID")
        
        if max_val > min_val and not use_log:
            fig_vol.update_xaxes(range=[0, max_val * 1.1])
            
        vol_ui = dcc.Graph(id='cdr-agent-volume', figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = e_ui('cdr-agent-volume')

    # Top 10 by Transfer Rate (min 5 calls)
    top_trans = agent_grp[agent_grp['Calls'] >= 5].sort_values(by='Transfer_Rate', ascending=False).head(10)
    if not top_trans.empty:
        min_val = top_trans['Transfer_Rate'].min()
        max_val = top_trans['Transfer_Rate'].max()
        use_log = should_use_log(min_val, max_val)
        
        hover_data = ['Company'] if 'Company' in top_trans.columns else None
        
        fig_trans = px.bar(top_trans, x='Transfer_Rate', y='anslogin', orientation='h', template='plotly_white', color_discrete_sequence=[COLOR_WARNING], log_x=use_log, hover_data=hover_data)
        fig_trans.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Transfer Rate %", yaxis_title="Agent ID")
        
        if max_val > min_val and not use_log:
            fig_trans.update_xaxes(range=[0, max_val * 1.1])
            
        trans_ui = dcc.Graph(id='cdr-agent-transfer', figure=fig_trans, config={'displayModeBar': False})
    else:
        trans_ui = e_ui('cdr-agent-transfer')

    # Scatter Plot: Talktime vs Hold Time
    if not agent_grp.empty and agent_grp['Calls'].sum() > 0:
        fig_scatter = px.scatter(
            agent_grp, x='Avg_Talktime', y='Avg_Holdtime',
            hover_name='anslogin', template='plotly_white', color_discrete_sequence=[COLOR_PRIMARY],
            labels={'Avg_Talktime': 'Average Talk Time (s)', 'Avg_Holdtime': 'Average Hold Time (s)'}
        )
        fig_scatter.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        
        min_x = agent_grp['Avg_Talktime'].min()
        max_x = agent_grp['Avg_Talktime'].max()
        if max_x > min_x or max_x > 0:
            fig_scatter.update_xaxes(range=[0 if min_x == 0 else min_x * 0.9, max_x * 1.1])
            
        min_y = agent_grp['Avg_Holdtime'].min()
        max_y = agent_grp['Avg_Holdtime'].max()
        if max_y > min_y or max_y > 0:
            fig_scatter.update_yaxes(range=[0 if min_y == 0 else min_y * 0.9, max_y * 1.1])
            
        scatter_ui = dcc.Graph(id='cdr-agent-scatter', figure=fig_scatter, config={'displayModeBar': False})
    else:
        scatter_ui = e_ui('cdr-agent-scatter')

    return kpis, vol_ui, trans_ui, scatter_ui


# ---------------- EXPORT CALLBACKS ----------------
@callback(
    Output({'type': 'download-data-cdr-agent', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-cdr-agent', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-agent-volume', 'figure'),
    State('cdr-agent-transfer', 'figure'),
    State('cdr-agent-scatter', 'figure'),
    prevent_initial_call=True
)
def export_pdf(n_clicks, vol, trans, scatter):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-agent-volume': vol, 'cdr-agent-transfer': trans, 'cdr-agent-scatter': scatter}
    
    if index == 'cdr-agent':
        pdf_bytes = generate_dashboard_pdf(figures, "CDR Agent Performance")
        return dcc.send_bytes(pdf_bytes, "cdr_agent_performance.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")

@callback(
    Output({'type': 'download-data-cdr-agent', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-cdr-agent', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-agent-volume', 'figure'),
    State('cdr-agent-transfer', 'figure'),
    State('cdr-agent-scatter', 'figure'),
    prevent_initial_call=True
)
def export_png(n_clicks, vol, trans, scatter):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-agent-volume': vol, 'cdr-agent-transfer': trans, 'cdr-agent-scatter': scatter}
    
    if index == 'cdr-agent':
        pdf_bytes = generate_dashboard_pdf(figures, "CDR Agent Performance")
        return dcc.send_bytes(pdf_bytes, "cdr_agent_performance.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-cdr-agent', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-cdr-agent', 'index': dash.MATCH}, "n_clicks"),
    State('cdr-agent-volume', 'figure'),
    State('cdr-agent-transfer', 'figure'),
    State('cdr-agent-scatter', 'figure'),
    prevent_initial_call=True
)
def export_html(n_clicks, vol, trans, scatter):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {'cdr-agent-volume': vol, 'cdr-agent-transfer': trans, 'cdr-agent-scatter': scatter}
    
    if index == 'cdr-agent':
        html_str = generate_dashboard_html(figures, "CDR Agent Performance")
        return dcc.send_string(html_str, "cdr_agent_performance.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
