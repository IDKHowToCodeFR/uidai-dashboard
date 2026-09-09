import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.shared.theme import get_plotly_template, make_header_with_download, make_export_dropdown, should_use_log, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL, COLOR_INFO
from frontend.shared.api_client import get_dataframe
import dash_bootstrap_components as dbc
from frontend.components.cards import wrap_chart_card
from frontend.components.empty_state import render_empty_state, e_ui

dash.register_page(__name__, path='/ccf/hourly', name='Hourly Insights')

layout = Container([
    Row([
        Col([
            html.Div([
                html.H3("Hourly Insights", className="display-xl mb-0"),
                html.P("Intraday monitoring of call volumes and SLAs.", className="text-muted mb-0 mt-2"),
            ])
        ], width=8),
        Col([
            html.Div([
                make_export_dropdown("hourly"),
                dcc.Download(id={'type': 'download-data-hourly', 'index': 'hourly'})
            ])
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    Row(style={"position": "relative", "zIndex": 100}, children=[
        Col([
            Card([
                CardBody([
                    Row([
                        Col([
                            html.H6("DATES", className="section-title mb-2"),
                            dcc.DatePickerRange(
                                id='hourly-date-picker-range',
                                display_format='YYYY-MM-DD',
                                minimum_nights=0,
                            )
                        ], width=12, md=6, className="mb-3 mb-md-0"),
                        Col([
                            html.H6("TIME", className="section-title mb-2"),
                            html.Div([
                                dbc.Input(
                                    id='hourly-time-start',
                                    type='time',
                                    value='00:00:00',
                                    step="1",
                                    className="me-2",
                                    style={"width": "120px", "border": "1px solid var(--color-border)", "borderRadius": "6px", "padding": "4px 8px", "fontSize": "13px", "background": "var(--color-bg-primary)"}
                                ),
                                html.Span("–", className="text-muted me-2"),
                                dbc.Input(
                                    id='hourly-time-end',
                                    type='time',
                                    value='23:59:59',
                                    step="1",
                                    className="me-4",
                                    style={"width": "120px", "border": "1px solid var(--color-border)", "borderRadius": "6px", "padding": "4px 8px", "fontSize": "13px", "background": "var(--color-bg-primary)"}
                                )
                            ], className="d-flex align-items-center")
                        ], width=12, md=6)
                    ])
                ])
            ], className="custom-card mb-4")
        ], width=12)
    ]),

    Row([
        Col([wrap_chart_card("ccf-hour-vol", "Intraday Volume", "hourly")], width=12, lg=6, className="mb-4"),
        Col([wrap_chart_card("ccf-hour-sl", "Intraday Service Level (%)", "hourly")], width=12, lg=6, className="mb-4")
    ]),

    Row([
        Col([wrap_chart_card("ccf-sl-heatmap", "Service Level Heatmap (Day vs Hour)", "hourly")], width=12, className="mb-4")
    ]),
    
    Row([
        Col([wrap_chart_card("hourly-aban-bar", "Highest Abandonment by Language", "hourly")], width=12, className="mb-4")
    ]),
    Row([
        Col([wrap_chart_card("aht-time-chart", "Average Handle Time (AHT) by Time of Day", "hourly")], width=12, className="mb-4")
    ])
], fluid=True, className="px-4")


@callback(
    Output('hourly-date-picker-range', 'start_date'),
    Output('hourly-date-picker-range', 'end_date'),
    Output('hourly-date-picker-range', 'min_date_allowed'),
    Output('hourly-date-picker-range', 'max_date_allowed'),
    Input('data-store', 'data'),
    State('auth-state', 'data')
)
def set_date_picker(data_ref, auth_state):
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
        
    if not date_col or df is None or df.empty:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    
    if df.empty:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    max_date = df[date_col].max().date()
    min_date = df[date_col].min().date()
    
    from datetime import timedelta
    lookback = auth_state.get('data_lookback_days')
    role = auth_state.get('role', '')
    
    if lookback is not None and role != 'Admin':
        try:
            min_date = max(min_date, max_date - timedelta(days=int(lookback)))
        except (ValueError, TypeError):
            pass
    
    return min_date, max_date, min_date, max_date

@callback(
    Output('ccf-hour-vol-container', 'children'),
    Output('ccf-hour-sl-container', 'children'),
    Output('ccf-sl-heatmap-container', 'children'),
    Output('hourly-aban-bar-container', 'children'),
    Output('aht-time-chart-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('hourly-date-picker-range', 'start_date'),
    Input('hourly-date-picker-range', 'end_date'),
    Input('hourly-time-start', 'value'),
    Input('hourly-time-end', 'value'),
    State('auth-state', 'data')
)
def update_hourly_insights(data_ref, company_filter, language_filter, start_date, end_date, time_start, time_end, auth_state):

    outs = [e_ui('ccf-hour-vol'), e_ui('ccf-hour-sl'), e_ui('ccf-sl-heatmap'), e_ui('hourly-aban-bar'), e_ui('aht-time-chart')]
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or not start_date:
        return tuple(outs)
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return tuple(outs)
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    
    if df is None or df.empty:
        return tuple(outs)
    
    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else None
    if not date_col:
        return tuple(outs)

    df['DateCol'] = pd.to_datetime(df[date_col])
    if start_date and not end_date: end_date = start_date
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
    df_current = df[(df['DateCol'] >= start_dt) & (df['DateCol'] < end_dt)].copy()
    
    # Filter by time range (HH:MM:SS)
    ts_col = 'Call Timestamp' if 'Call Timestamp' in df_current.columns else date_col
    if ts_col in df_current.columns and time_start and time_end:
        def _to_sec(t):
            parts = str(t).split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + (int(parts[2]) if len(parts) > 2 else 0)
        ts = pd.to_datetime(df_current[ts_col])
        df_current['SecOfDay'] = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second
        df_current = df_current[(df_current['SecOfDay'] >= _to_sec(time_start)) & (df_current['SecOfDay'] <= _to_sec(time_end))]
    
    # Apply global filters
    if company_filter and 'Company' in df_current.columns:
        df_current = df_current[df_current['Company'].isin(company_filter)]
    if language_filter and 'Language' in df_current.columns:
        df_current = df_current[df_current['Language'].isin(language_filter)]
        
    if df_current.empty or ts_col not in df_current.columns:
        return tuple(outs)

    df_current['Time'] = pd.to_datetime(df_current[ts_col]).dt.time
    df_current['TimeStr'] = df_current['Time'].astype(str)

    # Chart 1: Intraday Vol & SL (Separated)
    hourly_grp = df_current.groupby('TimeStr').sum(numeric_only=True).reset_index()
    
    denom = hourly_grp['Call Offered'] - hourly_grp['ABAN Calls in 10 Sec']
    hourly_grp['SL %'] = (hourly_grp['ACD Calls in 20 Sec'] / denom * 100).fillna(0)
    
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=hourly_grp['TimeStr'], y=hourly_grp['Call Offered'], name='Call Volume', mode='lines+markers', line=dict(color='#3182ce', width=3, shape='spline'), fill='tozeroy', fillcolor=f'rgba(49, 130, 206, 0.1)', hovertemplate='<b>Time:</b> %{x}<br><b>Volume:</b> %{y}<extra></extra>'
    ))
    fig_vol.update_layout(template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), showlegend=False, xaxis_title='Time of Day', yaxis_title='Call Volume')
    ui_vol = dcc.Graph(id='ccf-hour-vol', figure=fig_vol, config={'displayModeBar': False})
    
    fig_sl = go.Figure()
    fig_sl.add_trace(go.Scatter(
        x=hourly_grp['TimeStr'], y=hourly_grp['SL %'], name='Service Level %', mode='lines+markers', line=dict(color='#38a169', width=3, shape='spline'), fill='tozeroy', fillcolor=f'rgba(56, 161, 105, 0.1)', hovertemplate='<b>Time:</b> %{x}<br><b>SL:</b> %{y:.1f}%<extra></extra>'
    ))
    fig_sl.update_layout(template=get_plotly_template(), margin=dict(t=20, b=20, l=10, r=10), showlegend=False, xaxis_title='Time of Day', yaxis_title='Service Level %')
    fig_sl.update_yaxes(range=[0, 105])
    ui_sl = dcc.Graph(id='ccf-hour-sl', figure=fig_sl, config={'displayModeBar': False})

    # Chart 1.5: SL% Heatmap (Day vs Hour)
    df_current['Hour'] = pd.to_datetime(df_current[ts_col]).dt.hour
    df_current['DayOfWeek'] = df_current['DateCol'].dt.day_name()
    heat_grp = df_current.groupby(['DayOfWeek', 'Hour']).sum(numeric_only=True).reset_index()
    denom_heat = heat_grp['Call Offered'] - heat_grp['ABAN Calls in 10 Sec']
    heat_grp['SL %'] = (heat_grp['ACD Calls in 20 Sec'] / denom_heat * 100).fillna(0)
    
    # Pivot for heatmap
    sl_pivot = heat_grp.pivot(index='DayOfWeek', columns='Hour', values='SL %').fillna(0)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    sl_pivot = sl_pivot.reindex(days_order).dropna(how='all')
    
    if not sl_pivot.empty:
        hours_labels = [f"{h:02d}:00" for h in sl_pivot.columns]
        fig_sl_heat = go.Figure(data=go.Heatmap(
            z=sl_pivot.values,
            x=hours_labels,
            y=sl_pivot.index,
            colorscale='RdYlGn',
            zmin=0, zmax=100,
            texttemplate="%{z:.0f}%",
            hovertemplate="<b>%{y} at %{x}</b><br>SL: %{z:.1f}%<extra></extra>"
        ))
        fig_sl_heat.update_layout(
            template=get_plotly_template(), margin=dict(t=10, b=30, l=10, r=10),
            xaxis_title="Hour of Day", yaxis_title=""
        )
        fig_sl_heat.update_yaxes(autorange="reversed")
        ui_sl_heat = dcc.Graph(id='ccf-sl-heatmap', figure=fig_sl_heat, config={'displayModeBar': False}, style={'height': '400px'})
    else:
        ui_sl_heat = render_empty_state('ccf-sl-heatmap')

    # Chart 2: Highest Abandonment by Language (Bar Chart)
    if 'Language' in df_current.columns:
        lang_aban = df_current.groupby('Language')['ABAN Calls'].sum().reset_index()
        lang_aban = lang_aban.sort_values('ABAN Calls', ascending=True)
        
        # Avoid log(0) issues by adding tiny epsilon if log is used
        min_val = lang_aban['ABAN Calls'].min()
        max_val = lang_aban['ABAN Calls'].max()
        use_log = should_use_log(min_val, max_val)
        if use_log:
            lang_aban['Plot Value'] = lang_aban['ABAN Calls'].replace(0, 0.1)
        else:
            lang_aban['Plot Value'] = lang_aban['ABAN Calls']
        
        fig_heat = px.bar(lang_aban, x='Plot Value', y='Language', orientation='h',
                          color='Language', color_discrete_sequence=px.colors.qualitative.Vivid,
                          log_x=use_log,
                          hover_data={'Plot Value': False, 'ABAN Calls': True, 'Language': False},
                          labels={'ABAN Calls': 'Actual Abandoned Calls', 'Plot Value': 'Abandoned Calls'})
        
        fig_heat.update_layout(
            template=get_plotly_template(),
            margin=dict(t=30, b=30, l=10, r=10),
            showlegend=False
        )
        ui_heat = dcc.Graph(id='hourly-aban-bar', figure=fig_heat, config={'displayModeBar': False}, style={'height': '400px'})
    else:
        ui_heat = render_empty_state('hourly-aban-bar')

    # Chart 3: AHT by Time of Day (Stacked Bar Chart)
    if all(c in df_current.columns for c in ['ACD Calls', 'ACD Time', 'ACW Time', 'Hold Time']):
        aht_grp = df_current.groupby('TimeStr').sum(numeric_only=True).reset_index()
        aht_grp['Talk Time'] = (aht_grp['ACD Time'] / aht_grp['ACD Calls']).fillna(0)
        aht_grp['Wrap Time'] = (aht_grp['ACW Time'] / aht_grp['ACD Calls']).fillna(0)
        aht_grp['Hold Time Avg'] = (aht_grp['Hold Time'] / aht_grp['ACD Calls']).fillna(0)
        aht_grp['Total AHT'] = aht_grp['Talk Time'] + aht_grp['Wrap Time'] + aht_grp['Hold Time Avg']
        
        fig_aht = go.Figure()
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Talk Time'], name='Talk Time', marker_color='#4299E1', customdata=aht_grp['Total AHT'], hovertemplate='Talk Time: %{y:.1f}s<br>Total AHT: %{customdata:.1f}s<extra></extra>'))
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Wrap Time'], name='Wrap Time', marker_color='#48BB78', customdata=aht_grp['Total AHT'], hovertemplate='Wrap Time: %{y:.1f}s<br>Total AHT: %{customdata:.1f}s<extra></extra>'))
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Hold Time Avg'], name='Hold Time', marker_color='#ED8936', customdata=aht_grp['Total AHT'], hovertemplate='Hold Time: %{y:.1f}s<br>Total AHT: %{customdata:.1f}s<extra></extra>'))
        
        fig_aht.update_layout(
            barmode='stack',
            template=get_plotly_template(),
            margin=dict(t=30, b=30, l=10, r=10),
            xaxis=dict(title='Time of Day'),
            yaxis=dict(title='Average Time (s)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        ui_aht = dcc.Graph(id='aht-time-chart', figure=fig_aht, config={'displayModeBar': False}, style={'height': '400px'})
    else:
        ui_aht = e_ui('aht-time-chart')

    return ui_vol, ui_sl, ui_sl_heat, ui_heat, ui_aht

# CSV Export Callback
@callback(
    Output({'type': 'download-data-hourly', 'index': dash.MATCH}, "data"),
    Input({'type': 'export-csv-hourly', 'index': dash.MATCH}, "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('hourly-date-picker-range', 'start_date'),
    State('hourly-date-picker-range', 'end_date'),
    State('hourly-time-start', 'value'),
    State('hourly-time-end', 'value'),
    State('auth-state', 'data'),
    prevent_initial_call=True
)
def export_csv_hourly(n_clicks, data_ref, company_filter, language_filter, start_date, end_date, time_start, time_end, auth_state):
    from dash import ctx
    if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or not start_date:
        return dash.no_update
        
    triggered_id = ctx.triggered_id
    if triggered_id['index'] != 'hourly':
        return dash.no_update

    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
    
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update

    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else None
    if date_col:
        df['DateCol'] = pd.to_datetime(df[date_col])
        if start_date and not end_date: end_date = start_date
        df = df[(df['DateCol'] >= pd.to_datetime(start_date)) & (df['DateCol'] <= pd.to_datetime(end_date))]

    ts_col = 'Call Timestamp' if 'Call Timestamp' in df.columns else date_col
    if ts_col and ts_col in df.columns and time_start and time_end:
        def _to_sec(t):
            parts = str(t).split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + (int(parts[2]) if len(parts) > 2 else 0)
        ts = pd.to_datetime(df[ts_col])
        df['SecOfDay'] = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second
        df = df[(df['SecOfDay'] >= _to_sec(time_start)) & (df['SecOfDay'] <= _to_sec(time_end))]

    if company_filter and 'Company' in df.columns:
        df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns:
        df = df[df['Language'].isin(language_filter)]

    for col in ['DateCol', 'SecOfDay']:
        if col in df.columns:
            df = df.drop(columns=[col])

    return dcc.send_data_frame(df.to_csv, "hourly_insights_data.csv", index=False)

# Backend PDF and JPG Export Callbacks
from dash import ctx
from frontend.shared.pdf_generator import generate_single_chart_pdf, generate_dashboard_pdf, generate_single_chart_png, generate_single_chart_html, generate_dashboard_html

@callback(
    Output({'type': 'download-data-hourly', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-pdf-hourly', 'index': dash.MATCH}, "n_clicks"),
    State('ccf-hour-vol', 'figure'),
    State('ccf-hour-sl', 'figure'),
    State('ccf-sl-heatmap', 'figure'),
    State('hourly-aban-bar', 'figure'),
    State('aht-time-chart', 'figure'),
    prevent_initial_call=True
)
def export_pdf_hourly(n_clicks, intra_vol, intra_sl, sl_heat, heatmap, aht):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'ccf-hour-vol': intra_vol,
        'ccf-hour-sl': intra_sl,
        'ccf-sl-heatmap': sl_heat,
        'hourly-aban-bar': heatmap,
        'aht-time-chart': aht
    }
    
    if index == 'hourly':
        pdf_bytes = generate_dashboard_pdf(figures, "Hourly Insights")
        return dcc.send_bytes(pdf_bytes, "hourly_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        pdf_bytes = generate_single_chart_pdf(fig_dict)
        return dcc.send_bytes(pdf_bytes, f"{index}_export.pdf")


@callback(
    Output({'type': 'download-data-hourly', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-png-hourly', 'index': dash.MATCH}, "n_clicks"),
    State('ccf-hour-vol', 'figure'),
    State('ccf-hour-sl', 'figure'),
    State('ccf-sl-heatmap', 'figure'),
    State('hourly-aban-bar', 'figure'),
    State('aht-time-chart', 'figure'),
    prevent_initial_call=True
)
def export_png_hourly(n_clicks, intra_vol, intra_sl, sl_heat, heatmap, aht):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'ccf-hour-vol': intra_vol,
        'ccf-hour-sl': intra_sl,
        'ccf-sl-heatmap': sl_heat,
        'hourly-aban-bar': heatmap,
        'aht-time-chart': aht
    }
    
    if index == 'hourly':
        pdf_bytes = generate_dashboard_pdf(figures, "Hourly Insights")
        return dcc.send_bytes(pdf_bytes, "hourly_export.pdf")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        png_bytes = generate_single_chart_png(fig_dict)
        return dcc.send_bytes(png_bytes, f"{index}_export.png")

@callback(
    Output({'type': 'download-data-hourly', 'index': dash.MATCH}, "data", allow_duplicate=True),
    Input({'type': 'export-html-hourly', 'index': dash.MATCH}, "n_clicks"),
    State('ccf-hour-vol', 'figure'),
    State('ccf-hour-sl', 'figure'),
    State('ccf-sl-heatmap', 'figure'),
    State('hourly-aban-bar', 'figure'),
    State('aht-time-chart', 'figure'),
    prevent_initial_call=True
)
def export_html_hourly(n_clicks, intra_vol, intra_sl, sl_heat, heatmap, aht):
    if not n_clicks: return dash.no_update
    
    triggered_id = ctx.triggered_id
    index = triggered_id['index']
    
    figures = {
        'ccf-hour-vol': intra_vol,
        'ccf-hour-sl': intra_sl,
        'ccf-sl-heatmap': sl_heat,
        'hourly-aban-bar': heatmap,
        'aht-time-chart': aht
    }
    
    if index == 'hourly':
        html_str = generate_dashboard_html(figures, "Hourly Insights")
        return dcc.send_string(html_str, "hourly_export.html")
    else:
        fig_dict = figures.get(index)
        if not fig_dict: return dash.no_update
        html_str = generate_single_chart_html(fig_dict)
        return dcc.send_string(html_str, f"{index}_export.html")
