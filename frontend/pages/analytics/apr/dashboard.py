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
        dbc.Col([wrap_chart_card('apr-occ', "Agent Occupancy (%)", "apr")], width=12, lg=6, className="mb-4"),
        dbc.Col([wrap_chart_card('apr-aht', "Average Handle Time (s)", "apr")], width=12, lg=6, className="mb-4")
    ]),

    # dbc.Row([
    #     dbc.Col([wrap_chart_card('apr-state-pie', "Agent State Distribution", "apr")], width=12, lg=6, className="mb-4"),
    #     dbc.Col([wrap_chart_card('apr-lang-pie', "Calls by Language", "apr")], width=12, lg=6, className="mb-4")
    # ]),

    dbc.Row([
        dbc.Col([wrap_chart_card('apr-state-pie', "Agent State Distribution", "apr")], width=12, lg=6, className="mb-4"),
        dbc.Col([wrap_chart_card('apr-lang-pie', "Calls by Language", "apr")], width=12, lg=6, className="mb-4")
    ])
])

@callback(
    Output('apr-kpi-row', 'children'),
    Output('apr-volume-container', 'children'),
    Output('apr-occ-container', 'children'),
    Output('apr-aht-container', 'children'),
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
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ'), e_ui('apr-aht'), e_ui('apr-state-bar'), e_ui('apr-lang-bar')

    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ'), e_ui('apr-aht'), e_ui('apr-state-bar'), e_ui('apr-lang-bar')

    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))

    if df is None or df.empty:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ'), e_ui('apr-aht'), e_ui('apr-state-bar'), e_ui('apr-lang-bar')

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
    else:
        df['Date'] = pd.NaT

    if start_date and not end_date: end_date = start_date
    if start_date and end_date:
        valid_mask = df['Date'].notna()
        df = df[valid_mask]
        if not df.empty:
            df = df[(df['Date'] >= pd.to_datetime(start_date).date()) & (df['Date'] <= pd.to_datetime(end_date).date())]

    if df.empty:
        return empty_kpi, e_ui('apr-vol'), e_ui('apr-occ'), e_ui('apr-aht'), e_ui('apr-state-bar'), e_ui('apr-lang-bar')

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
        dbc.Col(make_kpi_card("Avg Occupancy", f"{avg_occ:.1f}%", "good" if avg_occ > 70 else "neutral", sla_text="Target > 70%"), width=True),
        dbc.Col(make_kpi_card("Occupancy (No ACW)", f"{avg_util:.1f}%", "good" if avg_util > 60 else "neutral", sla_text="Target > 60%"), width=True),
        dbc.Col(make_kpi_card("Avg Handle Time", f"{avg_aht:.0f}s", "bad" if avg_aht > 240 else "good", sla_text="Target ≤ 240s"), width=True),
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
                fig_vol.update_yaxes(range=[0, max_val * 1.1])
                
        vol_ui = dcc.Graph(figure=fig_vol, config={'displayModeBar': False})
    else:
        vol_ui = e_ui('apr-volume')

    # Occupancy & AHT separate
    if 'Date' in df.columns and not df['Date'].isna().all() and '% Agent Occupancy with ACW' in df.columns and 'aht' in df.columns:
        combo_df = df.groupby('Date').agg({'% Agent Occupancy with ACW': 'mean', 'aht': 'mean'}).reset_index()
        show_text = len(combo_df) <= 15
        
        # Occupancy
        fig_occ = go.Figure()
        trace_occ = go.Scatter(
            x=combo_df['Date'], y=combo_df['% Agent Occupancy with ACW'].round(1),
            name="Occupancy %", mode='lines+markers+text' if show_text else 'lines+markers',
            line=dict(color=COLOR_WARNING, width=3, shape='spline'),
            hovertemplate='<b>Date:</b> %{x}<br><b>Occupancy:</b> %{y}%<extra></extra>'
        )
        if show_text:
            trace_occ.update(text=combo_df['% Agent Occupancy with ACW'].round(1).astype(str) + '%', textposition='top center')
        fig_occ.add_trace(trace_occ)
        fig_occ.update_layout(template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
        fig_occ.add_hline(y=80, line_dash="dash", line_color=COLOR_SUCCESS, annotation_text="Target")
        if sl_scale and 1 in sl_scale:
            fig_occ.update_yaxes(showgrid=False)
        else:
            fig_occ.update_yaxes(showgrid=False, range=[0, 105])
        occ_ui = dcc.Graph(id='apr-occ', figure=fig_occ, config={'displayModeBar': False})
        
        # AHT
        fig_aht = go.Figure()
        trace_aht = go.Bar(
            x=combo_df['Date'], y=combo_df['aht'].round(0),
            name="AHT (s)", marker_color=COLOR_NEUTRAL, opacity=0.7,
            hovertemplate='<b>Date:</b> %{x}<br><b>AHT:</b> %{y}s<extra></extra>'
        )
        fig_aht.add_trace(trace_aht)
        fig_aht.update_layout(template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
        fig_aht.add_hline(y=240, line_dash="dash", line_color=COLOR_SUCCESS, annotation_text="Target")
        if not combo_df.empty:
            max_val = combo_df['aht'].max()
            fig_aht.update_yaxes(showgrid=False, range=[0, max_val * 1.1])
        else:
            fig_aht.update_yaxes(showgrid=False)
        aht_ui = dcc.Graph(id='apr-aht', figure=fig_aht, config={'displayModeBar': False})
    else:
        occ_ui = e_ui('apr-occ')
        aht_ui = e_ui('apr-aht')

    # Agent State Bar
    state_cols = ['ACD Time', 'ACW Time', 'Avail Time', 'AUX Time', 'Agent Ring Time']
    if all(c in df.columns for c in state_cols):
        state_vals = [df[c].sum() for c in state_cols]
        state_df = pd.DataFrame({'State': state_cols, 'Time (Sec)': state_vals})
        def format_sec(s):
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            if h > 0: return f"{h}h {m:02d}m {sec:02d}s"
            if m > 0: return f"{m}m {sec:02d}s"
            return f"{sec}s"
        state_df['Time_Fmt'] = state_df['Time (Sec)'].apply(format_sec)
        
        fig_state = px.pie(state_df, values='Time (Sec)', names='State', hole=0.4, color='State', color_discrete_sequence=px.colors.qualitative.Pastel, custom_data=['Time_Fmt'])
        fig_state.update_traces(hovertemplate='<b>%{label}</b><br>Time: %{customdata[0]}<br>Percent: %{percent}<extra></extra>', textposition='inside', textinfo='percent+label')
        fig_state.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        state_ui = dcc.Graph(figure=fig_state, config={'displayModeBar': False})
    else:
        state_ui = e_ui('apr-state-pie')
        
    # Language Bar
    if 'Language' in df.columns and 'ACD Calls' in df.columns:
        lang_grp = df.groupby('Language')['ACD Calls'].sum().reset_index()
        fig_lang = px.pie(lang_grp, values='ACD Calls', names='Language', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label')
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        lang_ui = dcc.Graph(figure=fig_lang, config={'displayModeBar': False})
    else:
        lang_ui = e_ui('apr-lang-bar')

    return kpis, vol_ui, occ_ui, aht_ui, state_ui, lang_ui
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
    State('apr-occ', 'figure'),
    State('apr-aht', 'figure'),
    State('apr-state-bar', 'figure'),
    State('apr-lang-bar', 'figure'),
    prevent_initial_call=True
)
def export_pdf_dashboard(n_clicks, vol, occ, aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ': occ, 'apr-aht': aht, 'apr-state-bar': state, 'apr-lang-bar': lang}
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
    State('apr-occ', 'figure'),
    State('apr-aht', 'figure'),
    State('apr-state-bar', 'figure'),
    State('apr-lang-bar', 'figure'),
    prevent_initial_call=True
)
def export_png_dashboard(n_clicks, vol, occ, aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ': occ, 'apr-aht': aht, 'apr-state-bar': state, 'apr-lang-bar': lang}
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
    State('apr-occ', 'figure'),
    State('apr-aht', 'figure'),
    State('apr-state-bar', 'figure'),
    State('apr-lang-bar', 'figure'),
    prevent_initial_call=True
)
def export_html_dashboard(n_clicks, vol, occ, aht, state, lang):
    if not n_clicks: return dash.no_update
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    figures = {'apr-volume': vol, 'apr-occ': occ, 'apr-aht': aht, 'apr-state-bar': state, 'apr-lang-bar': lang}
    if index == 'apr':
        html_str = generate_dashboard_html(figures, "APR Dashboard")
        return dcc.send_string(html_str, "apr_dashboard_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
