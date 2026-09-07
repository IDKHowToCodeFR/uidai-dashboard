import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from frontend.shared.api_client import get_dataframe
from frontend.shared.theme import get_plotly_template, make_header_with_download, make_export_dropdown, should_use_log, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

dash.register_page(__name__, path='/unimate/dashboard', name='UniMate Dashboard')

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3("UniMate Overview", className="display-xl mb-0"),
                html.P("Executive summary of UniMate call performance.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        dbc.Col([
            html.Div([
                make_export_dropdown("unimate-dash"),
                dcc.Download(id={'type': 'download-data-unimate-dash', 'index': 'unimate-dash'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    dcc.Loading(type="dot", color=COLOR_PRIMARY, children=dbc.Row(id='unimate-kpi-row', className="mb-4 g-3")),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-vol-auth-trend', "Auth Rate vs Volume Trend", "unimate-dash")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-language', "Calls by Language", "unimate-dash")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('unimate-termination', "Termination Reasons", "unimate-dash")
        ], width=12, lg=6, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-sunburst', "Regional Interaction Breakdown", "unimate-dash")
        ], width=12, lg=6, className="mb-4"),
        dbc.Col([
            wrap_chart_card('unimate-term-language', "Termination Reasons by Language", "unimate-dash")
        ], width=12, lg=6, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-intraday-language', "Intraday Language Distribution (Avg 30-min)", "unimate-dash")
        ], width=12, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            wrap_chart_card('unimate-duration-hist', "Call Duration Distribution (s)", "unimate-dash")
        ], width=12, className="mb-4")
    ])
], className="container-fluid py-4")

