import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import COLOR_PRIMARY, COLOR_WARNING, COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_DANGER, COLOR_INFO, get_plotly_template, make_export_dropdown
from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

dash.register_page(__name__, path='/apr/dashboard', name='APR Dashboard')

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3("APR Analytics Overview", className="display-xl mb-0"),
                html.P("Executive summary of Agent Performance Reports.", className="text-muted mb-4 mt-2"),
            ])
        ], width=8),
        dbc.Col([
            html.Div([
                make_export_dropdown("apr"),
                dcc.Download(id={'type': 'download-data-apr', 'index': 'apr'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='apr-kpi-row', className="mb-4 g-3")),

    dbc.Row([
        dbc.Col([wrap_chart_card('apr-volume', "ACD Calls Trend", "apr")], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([wrap_chart_card('apr-occ-aht', "Occupancy vs Average Handle Time", "apr")], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([wrap_chart_card('apr-state-pie', "Agent State Distribution", "apr")], width=12, lg=6, className="mb-4"),
        dbc.Col([wrap_chart_card('apr-lang-pie', "Calls by Language", "apr")], width=12, lg=6, className="mb-4")
    ])
])

@callback(
    Output('apr-kpi-row', 'children'),
    Output('apr-volume-container', 'children'),
    Output('apr-occ-aht-container', 'children'),
    Output('apr-state-pie-container', 'children'),
    Output('apr-lang-pie-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('sl-granularity', 'value'),
    Input('sl-scale-toggle', 'value'),
    State('auth-state', 'data')
)
def update_apr_dashboard(data_ref, companies, languages, start_date, end_date, sl_granularity, sl_scale, auth_state):
    empty_ui = render_empty_state()
    empty_kpi = dbc.Col(html.Div(empty_ui, style={"height": "120px"}), width=12)

    def e_ui(gid):
        return render_empty_state(graph_id=gid)

    if not data_ref or 'filename' not in data_ref:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ-aht'), e_ui('apr-state-pie'), e_ui('apr-lang-pie')

    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ-aht'), e_ui('apr-state-pie'), e_ui('apr-lang-pie')

    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))

    if df is None or df.empty:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ-aht'), e_ui('apr-state-pie'), e_ui('apr-lang-pie')

    def parse_time(val):
        if pd.isna(val): return 0
        try:
            parts = str(val).split(':')
            if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
            elif len(parts) == 2: return int(parts[0])*60 + float(parts[1])
            return float(val)
        except:
            return 0

    time_cols = ['ACD Time', 'ACW Time', 'Avail Time', 'AUX Time', 'Agent Ring Time', 'Other Time']
    for col in time_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_time)

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
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ-aht'), e_ui('apr-state-pie'), e_ui('apr-lang-pie')

    if '% Agent Occupancy with ACW' in df.columns:
        df['% Agent Occupancy with ACW'] = df['% Agent Occupancy with ACW'].apply(lambda x: min(x, 100) if pd.notnull(x) else x)

    total_acd_calls = df['ACD Calls'].sum() if 'ACD Calls' in df.columns else 0
    avg_occ = df['% Agent Occupancy with ACW'].mean() if '% Agent Occupancy with ACW' in df.columns else 0
    avg_util = df['% Agent Occupancy without ACW'].mean() if '% Agent Occupancy without ACW' in df.columns else 0
    
    df['aht'] = df['Avg ACD Time'] + df['Avg ACW Time'] if 'Avg ACD Time' in df.columns and 'Avg ACW Time' in df.columns else 0
    avg_aht = df['aht'].mean() if 'aht' in df.columns else 0

    if 'Date' in df.columns and not df['Date'].isna().all():
        if sl_granularity and sl_granularity != 'Auto':
            freq = sl_granularity
        else:
            days_diff = (df['Date'].max() - df['Date'].min()).days if not df['Date'].empty else 0
            freq = 'M' if days_diff > 90 else ('W-MON' if days_diff > 31 else 'D')
        df['Date_Bucket'] = pd.to_datetime(df['Date'])
        if freq != 'D':
            df['Date_Bucket'] = df['Date_Bucket'].dt.to_period(freq).dt.to_timestamp()
        df['Date'] = df['Date_Bucket'].dt.date
    
    kpis = [
        dbc.Col(make_kpi_card("Total ACD Calls", f"{int(total_acd_calls):,}"), width=True),
        dbc.Col(make_kpi_card("Avg Occupancy", f"{avg_occ:.1f}%", "good" if avg_occ > 70 else "neutral"), width=True),
        dbc.Col(make_kpi_card("Utilization (No ACW)", f"{avg_util:.1f}%", "good" if avg_util > 60 else "neutral"), width=True),
        dbc.Col(make_kpi_card("Avg Handle Time", f"{avg_aht:.0f}s", "bad" if avg_aht > 240 else "good"), width=True),
    ]

    # Volume
    if 'Date' in df.columns and not df['Date'].isna().all() and 'ACD Calls' in df.columns:
        vol_df = df.groupby('Date')['ACD Calls'].sum().reset_index()
        show_text = len(vol_df) <= 15
        fig_vol = go.Figure()
        
        trace_vol = go.Bar(
            x=vol_df['Date'], y=vol_df['ACD Calls'],
            name="ACD Calls", marker_color=COLOR_PRIMARY, opacity=0.85,
            hovertemplate='<b>Date:</b> %{x}<br><b>ACD Calls:</b> %{y:,.0f}<extra></extra>'
        )
        if show_text:
            trace_vol.update(text=vol_df['ACD Calls'].apply(lambda x: f"{x:,.0f}"), textposition='auto')
            
        fig_vol.add_trace(trace_vol)
        fig_vol.update_layout(
            template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10),
            xaxis_title="Date", yaxis_title="Volume", showlegend=False
        )
        if not vol_df.empty and 'ACD Calls' in vol_df.columns:
            min_val = vol_df['ACD Calls'].min()
            max_val = vol_df['ACD Calls'].max()
            if max_val > min_val:
                fig_vol.update_yaxes(range=[0 if min_val == 0 else min_val * 0.9, max_val * 1.1])
                
        vol_ui = dcc.Graph(figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = e_ui('apr-volume')

    # Combined Occupancy & AHT
    if 'Date' in df.columns and not df['Date'].isna().all() and '% Agent Occupancy with ACW' in df.columns and 'aht' in df.columns:
        from plotly.subplots import make_subplots
        combo_df = df.groupby('Date').agg({'% Agent Occupancy with ACW': 'mean', 'aht': 'mean'}).reset_index()
        show_text = len(combo_df) <= 15
        
        fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
        
        # AHT (Bar)
        trace_aht = go.Bar(
            x=combo_df['Date'], y=combo_df['aht'].round(0),
            name="AHT (s)", marker_color=COLOR_NEUTRAL, opacity=0.7,
            hovertemplate='<b>Date:</b> %{x}<br><b>AHT:</b> %{y}s<extra></extra>'
        )
        
        # Occupancy (Line)
        trace_occ = go.Scatter(
            x=combo_df['Date'], y=combo_df['% Agent Occupancy with ACW'].round(1),
            name="Occupancy %", mode='lines+markers+text' if show_text else 'lines+markers',
            line=dict(color=COLOR_WARNING, width=3),
            hovertemplate='<b>Date:</b> %{x}<br><b>Occupancy:</b> %{y}%<extra></extra>'
        )
        if show_text:
            trace_occ.update(text=combo_df['% Agent Occupancy with ACW'].round(1).astype(str) + '%', textposition='top center')
            
        fig_combo.add_trace(trace_aht, secondary_y=False)
        fig_combo.add_trace(trace_occ, secondary_y=True)
        
        fig_combo.update_layout(
            template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        if not combo_df.empty and 'aht' in combo_df.columns:
            min_val = combo_df['aht'].min()
            max_val = combo_df['aht'].max()
            if max_val > min_val:
                fig_combo.update_yaxes(title_text="AHT (Seconds)", secondary_y=False, showgrid=False, range=[0 if min_val == 0 else min_val * 0.9, max_val * 1.1])
            else:
                fig_combo.update_yaxes(title_text="AHT (Seconds)", secondary_y=False, showgrid=False)
        else:
            fig_combo.update_yaxes(title_text="AHT (Seconds)", secondary_y=False, showgrid=False)
            
        if sl_scale and 1 in sl_scale:
            fig_combo.update_yaxes(title_text="Occupancy %", secondary_y=True, showgrid=False)
        else:
            fig_combo.update_yaxes(title_text="Occupancy %", secondary_y=True, showgrid=False, range=[0, 105])
        
        occ_aht_ui = dcc.Graph(figure=fig_combo, config={'displayModeBar': False})
    else:
        occ_aht_ui = e_ui('apr-occ-aht')

    # Agent State Pie
    state_cols = ['ACD Time', 'ACW Time', 'Avail Time', 'AUX Time', 'Agent Ring Time']
    if all(c in df.columns for c in state_cols):
        state_vals = [df[c].sum() for c in state_cols]
        state_df = pd.DataFrame({'State': state_cols, 'Time (Sec)': state_vals})
        fig_state = px.pie(state_df, names='State', values='Time (Sec)', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_state.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Seconds: %{value:,.0f}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_state.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        state_ui = dcc.Graph(figure=fig_state, config={'displayModeBar': False})
    else:
        state_ui = e_ui('apr-state-pie')
        
    # Language Pie
    if 'Language' in df.columns and 'ACD Calls' in df.columns:
        lang_grp = df.groupby('Language')['ACD Calls'].sum().reset_index()
        fig_lang = px.pie(lang_grp, names='Language', values='ACD Calls', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Count: %{value:,}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        lang_ui = dcc.Graph(figure=fig_lang, config={'displayModeBar': False})
    else:
        lang_ui = e_ui('apr-lang-pie')

    return kpis, vol_ui, occ_aht_ui, state_ui, lang_ui

# Exports
@callback(
    Output({'type': 'download-data-apr', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-apr', 'index': dash.MATCH}, "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_dashboard(n_clicks, data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    if not n_clicks or not data_ref or 'filename' not in data_ref: return dash.no_update
    triggered_id = ctx.triggered_id
    if triggered_id['index'] != 'apr': return dash.no_update
    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update
    if company_filter and 'Company' in df.columns: df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns: df = df[df['Language'].isin(language_filter)]
    return dcc.send_data_frame(df.to_csv, "apr_dashboard_data.csv", index=False)

@callback(
    Output({'type': 'download-data-apr', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-apr', 'index': dash.MATCH}, "n_clicks"),
    State('apr-volume', 'figure'),
    State('apr-occ-aht', 'figure'),
    State('apr-state-pie', 'figure'),
    State('apr-lang-pie', 'figure'),
    prevent_initial_call=True
)
def export_pdf_dashboard(n_clicks, vol, occ_aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ-aht': occ_aht, 'apr-state-pie': state, 'apr-lang-pie': lang}
    if index == 'apr':
        pdf_bytes = generate_dashboard_pdf(figures, "APR Dashboard")
        return dcc.send_bytes(pdf_bytes, "apr_dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")

@callback(
    Output({'type': 'download-data-apr', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-apr', 'index': dash.MATCH}, "n_clicks"),
    State('apr-volume', 'figure'),
    State('apr-occ-aht', 'figure'),
    State('apr-state-pie', 'figure'),
    State('apr-lang-pie', 'figure'),
    prevent_initial_call=True
)
def export_png_dashboard(n_clicks, vol, occ_aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ-aht': occ_aht, 'apr-state-pie': state, 'apr-lang-pie': lang}
    if index == 'apr':
        pdf_bytes = generate_dashboard_pdf(figures, "APR Dashboard")
        return dcc.send_bytes(pdf_bytes, "apr_dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-apr', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-apr', 'index': dash.MATCH}, "n_clicks"),
    State('apr-volume', 'figure'),
    State('apr-occ-aht', 'figure'),
    State('apr-state-pie', 'figure'),
    State('apr-lang-pie', 'figure'),
    prevent_initial_call=True
)
def export_html_dashboard(n_clicks, vol, occ_aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ-aht': occ_aht, 'apr-state-pie': state, 'apr-lang-pie': lang}
    if index == 'apr':
        html_str = generate_dashboard_html(figures, "APR Dashboard")
        return dcc.send_string(html_str, "apr_dashboard_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
