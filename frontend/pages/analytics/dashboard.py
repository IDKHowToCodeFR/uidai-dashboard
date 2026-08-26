import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from frontend.shared.theme import get_plotly_template, make_header_with_download, make_export_dropdown, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.shared.api_client import get_dataframe
import dash_bootstrap_components as dbc
from frontend.components.cards import make_kpi_card, wrap_chart_card
from frontend.components.empty_state import render_empty_state

dash.register_page(__name__, path='/ccf/dashboard', name='Dashboard')

layout = Container([
    Row([
        Col([
            html.Div([
                html.H3("Call Center Performance", className="display-xl mb-0"),
                html.P("Overview of key contact center metrics and SLAs.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        Col([
            html.Div([
                make_export_dropdown("dashboard"),
                dcc.Download(id={'type': 'download-data-dashboard', 'index': 'dashboard'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    Row(id='kpi-row'),

    Row([
        Col([wrap_chart_card("sl-trend", "Service Level Trend (%)")], width=12, lg=7, className="mb-4"),
        Col([wrap_chart_card("lang-pie", "Volume by Language")], width=12, lg=5, className="mb-4"),
    ]),

    Row([
        Col([wrap_chart_card("aht-line-chart", "Company KPI Radar (Monthly Median)")], width=12, lg=6, className="mb-4"),
        Col([wrap_chart_card("aht-lang-bar", "AHT Composition Sunburst")], width=12, lg=6, className="mb-4"),
    ]),

    Row([
        Col([wrap_chart_card("talk-hist", "Talk Time Distribution (s)")], width=12, lg=4, className="mb-4"),
        Col([wrap_chart_card("wrap-hist", "Wrap Time (ACW) Distribution (s)")], width=12, lg=4, className="mb-4"),
        Col([wrap_chart_card("hold-hist", "Hold Time Distribution (s)")], width=12, lg=4, className="mb-4")
    ]),

    Row([
        Col([wrap_chart_card("intraday-chart-overall", "Average Intraday Performance (Volume & SL)")], width=12, className="mb-4")
    ]),

    Row([
        Col([wrap_chart_card("vol-aban-trend", "Volume vs Abandonment Trend")], width=12, className="mb-4"),
    ]),
    
    Row([
        Col([wrap_chart_card("offered-ans-bar", "Calls Offered vs Answered (Daily)")], width=12, className="mb-4")
    ])
], fluid=True, className="px-4")

@callback(
    Output('kpi-row', 'children'),
    Output('sl-trend-container', 'children'),
    Output('lang-pie-container', 'children'),
    Output('talk-hist-container', 'children'),
    Output('wrap-hist-container', 'children'),
    Output('hold-hist-container', 'children'),
    Output('intraday-chart-overall-container', 'children'),
    Output('aht-line-chart-container', 'children'),
    Output('vol-aban-trend-container', 'children'),
    Output('aht-lang-bar-container', 'children'),
    Output('offered-ans-bar-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_dashboard(data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    try:
        def e_ui(gid):
            return render_empty_state(graph_id=gid)
    
        if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
            return [], e_ui('sl-trend'), e_ui('lang-pie'), e_ui('talk-hist'), e_ui('wrap-hist'), e_ui('hold-hist'), e_ui('intraday-chart-overall'), e_ui('aht-line-chart'), e_ui('vol-aban-trend'), e_ui('aht-lang-bar'), e_ui('offered-ans-bar')

            
        token = auth_state.get('token') if auth_state else None
        if not token:
            return [], e_ui('sl-trend'), e_ui('lang-pie'), e_ui('talk-hist'), e_ui('wrap-hist'), e_ui('hold-hist'), e_ui('intraday-chart-overall'), e_ui('aht-line-chart'), e_ui('vol-aban-trend'), e_ui('aht-lang-bar'), e_ui('offered-ans-bar')
            
        df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
        if df is None or df.empty:
            return [], e_ui('sl-trend'), e_ui('lang-pie'), e_ui('talk-hist'), e_ui('wrap-hist'), e_ui('hold-hist'), e_ui('intraday-chart-overall'), e_ui('aht-line-chart'), e_ui('vol-aban-trend'), e_ui('aht-lang-bar'), e_ui('offered-ans-bar')
    
        date_candidates = ['Timestamp', 'Call Timestamp', 'Date', 'Call Start Time']
        df['Date'] = pd.NaT
        for col in date_candidates:
            if col in df.columns:
                df['Date'] = df['Date'].fillna(pd.to_datetime(df[col], errors='coerce'))
        
        date_col = 'Date' if not df['Date'].isna().all() else None
    
        # Fetch dynamic SLA targets
        sla_targets = [85, 95, 95, 85, 85, 85]
        if auth_state and auth_state.get('token'):
            from frontend.shared.api_client import api_get, api_post, get_history_options, download_file
            try:
                res = api_get("settings", token=auth_state.get('token'))
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
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            mask = mask & (df['Date'] >= start_dt) & (df['Date'] < end_dt)
            
        df_current = df[mask].copy()
    
        if df_current.empty:
            return [], e_ui('sl-trend'), e_ui('lang-pie'), e_ui('talk-hist'), e_ui('wrap-hist'), e_ui('hold-hist'), e_ui('intraday-chart-overall'), e_ui('aht-line-chart'), e_ui('vol-aban-trend'), e_ui('aht-lang-bar'), e_ui('offered-ans-bar')
    
        # Dynamic Time Bucketing
        if 'Date' in df_current.columns and not df_current['Date'].isna().all():
            min_dt, max_dt = df_current['Date'].min(), df_current['Date'].max()
            days_diff = (max_dt - min_dt).days if pd.notnull(min_dt) and pd.notnull(max_dt) else 0
            
            if days_diff > 90:
                freq = 'M'
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
            fig_sl.add_hline(y=85, line_dash="dash", line_color=COLOR_SUCCESS, annotation_text="85% Target")
            fig_sl.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))
            ui_sl = dcc.Graph(id='sl-trend', figure=fig_sl, config={'displayModeBar': False})
        else:
            ui_sl = e_ui('sl-trend')
    
        # Chart 2: Language Pie
        if 'Language' in df_current.columns and 'Call Offered' in df_current.columns:
            lang_grp = df_current.groupby('Language')['Call Offered'].sum().reset_index()
            fig_lang = px.pie(lang_grp, names='Language', values='Call Offered', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_lang.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Count: %{value:,}<extra></extra>', marker=dict(line=dict(color='#ffffff', width=2)))
            fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            ui_lang = dcc.Graph(id='lang-pie', figure=fig_lang, config={'displayModeBar': False})
        else:
            ui_lang = e_ui('lang-pie')
    
        # Chart 3, 4, 5: Histograms
        if all(c in df_current.columns for c in ['ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
            df_valid = df_current[df_current['ACD Calls'] > 0].copy()
            den_hist = df_valid['ACD Calls']
            
            df_valid['Talk Time'] = np.where(den_hist == 0, 0, df_valid['ACD Time'] / den_hist)
            df_valid['Wrap Time'] = np.where(den_hist == 0, 0, df_valid['ACW Time'] / den_hist)
            df_valid['Hold Time Avg'] = np.where(den_hist == 0, 0, df_valid['Hold Time'] / den_hist)
            
            fig_talk = px.histogram(df_valid, x='Talk Time', nbins=30, color_discrete_sequence=[COLOR_PRIMARY])
            fig_talk.update_traces(hovertemplate='<b>Talk Time:</b> %{x}s<br><b>Frequency:</b> %{y}<extra></extra>')
            fig_talk.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="Frequency")
            ui_talk = dcc.Graph(id='talk-hist', figure=fig_talk, config={'displayModeBar': False})
            
            fig_wrap = px.histogram(df_valid, x='Wrap Time', nbins=30, color_discrete_sequence=[COLOR_NEUTRAL])
            fig_wrap.update_traces(hovertemplate='<b>Wrap Time:</b> %{x}s<br><b>Frequency:</b> %{y}<extra></extra>')
            fig_wrap.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="")
            ui_wrap = dcc.Graph(id='wrap-hist', figure=fig_wrap, config={'displayModeBar': False})
            
            fig_hold = px.histogram(df_valid, x='Hold Time Avg', nbins=30, color_discrete_sequence=[COLOR_WARNING])
            fig_hold.update_traces(hovertemplate='<b>Hold Time:</b> %{x}s<br><b>Frequency:</b> %{y}<extra></extra>')
            fig_hold.update_layout(template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10), showlegend=False, yaxis_title="")
            ui_hold = dcc.Graph(id='hold-hist', figure=fig_hold, config={'displayModeBar': False})
        else:
            ui_talk = e_ui('talk-hist')
            ui_wrap = e_ui('wrap-hist')
            ui_hold = e_ui('hold-hist')
    
        # Chart 6: Intraday
        if 'Date' in df_current.columns and not df_current['Date'].isna().all():
            df_current['Time'] = df_current['Date'].dt.floor('30min').dt.time
            df_current['True_Day'] = df_current['Date'].dt.floor('D')
            intraday_grp = df_current.groupby(['True_Day', 'Time']).sum(numeric_only=True).reset_index()
            avg_intraday = intraday_grp.groupby('Time').mean(numeric_only=True).reset_index()
            avg_intraday['TimeStr'] = avg_intraday['Time'].astype(str).str[:5]
            
            den_intra = avg_intraday['Call Offered'] - avg_intraday['ABAN Calls in 10 Sec']
            avg_intraday['SL %'] = np.where(den_intra == 0, 0, (avg_intraday['ACD Calls in 20 Sec'] / den_intra * 100))
            
            fig_intra = go.Figure()
            fig_intra.add_trace(go.Bar(
                x=avg_intraday['TimeStr'], y=avg_intraday['Call Offered'].round(2), 
                name='Avg Volume', marker_color=COLOR_NEUTRAL, opacity=0.7, yaxis='y',
                hovertemplate='<b>Time:</b> %{x}<br><b>Volume:</b> %{y}<extra></extra>'
            ))
            fig_intra.add_trace(go.Scatter(
                x=avg_intraday['TimeStr'], y=avg_intraday['SL %'].round(2), 
                name='Avg SL %', mode='lines+markers', line=dict(color=COLOR_SUCCESS, width=2), yaxis='y2',
                hovertemplate='<b>Time:</b> %{x}<br><b>SL:</b> %{y:.2f}%<extra></extra>'
            ))
            fig_intra.update_layout(
                template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), xaxis=dict(title='Time of Day'),
                yaxis=dict(title='Avg Volume', side='left', showgrid=False), yaxis2=dict(title='Avg SL %', side='right', overlaying='y', range=[0, 105], showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            ui_intra = dcc.Graph(id='intraday-chart-overall', figure=fig_intra, config={'displayModeBar': False}, style={'height': '400px'})
        else:
            ui_intra = e_ui('intraday-chart-overall')
    
        # Chart 7: Company KPI Radar
        if all(c in df_current.columns for c in ['Company', 'Call Offered', 'ABAN Calls', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls', 'ACD Calls in 20 Sec', 'ABAN Calls in 10 Sec']):
            comp_df = df_current.copy() 
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
            ui_agent = dcc.Graph(id='aht-line-chart', figure=fig_agent, config={'displayModeBar': False})
        else:
            ui_agent = e_ui('aht-line-chart')
    
        # Vol vs Abandonment Trend (using shared daily_grp)
        if not daily_grp.empty and all(c in daily_grp.columns for c in ['Call Offered', 'ABAN Calls']):
            daily_grp['Aban %'] = np.where(daily_grp['Call Offered'] == 0, 0, (daily_grp['ABAN Calls'] / daily_grp['Call Offered'] * 100))
            
            show_text = len(daily_grp) <= 15
            from plotly.subplots import make_subplots
            fig_vol = make_subplots(specs=[[{"secondary_y": True}]])
            
            vol_trace = go.Bar(x=daily_grp['Date_Bucket'], y=daily_grp['Call Offered'].round(2), name="Volume", marker_color=COLOR_INFO, opacity=0.85, hovertemplate='<b>Date:</b> %{x}<br><b>Volume:</b> %{y}<extra></extra>')
            if show_text:
                vol_trace.update(text=daily_grp['Call Offered'].round(2), textposition='auto')
                
            aban_trace = go.Scatter(x=daily_grp['Date_Bucket'], y=daily_grp['Aban %'].round(2), name="Abandon %", mode='lines+markers+text' if show_text else 'lines+markers', line=dict(color=COLOR_DANGER, width=3), hovertemplate='<b>Date:</b> %{x}<br><b>Abandon %:</b> %{y:.2f}%<extra></extra>')
            if show_text:
                aban_trace.update(text=daily_grp['Aban %'].round(2), textposition='top center')
                
            fig_vol.add_trace(vol_trace, secondary_y=False)
            fig_vol.add_trace(aban_trace, secondary_y=True)
            fig_vol.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_vol.update_xaxes(title_text="Date")
            fig_vol.update_yaxes(title_text="Volume", secondary_y=False, showgrid=False)
            fig_vol.update_yaxes(title_text="Abandon Rate %", secondary_y=True, showgrid=False)
            ui_vol = dcc.Graph(id='vol-aban-trend', figure=fig_vol, config={'displayModeBar': False})
        else:
            ui_vol = e_ui('vol-aban-trend')
    
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
            color_map = {'Talk Time': COLOR_PRIMARY, 'Wrap Time': COLOR_NEUTRAL, 'Hold Time': COLOR_DANGER}
            fig_aht_lang = px.sunburst(sb_df, path=['Language', 'Metric'], values='Value', color='Metric', color_discrete_map=color_map)
            fig_aht_lang.update_traces(textinfo='label+value', texttemplate='%{label}: %{value}s', hovertemplate='<b>%{label}</b><br>Value: %{value}s<extra></extra>')
            fig_aht_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10))
            ui_aht_lang = dcc.Graph(id='aht-lang-bar', figure=fig_aht_lang, config={'displayModeBar': False})
        else:
            ui_aht_lang = e_ui('aht-lang-bar')
    
        # Calls Offered vs Answered
        if not daily_grp.empty and all(c in daily_grp.columns for c in ['Call Offered', 'ACD Calls']):
            show_text = len(daily_grp) <= 15
            
            trace_off = go.Bar(name='Offered', x=daily_grp['Date_Bucket'], y=daily_grp['Call Offered'].round(2), marker_color=COLOR_NEUTRAL, opacity=0.9, hovertemplate='<b>Date:</b> %{x}<br><b>Offered:</b> %{y}<extra></extra>')
            trace_ans = go.Bar(name='Answered', x=daily_grp['Date_Bucket'], y=daily_grp['ACD Calls'].round(2), marker_color=COLOR_SUCCESS, opacity=0.9, hovertemplate='<b>Date:</b> %{x}<br><b>Answered:</b> %{y}<extra></extra>')
            
            if show_text:
                trace_off.update(text=daily_grp['Call Offered'].round(2), textposition='auto')
                trace_ans.update(text=daily_grp['ACD Calls'].round(2), textposition='auto')
                
            fig_off_ans = go.Figure(data=[trace_off, trace_ans])
            fig_off_ans.update_layout(barmode='group', template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_off_ans.update_xaxes(title_text="Date")
            ui_off_ans = dcc.Graph(id='offered-ans-bar', figure=fig_off_ans, config={'displayModeBar': False})
        else:
            ui_off_ans = e_ui('offered-ans-bar')
    
        return kpis, ui_sl, ui_lang, ui_talk, ui_wrap, ui_hold, ui_intra, ui_agent, ui_vol, ui_aht_lang, ui_off_ans
    
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        from dash import html
        err_ui = [html.Div([html.H4("Dashboard Error"), html.Pre(err_msg)], style={"color": "red", "padding": "20px"})]
        return err_ui, e_ui('sl-trend'), e_ui('lang-pie'), e_ui('talk-hist'), e_ui('wrap-hist'), e_ui('hold-hist'), e_ui('intraday-chart-overall'), e_ui('aht-line-chart'), e_ui('vol-aban-trend'), e_ui('aht-lang-bar'), e_ui('offered-ans-bar')
# CSV Export Callback
@callback(
    Output({'type': 'download-data-dashboard', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-dashboard', 'index': dash.MATCH}, "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_dashboard(n_clicks, data_ref, company_filter, language_filter, start_date, end_date, auth_state):
    from dash import ctx
    if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return dash.no_update
        
    triggered_id = ctx.triggered_id
    if triggered_id['index'] != 'dashboard':
        return dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return dash.no_update
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty:
        return dash.no_update

    if 'Date' not in df.columns:
        df['Date'] = pd.NaT
        
    date_candidates = ['Call Timestamp', 'Date Logged', 'Date', 'Start Time']
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

# Backend PDF and JPG Export Callbacks
from dash import ctx
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

@callback(
    Output({'type': 'download-data-dashboard', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-dashboard', 'index': dash.MATCH}, "n_clicks"),
    State('sl-trend', 'figure'),
    State('lang-pie', 'figure'),
    State('talk-hist', 'figure'),
    State('wrap-hist', 'figure'),
    State('hold-hist', 'figure'),
    State('intraday-chart-overall', 'figure'),
    State('aht-line-chart', 'figure'),
    State('vol-aban-trend', 'figure'),
    State('aht-lang-bar', 'figure'),
    State('offered-ans-bar', 'figure'),
    prevent_initial_call=True
)
def export_pdf_dashboard(n_clicks, sl, lang, talk, wrap, hold, intraday, aht_line, vol, aht_bar, offered):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'sl-trend': sl, 'lang-pie': lang, 'talk-hist': talk, 'wrap-hist': wrap,
        'hold-hist': hold, 'intraday-chart-overall': intraday, 'aht-line-chart': aht_line,
        'vol-aban-trend': vol, 'aht-lang-bar': aht_bar, 'offered-ans-bar': offered
    }
    
    if index == 'dashboard':
        pdf_bytes = generate_dashboard_pdf(figures, "Dashboard")
        return dcc.send_bytes(pdf_bytes, "dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")


@callback(
    Output({'type': 'download-data-dashboard', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-dashboard', 'index': dash.MATCH}, "n_clicks"),
    State('sl-trend', 'figure'),
    State('lang-pie', 'figure'),
    State('talk-hist', 'figure'),
    State('wrap-hist', 'figure'),
    State('hold-hist', 'figure'),
    State('intraday-chart-overall', 'figure'),
    State('aht-line-chart', 'figure'),
    State('vol-aban-trend', 'figure'),
    State('aht-lang-bar', 'figure'),
    State('offered-ans-bar', 'figure'),
    prevent_initial_call=True
)
def export_png_dashboard(n_clicks, sl, lang, talk, wrap, hold, intraday, aht_line, vol, aht_bar, offered):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'sl-trend': sl, 'lang-pie': lang, 'talk-hist': talk, 'wrap-hist': wrap,
        'hold-hist': hold, 'intraday-chart-overall': intraday, 'aht-line-chart': aht_line,
        'vol-aban-trend': vol, 'aht-lang-bar': aht_bar, 'offered-ans-bar': offered
    }
    
    if index == 'dashboard':
        pdf_bytes = generate_dashboard_pdf(figures, "Dashboard")
        return dcc.send_bytes(pdf_bytes, "dashboard_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-dashboard', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-dashboard', 'index': dash.MATCH}, "n_clicks"),
    State('sl-trend', 'figure'),
    State('lang-pie', 'figure'),
    State('talk-hist', 'figure'),
    State('wrap-hist', 'figure'),
    State('hold-hist', 'figure'),
    State('intraday-chart-overall', 'figure'),
    State('aht-line-chart', 'figure'),
    State('vol-aban-trend', 'figure'),
    State('aht-lang-bar', 'figure'),
    State('offered-ans-bar', 'figure'),
    prevent_initial_call=True
)
def export_html_dashboard(n_clicks, sl, lang, talk, wrap, hold, intraday, aht_line, vol, aht_bar, offered):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'sl-trend': sl, 'lang-pie': lang, 'talk-hist': talk, 'wrap-hist': wrap,
        'hold-hist': hold, 'intraday-chart-overall': intraday, 'aht-line-chart': aht_line,
        'vol-aban-trend': vol, 'aht-lang-bar': aht_bar, 'offered-ans-bar': offered
    }
    
    if index == 'dashboard':
        html_str = generate_dashboard_html(figures, "Dashboard")
        return dcc.send_string(html_str, "dashboard_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")