@callback(
    Output('unimate-kpi-row', 'children'),
    Output('unimate-vol-auth-trend-container', 'children'),
    Output('unimate-termination-container', 'children'),
    Output('unimate-language-container', 'children'),
    Output('unimate-duration-hist-container', 'children'),
    Output('unimate-sunburst-container', 'children'),
    Output('unimate-intraday-language-container', 'children'),
    Output('unimate-term-language-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('sl-granularity', 'value'),
    Input('sl-scale-toggle', 'value'),
    State('auth-state', 'data')
)
def update_unimate_dashboard(data_ref, companies, languages, start_date, end_date, sl_granularity, sl_scale, auth_state):
    def e_ui(gid=None):
        return render_empty_state(graph_id=gid)

    empty_kpi = dbc.Col(html.Div(e_ui(), style={"height": "120px"}), width=12)
    outs = [empty_kpi] + [e_ui(gid) for gid in [
        'unimate-vol-auth-trend', 'unimate-termination', 'unimate-language', 
        'unimate-duration-hist', 'unimate-sunburst', 
        'unimate-intraday-language', 'unimate-term-language'
    ]]

    if not data_ref or 'filename' not in data_ref: return outs
    token = auth_state.get('token') if auth_state else None
    if not token: return outs
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df is None or df.empty: return outs

    if 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'], errors='coerce')
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
    
    date_col = 'Date' if not df['Date'].isna().all() else None

    # KPIs
    total_calls = len(df)
    auth_rate = 0
    if 'Authentication' in df.columns:
        auth_calls = df[df['Authentication'].astype(str).str.lower().isin(['true', '1', '1.0'])].shape[0]
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
        except: pass

    kpis = [
        dbc.Col(make_kpi_card("Total Calls", f"{total_calls:,}"), width=True),
        dbc.Col(make_kpi_card("Avg Duration", f"{avg_duration:.1f}s"), width=True),
        dbc.Col(make_kpi_card("Auth Rate", f"{auth_rate:.1f}%", "good" if auth_rate > 50 else "neutral"), width=True),
        dbc.Col(make_kpi_card("System Drops", f"{system_term:.1f}%", "bad" if system_term > 10 else "neutral"), width=True),
    ]

    # Time Bucketing
    if date_col:
        df['Date_Day'] = df['Date'].dt.date
        if sl_granularity and sl_granularity != 'Auto':
            freq = sl_granularity
        else:
            days_diff = (df['Date'].max() - df['Date'].min()).days
            freq = 'M' if days_diff > 90 else ('W-MON' if days_diff > 31 else 'D')
            
        if freq == 'D':
            df['Date_Bucket'] = df['Date'].dt.floor('D')
        else:
            df['Date_Bucket'] = df['Date'].dt.to_period(freq).dt.to_timestamp()
    else:
        df['Date_Bucket'] = pd.NaT

    # 1. Dual-Axis Vol Auth Trend
    if date_col and 'Authentication' in df.columns:
        trend_grp = df.groupby('Date_Bucket').agg(
            Calls=('Authentication', 'size'),
            Auths=('Authentication', lambda x: x.astype(str).str.lower().isin(['true', '1', '1.0']).sum())
        ).reset_index()
        trend_grp['Auth %'] = np.where(trend_grp['Calls'] == 0, 0, (trend_grp['Auths'] / trend_grp['Calls']) * 100)
        
        from plotly.subplots import make_subplots
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(go.Bar(
            x=trend_grp['Date_Bucket'], y=trend_grp['Calls'], name="Volume", 
            marker_color=COLOR_INFO, opacity=0.85, 
            hovertemplate='<b>Date:</b> %{x}<br><b>Volume:</b> %{y:,}<extra></extra>'
        ), secondary_y=False)
        
        fig_dual.add_trace(go.Scatter(
            x=trend_grp['Date_Bucket'], y=trend_grp['Auth %'], name="Auth %", 
            mode='lines+markers', line=dict(color=COLOR_SUCCESS, width=3, shape='spline'), 
            hovertemplate='<b>Date:</b> %{x}<br><b>Auth %:</b> %{y:.2f}%<extra></extra>'
        ), secondary_y=True)
        
        fig_dual.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_dual.update_yaxes(title_text="Volume", secondary_y=False, showgrid=False)
        if not trend_grp.empty and "Calls" in trend_grp.columns:
            min_v, max_v = trend_grp["Calls"].min(), trend_grp["Calls"].max()
            if max_v > min_v:
                fig_dual.update_yaxes(secondary_y=False, range=[0 if min_v == 0 else min_v * 0.9, max_v * 1.1])
        if sl_scale and 1 in sl_scale:
            fig_dual.update_yaxes(title_text="Auth %", secondary_y=True, showgrid=False, range=[max(0, min(trend_grp['Auth %'].min() - 2, 80)), min(100, trend_grp['Auth %'].max() + 2)])
        else:
            fig_dual.update_yaxes(title_text="Auth %", secondary_y=True, showgrid=False, range=[0, 100])
        ui_vol_auth = dcc.Graph(id='unimate-vol-auth-trend', figure=fig_dual, config={'displayModeBar': False})
    else:
        ui_vol_auth = e_ui('unimate-vol-auth-trend')

    # 2. Language Pie
    if 'Language' in df.columns:
        lang_df = df['Language'].value_counts().reset_index()
        lang_df.columns = ['Language', 'Count']
        fig_lang = px.pie(lang_df, names='Language', values='Count', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Count: %{value:,}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        ui_lang = dcc.Graph(id='unimate-language', figure=fig_lang, config={'displayModeBar': False})
    else:
        ui_lang = e_ui('unimate-language')

    # 3. Termination Chart
    if 'Termination Reason' in df.columns:
        term_df = df['Termination Reason'].value_counts().reset_index()
        term_df.columns = ['Reason', 'Count']
        fig_term = px.pie(term_df, names='Reason', values='Count', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_term.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>Reason:</b> %{label}<br><b>Count:</b> %{value:,}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_term.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        ui_term = dcc.Graph(id='unimate-termination', figure=fig_term, config={'displayModeBar': False})
    else:
        ui_term = e_ui('unimate-termination')

    # 4. Duration Histogram
    if 'Call Duration' in df.columns:
        df_dur = df[df['Call Duration'].notna()].copy()
        df_dur['Call Duration'] = pd.to_numeric(df_dur['Call Duration'], errors='coerce')
        df_dur = df_dur[df_dur['Call Duration'] > 0]
        
        fig_hist = px.histogram(df_dur, x='Call Duration', color_discrete_sequence=[COLOR_PRIMARY])
        fig_hist.update_traces(xbins=dict(start=0, end=df_dur['Call Duration'].max(), size=10), hovertemplate='<b>Duration:</b> %{x}s<br><b>Frequency:</b> %{y:,}<extra></extra>', marker_line_width=0)
        fig_hist.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, xaxis_title="Seconds", bargap=0.05)
        
        if sl_scale and 1 in sl_scale:
            fig_hist.update_yaxes(type="log")
            
        ui_hist = dcc.Graph(id='unimate-duration-hist', figure=fig_hist, config={'displayModeBar': False})
    else:
        ui_hist = e_ui('unimate-duration-hist')

    # 5. Regional Sunburst (Region -> Language -> Auth)
    if 'Language' in df.columns:
        df_sun = df.copy()
        df_sun['Region'] = df_sun.get('Region', pd.Series('Unknown', index=df_sun.index)).fillna('Unknown')
        df_sun['Language'] = df_sun['Language'].fillna('Unknown')
        df_sun['Authentication'] = df_sun.get('Authentication', pd.Series('Unknown', index=df_sun.index))
        df_sun['Auth_Status'] = np.where(df_sun['Authentication'].astype(str).str.lower().isin(['true', '1', '1.0']), 'Authenticated', 'Not Authenticated')
        
        sun_grp = df_sun.groupby(['Region', 'Language', 'Auth_Status']).size().reset_index(name='Calls')
        
        fig_sun = px.sunburst(sun_grp, path=['Region', 'Language', 'Auth_Status'], values='Calls', color='Auth_Status', 
                              color_discrete_map={'Authenticated': COLOR_SUCCESS, 'Not Authenticated': COLOR_WARNING, '(?)': COLOR_NEUTRAL})
        fig_sun.update_traces(textinfo='label+percent parent', hovertemplate='<b>%{label}</b><br>Calls: %{value:,}<extra></extra>')
        fig_sun.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10))
        ui_sun = dcc.Graph(id='unimate-sunburst', figure=fig_sun, config={'displayModeBar': False})
    else:
        ui_sun = e_ui('unimate-sunburst')

    # 7. Intraday Language Distribution
    if date_col and 'Language' in df.columns:
        df_intra = df.copy()
        df_intra['Time'] = df_intra['Date'].dt.floor('30min').dt.time
        df_intra['True_Day'] = df_intra['Date_Day']
        df_intra['Time'] = df_intra['Date'].dt.floor('30min').dt.time
        num_days = df_intra['Date_Day'].nunique()
        num_days = num_days if num_days > 0 else 1
        
        avg_intra = df_intra.groupby(['Time', 'Language']).size().reset_index(name='TotalCalls')
        avg_intra['Calls'] = (avg_intra['TotalCalls'] / num_days).round(2)
        
        lang_totals = avg_intra.groupby('Language')['Calls'].transform('sum')
        avg_intra['Percent'] = np.where(lang_totals > 0, (avg_intra['Calls'] / lang_totals) * 100, 0).round(1)
        
        avg_intra['TimeStr'] = avg_intra['Time'].astype(str).str[:5]
        avg_intra = avg_intra.sort_values(['TimeStr', 'Language'])
        
        if sl_scale and 1 in sl_scale:
            y_col = 'Percent'
            y_title = "% of Language's Daily Volume"
            hover = '<b>%{data.name}</b>: %{y}%<extra></extra>'
        else:
            y_col = 'Calls'
            y_title = "Average Volume (Calls)"
            hover = '<b>%{data.name}</b>: %{y}<extra></extra>'
        
        fig_intra = px.line(avg_intra, x='TimeStr', y=y_col, color='Language', color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_intra.update_xaxes(categoryorder='category ascending')
        fig_intra.update_traces(mode='lines', line_shape='spline', hovertemplate=hover)
        fig_intra.update_layout(template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), xaxis_title="Time of Day", yaxis_title=y_title, hovermode='x unified')
            
        ui_intra = dcc.Graph(id='unimate-intraday-language', figure=fig_intra, config={'displayModeBar': False})
    else:
        ui_intra = e_ui('unimate-intraday-language')

    # 8. Language-wise Termination Breakdown
    if 'Language' in df.columns and 'Termination Reason' in df.columns:
        term_lang_df = df.groupby(['Language', 'Termination Reason']).size().reset_index(name='Count')
        lang_totals = term_lang_df.groupby('Language')['Count'].transform('sum')
        term_lang_df['Percentage'] = (term_lang_df['Count'] / lang_totals) * 100
        
        min_val = term_lang_df['Percentage'].min()
        max_val = term_lang_df['Percentage'].max()
        use_log = should_use_log(min_val, max_val)
        
        fig_term_lang = px.bar(term_lang_df, x='Language', y='Percentage', color='Termination Reason', hover_data=['Count'], log_y=use_log)
        
        color_map = {}
        for reason in term_lang_df['Termination Reason'].unique():
            rl = str(reason).lower()
            if rl in ['system', 'abandon']: color_map[reason] = COLOR_DANGER
            elif rl in ['agent disconnect', 'normal']: color_map[reason] = COLOR_SUCCESS
            elif rl in ['transfer', 'transferred']: color_map[reason] = COLOR_INFO
            else: color_map[reason] = COLOR_NEUTRAL
                
        fig_term_lang.for_each_trace(lambda t: t.update(marker_color=color_map.get(t.name, COLOR_NEUTRAL)))
        fig_term_lang.update_traces(hovertemplate='<b>%{x}</b><br>Reason: %{data.name}<br>Percentage: %{y:.1f}%<br>Count: %{customdata[0]:,}<extra></extra>')
        fig_term_lang.update_layout(barmode='stack', template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), yaxis_title="% of Calls")
        ui_term_lang = dcc.Graph(id='unimate-term-language', figure=fig_term_lang, config={'displayModeBar': False})
    else:
        ui_term_lang = e_ui('unimate-term-language')

    return kpis, ui_vol_auth, ui_term, ui_lang, ui_hist, ui_sun, ui_intra, ui_term_lang


