import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from frontend.utils.theme import get_plotly_template, make_header_with_download, make_export_dropdown, wrap_graph_with_download
from frontend.utils.api import get_dataframe
import dash_bootstrap_components as dbc
# Global config removed in favor of API

dash.register_page(__name__, path='/', name='Dashboard')

def make_kpi_card(title, value, status="neutral"):
    color_class = "text-primary"
    if status == "Good":
        color_class = "text-success"
    elif status == "Penalty":
        color_class = "text-danger"

    return Card([
        CardBody([
            html.H6(title, className="text-muted text-uppercase mb-2", style={"fontSize": "12px", "fontWeight": "700", "letterSpacing": "0.5px"}),
            html.H3(value, className=f"mb-0 display-lg {color_class}")
        ])
    ], className="custom-card h-100")

def make_chart_card(title, chart_id, height_class="h-100", extra_style=None):
    if extra_style is None:
        extra_style = {}
    return Card([
        CardHeader(make_header_with_download(title, chart_id)),
        CardBody(wrap_graph_with_download(chart_id, dcc.Graph(id=chart_id, config={'displayModeBar': False}, style=extra_style)))
    ], className=f"custom-card {height_class}")

layout = Container([
    Row([
        Col([
            html.H2("Call Center Performance", className="display-xl mb-4")
        ], width=8),
        Col([
            make_export_dropdown("dashboard")
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    Row(id='kpi-row'),

    Row([
        Col([make_chart_card("Service Level Trend (%)", "sl-trend")], width=12, lg=7, className="mb-4"),
        Col([make_chart_card("Volume by Language", "lang-pie")], width=12, lg=5, className="mb-4"),
    ]),

    Row([
        Col([make_chart_card("Company KPI Radar (Monthly Median)", "aht-line-chart")], width=12, lg=6, className="mb-4"),
        Col([make_chart_card("AHT Composition Sunburst", "aht-lang-bar")], width=12, lg=6, className="mb-4"),
    ]),

    Row([
        Col([make_chart_card("Talk Time Distribution (s)", "talk-hist")], width=12, lg=4, className="mb-4"),
        Col([make_chart_card("Wrap Time (ACW) Distribution (s)", "wrap-hist")], width=12, lg=4, className="mb-4"),
        Col([make_chart_card("Hold Time Distribution (s)", "hold-hist")], width=12, lg=4, className="mb-4")
    ]),

    Row([
        Col([make_chart_card("Average Intraday Performance (Volume & SL)", "intraday-chart-overall", extra_style={'height': '400px'})], width=12, className="mb-4")
    ]),

    Row([
        Col([make_chart_card("Volume vs Abandonment Trend", "vol-aban-trend")], width=12, className="mb-4"),
    ]),
    
    Row([
        Col([make_chart_card("Calls Offered vs Answered (Daily)", "offered-ans-bar")], width=12, className="mb-4")
    ])
], fluid=True, className="px-4")

@callback(
    Output('kpi-row', 'children'),
    Output('sl-trend', 'figure'),
    Output('lang-pie', 'figure'),
    Output('talk-hist', 'figure'),
    Output('wrap-hist', 'figure'),
    Output('hold-hist', 'figure'),
    Output('intraday-chart-overall', 'figure'),
    Output('aht-line-chart', 'figure'),
    Output('vol-aban-trend', 'figure'),
    Output('aht-lang-bar', 'figure'),
    Output('offered-ans-bar', 'figure'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_dashboard(data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    empty_fig = px.pie(title="No Data")
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    date_candidates = ['Timestamp', 'Call Timestamp', 'Date', 'Call Start Time']
    df['Date'] = pd.NaT
    for col in date_candidates:
        if col in df.columns:
            df['Date'] = df['Date'].fillna(pd.to_datetime(df[col], errors='coerce'))
    
    date_col = 'Date' if not df['Date'].isna().all() else None

    # Fetch dynamic SLA targets
    sla_targets = [85, 95, 95, 85, 85, 85]
    if auth_state and auth_state.get('token'):
        from frontend.utils.api import api_client
        try:
            res = api_client.get_settings(auth_state.get('token'))
            if res.status_code == 200:
                settings = res.json()
                if "radar_sla_targets" in settings:
                    sla_targets = settings["radar_sla_targets"]
        except:
            pass

    # Filter boolean mask logic (optimizes memory)
    mask = pd.Series(True, index=df.index)
    if company_filter and 'Company' in df.columns:
        mask = mask & df['Company'].isin(company_filter)
    if language_filter and 'Language' in df.columns:
        mask = mask & df['Language'].isin(language_filter)
    if start_date and end_date and date_col:
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        mask = mask & (df['Date'] >= start_dt) & (df['Date'] <= end_dt)
        
    df_current = df[mask].copy()

    if df_current.empty:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    # Dynamic Time Bucketing
    if 'Date' in df_current.columns and not df_current['Date'].isna().all():
        min_dt, max_dt = df_current['Date'].min(), df_current['Date'].max()
        days_diff = (max_dt - min_dt).days if pd.notnull(min_dt) and pd.notnull(max_dt) else 0
        
        if days_diff > 90:
            freq = 'MS'
        elif days_diff > 31:
            freq = 'W-MON'
        else:
            freq = 'D'
            
        if freq == 'D':
            df_current['Date_Bucket'] = df_current['Date'].dt.floor('D')
        else:
            df_current['Date_Bucket'] = df_current['Date'].dt.to_period(freq).dt.to_timestamp()
    else:
        df_current['Date_Bucket'] = df_current.get('Date', pd.NaT)

    # Shared Aggregation for trends
    has_date_bucket = 'Date_Bucket' in df_current.columns
    daily_grp = pd.DataFrame()
    if has_date_bucket:
        daily_grp = df_current.groupby('Date_Bucket').sum(numeric_only=True).reset_index()

    # Cached KPI calcs
    total_calls_raw = df_current['Call Offered'].sum() if 'Call Offered' in df_current.columns else len(df_current)
    total_aban = df_current['ABAN Calls in 10 Sec'].sum() if 'ABAN Calls in 10 Sec' in df_current.columns else 0
    total_acd_20 = df_current['ACD Calls in 20 Sec'].sum() if 'ACD Calls in 20 Sec' in df_current.columns else 0
    total_acd_calls = df_current['ACD Calls'].sum() if 'ACD Calls' in df_current.columns else 0
    total_aban_raw = df_current['ABAN Calls'].sum() if 'ABAN Calls' in df_current.columns else 0
    
    # Service Level (Overall)
    den_sl = total_calls_raw - total_aban
    overall_sl = (total_acd_20 / den_sl * 100) if den_sl > 0 else 0
    sl_status = "Good" if overall_sl > 85 else "Penalty"

    # AHT (Overall)
    overall_aht = 0
    aht_status = "neutral"
    if all(c in df_current.columns for c in ['ACD Time', 'ACW Time', 'Hold Time']):
        num_aht = df_current['ACD Time'].sum() + df_current['ACW Time'].sum() + df_current['Hold Time'].sum()
        overall_aht = (num_aht / total_acd_calls) if total_acd_calls > 0 else 0
        aht_status = "Good" if overall_aht <= 240 else "Penalty"

    # Avg Hold Time (Overall)
    overall_hold = 0
    hold_status = "neutral"
    if 'Hold Time' in df_current.columns:
        num_hold = df_current['Hold Time'].sum()
        overall_hold = (num_hold / total_acd_calls) if total_acd_calls > 0 else 0
        hold_status = "Good" if overall_hold <= 20 else "Penalty"

    # Rates
    aban_rate = (total_aban_raw / total_calls_raw * 100) if total_calls_raw > 0 else 0
    ans_rate = (total_acd_calls / total_calls_raw * 100) if total_calls_raw > 0 else 0

    kpis = [
        Col(make_kpi_card("Total Calls", f"{int(total_calls_raw):,}"), className="col-4 col-lg mb-4"),
        Col(make_kpi_card("Answer Rate", f"{ans_rate:.1f}%"), className="col-4 col-lg mb-4"),
        Col(make_kpi_card("Abandon Rate", f"{aban_rate:.1f}%"), className="col-4 col-lg mb-4"),
        Col(make_kpi_card("Service Level", f"{overall_sl:.1f}%", sl_status), className="col-4 col-lg mb-4"),
        Col(make_kpi_card("SLA Vol Met", f"{int(total_acd_20):,}"), className="col-4 col-lg mb-4"),
        Col(make_kpi_card("AHT", f"{overall_aht:.0f}s", aht_status), className="col-4 col-lg mb-4"),
    ]

    # Chart 1: SL Trend (using shared daily_grp)
    if not daily_grp.empty and all(c in daily_grp.columns for c in ['ACD Calls in 20 Sec', 'Call Offered', 'ABAN Calls in 10 Sec']):
        denom = daily_grp['Call Offered'] - daily_grp['ABAN Calls in 10 Sec']
        daily_grp['SL %'] = np.where(denom == 0, 0, (daily_grp['ACD Calls in 20 Sec'] / denom * 100))
        
        # Rounding and text logic
        daily_grp['SL % text'] = daily_grp['SL %'].round(2).astype(str) + '%'
        show_text = len(daily_grp) <= 15
        
        if show_text:
            fig_sl = px.line(daily_grp, x='Date_Bucket', y='SL %', text='SL % text', render_mode='svg')
            fig_sl.update_traces(textposition='top center', mode='lines+markers+text', hovertemplate='<b>Date:</b> %{x}<br><b>SL:</b> %{y:.2f}%<extra></extra>')
        else:
            fig_sl = px.line(daily_grp, x='Date_Bucket', y='SL %', render_mode='svg')
            fig_sl.update_traces(mode='lines+markers', hovertemplate='<b>Date:</b> %{x}<br><b>SL:</b> %{y:.2f}%<extra></extra>')
            
        fig_sl.update_layout(xaxis_title="Date")
        fig_sl.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="85% Target")
    else:
        fig_sl = px.line(title="No SL Data")
    fig_sl.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))

    # Chart 2: Language Pie
    if 'Language' in df_current.columns and 'Call Offered' in df_current.columns:
        lang_grp = df_current.groupby('Language')['Call Offered'].sum().reset_index()
        fig_lang = px.pie(lang_grp, names='Language', values='Call Offered', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label', hoverinfo='label+value', marker=dict(line=dict(color='#ffffff', width=2)))
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
    else:
        fig_lang = px.pie(title="No Language Data")
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False)

    # Chart 3, 4, 5: Histograms
    if all(c in df_current.columns for c in ['ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        df_valid = df_current[df_current['ACD Calls'] > 0].copy()
        den_hist = df_valid['ACD Calls']
        
        df_valid['Talk Time'] = np.where(den_hist == 0, 0, df_valid['ACD Time'] / den_hist)
        df_valid['Wrap Time'] = np.where(den_hist == 0, 0, df_valid['ACW Time'] / den_hist)
        df_valid['Hold Time Avg'] = np.where(den_hist == 0, 0, df_valid['Hold Time'] / den_hist)
        
        fig_talk = px.histogram(df_valid, x='Talk Time', nbins=30, color_discrete_sequence=['#4299E1'])
        fig_talk.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="Frequency")
        
        fig_wrap = px.histogram(df_valid, x='Wrap Time', nbins=30, color_discrete_sequence=['#48BB78'])
        fig_wrap.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="")
        
        fig_hold = px.histogram(df_valid, x='Hold Time Avg', nbins=30, color_discrete_sequence=['#ED8936'])
        fig_hold.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="")
    else:
        fig_talk = px.histogram(title="No Data")
        fig_wrap = px.histogram(title="No Data")
        fig_hold = px.histogram(title="No Data")

    # Chart 6: Intraday
    if 'Date' in df_current.columns and not df_current['Date'].isna().all():
        df_current['Time'] = df_current['Date'].dt.floor('30min').dt.time
        df_current['True_Day'] = df_current['Date'].dt.floor('D')
        intraday_grp = df_current.groupby(['True_Day', 'Time']).sum(numeric_only=True).reset_index()
        avg_intraday = intraday_grp.groupby('Time').mean(numeric_only=True).reset_index()
        avg_intraday['TimeStr'] = avg_intraday['Time'].astype(str).str[:5]
        
        den_intra = avg_intraday['Call Offered'] - avg_intraday['ABAN Calls in 10 Sec']
        avg_intraday['SL %'] = np.where(den_intra == 0, 0, (avg_intraday['ACD Calls in 20 Sec'] / den_intra * 100))
        
        # Intraday is always 48 points, too dense for static text labels
        fig_intra = go.Figure()
        fig_intra.add_trace(go.Bar(
            x=avg_intraday['TimeStr'], y=avg_intraday['Call Offered'].round(2), 
            name='Avg Volume', marker_color='#3182ce', opacity=0.7, yaxis='y',
            hovertemplate='<b>Time:</b> %{x}<br><b>Volume:</b> %{y}<extra></extra>'
        ))
        fig_intra.add_trace(go.Scatter(
            x=avg_intraday['TimeStr'], y=avg_intraday['SL %'].round(2), 
            name='Avg SL %', mode='lines+markers', line=dict(color='#38a169', width=2), yaxis='y2',
            hovertemplate='<b>Time:</b> %{x}<br><b>SL:</b> %{y:.2f}%<extra></extra>'
        ))
        fig_intra.update_layout(
            template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), xaxis=dict(title='Time of Day'),
            yaxis=dict(title='Avg Volume', side='left', showgrid=False), yaxis2=dict(title='Avg SL %', side='right', overlaying='y', range=[0, 105], showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    else:
        fig_intra = px.line(title="No Timestamp Data")

    # Chart 7: Company KPI Radar
    if all(c in df_current.columns for c in ['Company', 'Call Offered', 'ABAN Calls', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls', 'ACD Calls in 20 Sec', 'ABAN Calls in 10 Sec']):
        comp_df = df_current.copy() # Removed hardcoded vendors
        comp_grp = comp_df.groupby('Company').sum(numeric_only=True).reset_index()
        
        comp_off = comp_grp['Call Offered']
        comp_grp['Abandon Rate (%)'] = np.where(comp_off == 0, 0, (comp_grp['ABAN Calls'] / comp_off * 100))
        
        den_radar = comp_grp['ACD Calls']
        
        comp_grp['Total AHT'] = np.where(den_radar == 0, 0, (comp_grp['ACD Time'] + comp_grp['ACW Time'] + comp_grp['Hold Time']) / den_radar)
        
        talk_ratio = np.where(den_radar == 0, 0, comp_grp['ACD Time'] / den_radar)
        wrap_ratio = np.where(den_radar == 0, 0, comp_grp['ACW Time'] / den_radar)
        hold_ratio = np.where(den_radar == 0, 0, comp_grp['Hold Time'] / den_radar)
        
        comp_grp['Talk Score'] = np.where(talk_ratio == 0, 0, (180 / talk_ratio * 100)).clip(min=0, max=100)
        comp_grp['Wrap Score'] = np.where(wrap_ratio == 0, 0, (30 / wrap_ratio * 100)).clip(min=0, max=100)
        comp_grp['Hold Score'] = np.where(hold_ratio == 0, 0, (30 / hold_ratio * 100)).clip(min=0, max=100)
        
        comp_grp['Answer Rate (%)'] = np.where(comp_off == 0, 0, (comp_grp['ACD Calls'] / comp_off * 100))
        
        den_sl_radar = comp_off - comp_grp['ABAN Calls in 10 Sec']
        comp_grp['SL %'] = np.where(den_sl_radar == 0, 0, (comp_grp['ACD Calls in 20 Sec'] / den_sl_radar * 100))
        comp_grp['No Abandon %'] = 100 - comp_grp['Abandon Rate (%)']
        
        categories = ['SL %', 'Answer Rate %', 'No Abandon %', 'Talk Score', 'Wrap Score', 'Hold Score']
        categories_closed = categories + [categories[0]]
        
        fig_agent = go.Figure()
        
        r_targets_closed = sla_targets + [sla_targets[0]]
        fig_agent.add_trace(go.Scatterpolar(
            r=r_targets_closed,
            theta=categories_closed,
            fill='toself',
            name='Target Limit (Red Line)',
            line=dict(color='red', dash='dot', width=2),
            fillcolor='rgba(255, 0, 0, 0.05)',
            hoverinfo='skip'
        ))
        
        colors = ['#3182ce', '#38a169', '#d69e2e', '#805ad5', '#e53e3e', '#319795']
        for i, row in comp_grp.iterrows():
            r_vals = [row['SL %'], row['Answer Rate (%)'], row['No Abandon %'], row['Talk Score'], row['Wrap Score'], row['Hold Score']]
            r_vals_closed = r_vals + [r_vals[0]]
            fig_agent.add_trace(go.Scatterpolar(
                r=r_vals_closed,
                theta=categories_closed, fill='toself', name=row['Company'], line_color=colors[i % len(colors)], opacity=0.6
            ))
            
        fig_agent.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, template=get_plotly_template(), margin=dict(t=40, b=40, l=40, r=40))
    else:
        fig_agent = px.line(title="No Company KPI Data")

    # Vol vs Abandonment Trend (using shared daily_grp)
    if not daily_grp.empty and all(c in daily_grp.columns for c in ['Call Offered', 'ABAN Calls']):
        daily_grp['Aban %'] = np.where(daily_grp['Call Offered'] == 0, 0, (daily_grp['ABAN Calls'] / daily_grp['Call Offered'] * 100))
        
        show_text = len(daily_grp) <= 15
        from plotly.subplots import make_subplots
        fig_vol = make_subplots(specs=[[{"secondary_y": True}]])
        
        vol_trace = go.Bar(x=daily_grp['Date_Bucket'], y=daily_grp['Call Offered'].round(2), name="Volume", marker_color='#818cf8', opacity=0.85, hovertemplate='<b>Date:</b> %{x}<br><b>Volume:</b> %{y}<extra></extra>')
        if show_text:
            vol_trace.update(text=daily_grp['Call Offered'].round(2), textposition='auto')
            
        aban_trace = go.Scatter(x=daily_grp['Date_Bucket'], y=daily_grp['Aban %'].round(2), name="Abandon %", mode='lines+markers+text' if show_text else 'lines+markers', line=dict(color='#f43f5e', width=3), hovertemplate='<b>Date:</b> %{x}<br><b>Abandon %:</b> %{y:.2f}%<extra></extra>')
        if show_text:
            aban_trace.update(text=daily_grp['Aban %'].round(2), textposition='top center')
            
        fig_vol.add_trace(vol_trace, secondary_y=False)
        fig_vol.add_trace(aban_trace, secondary_y=True)
        fig_vol.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_vol.update_xaxes(title_text="Date")
        fig_vol.update_yaxes(title_text="Volume", secondary_y=False, showgrid=False)
        fig_vol.update_yaxes(title_text="Abandon Rate %", secondary_y=True, showgrid=False)
    else:
        fig_vol = px.bar(title="No Volume Data")

    # AHT Breakdown by Language (Sunburst)
    if all(c in df_current.columns for c in ['Language', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        lang_aht_grp = df_current.groupby('Language').sum(numeric_only=True).reset_index()
        den_sun = lang_aht_grp['ACD Calls']
        
        sunburst_data = []
        for i, row in lang_aht_grp.iterrows():
            lang = row['Language']
            d = den_sun.iloc[i]
            t_time = row['ACD Time']/d if d > 0 else 0
            w_time = row['ACW Time']/d if d > 0 else 0
            h_time = row['Hold Time']/d if d > 0 else 0
            
            sunburst_data.append({'Language': lang, 'Metric': 'Talk Time', 'Value': round(t_time, 2)})
            sunburst_data.append({'Language': lang, 'Metric': 'Wrap Time', 'Value': round(w_time, 2)})
            sunburst_data.append({'Language': lang, 'Metric': 'Hold Time', 'Value': round(h_time, 2)})
            
        sb_df = pd.DataFrame(sunburst_data)
        # Semantic enterprise color scheme based on CONTEXT.md rules
        color_map = {'Talk Time': '#3b82f6', 'Wrap Time': '#64748b', 'Hold Time': '#ef4444'}
        fig_aht_lang = px.sunburst(sb_df, path=['Language', 'Metric'], values='Value', color='Metric', color_discrete_map=color_map)
        fig_aht_lang.update_traces(textinfo='label+value', texttemplate='%{label}: %{value}s', hovertemplate='<b>%{label}</b><br>Value: %{value}s<extra></extra>')
        fig_aht_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10))
    else:
        fig_aht_lang = px.pie(title="No Language AHT Data")

    # Calls Offered vs Answered (using shared daily_grp)
    if not daily_grp.empty and all(c in daily_grp.columns for c in ['Call Offered', 'ACD Calls']):
        show_text = len(daily_grp) <= 15
        
        trace_off = go.Bar(name='Offered', x=daily_grp['Date_Bucket'], y=daily_grp['Call Offered'].round(2), marker_color='#38bdf8', opacity=0.9, hovertemplate='<b>Date:</b> %{x}<br><b>Offered:</b> %{y}<extra></extra>')
        trace_ans = go.Bar(name='Answered', x=daily_grp['Date_Bucket'], y=daily_grp['ACD Calls'].round(2), marker_color='#6366f1', opacity=0.9, hovertemplate='<b>Date:</b> %{x}<br><b>Answered:</b> %{y}<extra></extra>')
        
        if show_text:
            trace_off.update(text=daily_grp['Call Offered'].round(2), textposition='auto')
            trace_ans.update(text=daily_grp['ACD Calls'].round(2), textposition='auto')
            
        fig_off_ans = go.Figure(data=[trace_off, trace_ans])
        fig_off_ans.update_layout(barmode='group', template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_off_ans.update_xaxes(title_text="Date")
    else:
        fig_off_ans = px.bar(title="No Data")

    return kpis, fig_sl, fig_lang, fig_talk, fig_wrap, fig_hold, fig_intra, fig_agent, fig_vol, fig_aht_lang, fig_off_ans

# CSV Export Callback
@callback(
    Output("download-dataframe-csv", "data", allow_duplicate=True),
    Input("btn-export-csv-dashboard", "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_dashboard(n_clicks, data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return dash.no_update
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty:
        return dash.no_update

    date_candidates = ['Timestamp', 'Call Timestamp', 'Date', 'Call Start Time']
    df['Date'] = pd.NaT
    for col in date_candidates:
        if col in df.columns:
            df['Date'] = df['Date'].fillna(pd.to_datetime(df[col], errors='coerce'))
    
    date_col = 'Date' if not df['Date'].isna().all() else None

    if company_filter and 'Company' in df.columns:
        df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns:
        df = df[df['Language'].isin(language_filter)]

    if start_date and end_date and date_col:
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]

    if 'Date' in df.columns:
        df = df.drop(columns=['Date'])

    return dcc.send_data_frame(df.to_csv, "dashboard_data.csv", index=False)

# PDF and JPG Page Export Callbacks
dash.clientside_callback(
    dash.ClientsideFunction(namespace='clientside', function_name='export_pdf'),
    Output('btn-export-pdf-dashboard', 'title'),
    Input('btn-export-pdf-dashboard', 'n_clicks'),
    prevent_initial_call=True
)

dash.clientside_callback(
    dash.ClientsideFunction(namespace='clientside', function_name='export_jpg'),
    Output('btn-export-jpg-dashboard', 'title'),
    Input('btn-export-jpg-dashboard', 'n_clicks'),
    prevent_initial_call=True
)

# Individual Chart JPG Export Callbacks
for graph_id in ['sl-trend', 'lang-pie', 'talk-hist', 'wrap-hist', 'hold-hist', 'intraday-chart-overall', 'aht-line-chart', 'vol-aban-trend', 'aht-lang-bar', 'offered-ans-bar']:
    dash.clientside_callback(
        dash.ClientsideFunction(namespace='clientside', function_name='export_chart_jpg'),
        Output(f"btn-download-{graph_id}", "title"),
        Input(f"btn-download-{graph_id}", "n_clicks"),
        State(graph_id, "id"),
        prevent_initial_call=True
    )