# ---------------- EXPORT CALLBACKS ----------------

@callback(
    Output({'type': 'download-data-unimate-dash', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-unimate-dash', 'index': dash.MATCH}, "n_clicks"),
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
    if ctx.triggered_id['index'] != 'unimate-dash': return dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update

    if company_filter and 'Company' in df.columns:
        df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns:
        df = df[df['Language'].isin(language_filter)]

    if 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'], errors='coerce')
        if start_date and end_date and not df['Date'].isna().all():
            start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date) + pd.Timedelta(days=1)
            df = df[(df['Date'] >= start_dt) & (df['Date'] < end_dt)]
        df = df.drop(columns=['Date'])

    return dcc.send_data_frame(df.to_csv, "unimate_dashboard_data.csv", index=False)


@callback(
    Output({'type': 'download-data-unimate-dash', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-unimate-dash', 'index': dash.MATCH}, "n_clicks"),
    State('unimate-vol-auth-trend', 'figure'),
    State('unimate-language', 'figure'),
    State('unimate-termination', 'figure'),
    State('unimate-duration-hist', 'figure'),
    State('unimate-sunburst', 'figure'),
    State('unimate-intraday-language', 'figure'),
    State('unimate-term-language', 'figure'),
    prevent_initial_call=True
)
def export_pdf_dashboard(n_clicks, vol_auth, lang, term, hist, sun, intra, term_lang):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {
        'unimate-vol-auth-trend': vol_auth, 'unimate-language': lang, 'unimate-termination': term,
        'unimate-duration-hist': hist, 'unimate-sunburst': sun,
        'unimate-intraday-language': intra, 'unimate-term-language': term_lang
    }
    
    if index == 'unimate-dash':
        pdf_bytes = generate_dashboard_pdf(figures, "UniMate Dashboard")
        return dcc.send_bytes(pdf_bytes, "unimate_dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")


@callback(
    Output({'type': 'download-data-unimate-dash', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-unimate-dash', 'index': dash.MATCH}, "n_clicks"),
    State('unimate-vol-auth-trend', 'figure'),
    State('unimate-language', 'figure'),
    State('unimate-termination', 'figure'),
    State('unimate-duration-hist', 'figure'),
    State('unimate-sunburst', 'figure'),
    State('unimate-intraday-language', 'figure'),
    State('unimate-term-language', 'figure'),
    prevent_initial_call=True
)
def export_png_dashboard(n_clicks, vol_auth, lang, term, hist, sun, intra, term_lang):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {
        'unimate-vol-auth-trend': vol_auth, 'unimate-language': lang, 'unimate-termination': term,
        'unimate-duration-hist': hist, 'unimate-sunburst': sun,
        'unimate-intraday-language': intra, 'unimate-term-language': term_lang
    }
    
    if index == 'unimate-dash':
        pdf_bytes = generate_dashboard_pdf(figures, "UniMate Dashboard")
        return dcc.send_bytes(pdf_bytes, "unimate_dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-unimate-dash', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-unimate-dash', 'index': dash.MATCH}, "n_clicks"),
    State('unimate-vol-auth-trend', 'figure'),
    State('unimate-language', 'figure'),
    State('unimate-termination', 'figure'),
    State('unimate-duration-hist', 'figure'),
    State('unimate-sunburst', 'figure'),
    State('unimate-intraday-language', 'figure'),
    State('unimate-term-language', 'figure'),
    prevent_initial_call=True
)
def export_html_dashboard(n_clicks, vol_auth, lang, term, hist, sun, intra, term_lang):
    if not n_clicks: return dash.no_update
    index = ctx.triggered_id['index']
    
    figures = {
        'unimate-vol-auth-trend': vol_auth, 'unimate-language': lang, 'unimate-termination': term,
        'unimate-duration-hist': hist, 'unimate-sunburst': sun,
        'unimate-intraday-language': intra, 'unimate-term-language': term_lang
    }
    
    if index == 'unimate-dash':
        html_str = generate_dashboard_html(figures, "UniMate Dashboard")
        return dcc.send_string(html_str, "unimate_dashboard_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
