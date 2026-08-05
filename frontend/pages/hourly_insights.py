import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.utils.theme import get_plotly_template, make_header_with_download, make_export_dropdown, wrap_graph_with_download
from frontend.utils.api import get_dataframe
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/hourly', name='Hourly Insights')

layout = Container([
    Row([
        Col([
            html.Div([
                html.H2("Hourly Insights", className="display-xl mb-0"),
                html.Div([
                    html.Span("Dates: ", className="text-muted small text-uppercase me-2 fw-bold"),
                    dcc.DatePickerRange(
                        id='hourly-date-picker-range',
                        display_format='YYYY-MM-DD',
                        className="ms-2 me-4"
                    ),
                    html.Span("Time: ", className="text-muted small text-uppercase me-2 fw-bold"),
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
                    ),
                    make_export_dropdown("hourly")
                ], className="d-flex align-items-center bg-white border rounded px-3 py-2 shadow-sm flex-wrap")
            ], className="d-flex justify-content-between align-items-center mb-4")
        ], width=12)
    ]),

    Row([
        Col([
            Card([
                CardHeader(make_header_with_download("Intraday Performance (Volume & Service Level)", "intraday-chart")),
                CardBody(wrap_graph_with_download("intraday-chart", dcc.Graph(id='intraday-chart', config={'displayModeBar': False}, style={'height': '400px'})))
            ], className="custom-card h-100")
        ], width=12, className="mb-4")
    ]),
    
    Row([
        Col([
            Card([
                CardHeader(make_header_with_download("Highest Abandonment by Language", "hourly-heatmap")),
                CardBody(wrap_graph_with_download("hourly-heatmap", dcc.Graph(id='hourly-heatmap', config={'displayModeBar': False}, style={'height': '400px'})))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4"),
        
        Col([
            Card([
                CardHeader(make_header_with_download("Average Handle Time (AHT) by Time of Day", "aht-time-chart")),
                CardBody(wrap_graph_with_download("aht-time-chart", dcc.Graph(id='aht-time-chart', config={'displayModeBar': False}, style={'height': '400px'})))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4")
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
        
    if not date_col or df.empty:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    df[date_col] = pd.to_datetime(df[date_col])
    max_date = df[date_col].max().date()
    min_date = df[date_col].min().date()
    
    return min_date, max_date, min_date, max_date

@callback(
    Output('intraday-chart', 'figure'),
    Output('hourly-heatmap', 'figure'),
    Output('aht-time-chart', 'figure'),
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
    empty_fig = px.pie(title="No Data")
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or not start_date or not end_date:
        return empty_fig, empty_fig, empty_fig
        
    token = auth_state.get('token') if auth_state else None
    if not token:
        return empty_fig, empty_fig, empty_fig
        
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    
    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else None
    if not date_col or df.empty:
        return empty_fig, empty_fig, empty_fig

    df['DateCol'] = pd.to_datetime(df[date_col])
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
        return empty_fig, empty_fig, empty_fig

    df_current['Time'] = pd.to_datetime(df_current[ts_col]).dt.time
    df_current['TimeStr'] = df_current['Time'].astype(str)

    # Chart 1: Intraday Performance (Dual Axis)
    hourly_grp = df_current.groupby('TimeStr').sum(numeric_only=True).reset_index()
    
    denom = hourly_grp['Call Offered'] - hourly_grp['ABAN Calls in 10 Sec']
    hourly_grp['SL %'] = (hourly_grp['ACD Calls in 20 Sec'] / denom * 100).fillna(0)
    
    fig_intraday = go.Figure()
    # Add Bars for Call Volume
    fig_intraday.add_trace(go.Bar(
        x=hourly_grp['TimeStr'],
        y=hourly_grp['Call Offered'],
        name='Call Offered',
        marker_color='#3182ce',
        opacity=0.7,
        yaxis='y'
    ))
    # Add Line for Service Level
    fig_intraday.add_trace(go.Scatter(
        x=hourly_grp['TimeStr'],
        y=hourly_grp['SL %'],
        name='Service Level %',
        mode='lines+markers',
        line=dict(color='#38a169', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig_intraday.update_layout(
        template=get_plotly_template(),
        margin=dict(t=30, b=30, l=10, r=10),
        xaxis=dict(title='Time of Day'),
        yaxis=dict(title='Call Volume', side='left', showgrid=False),
        yaxis2=dict(title='Service Level %', side='right', overlaying='y', range=[0, 105], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Chart 2: Highest Abandonment by Language (Bar Chart)
    if 'Language' in df_current.columns:
        lang_aban = df_current.groupby('Language')['ABAN Calls'].sum().reset_index()
        lang_aban = lang_aban.sort_values('ABAN Calls', ascending=True)
        
        lang_aban['Plot Value'] = lang_aban['ABAN Calls'] + 1
        
        fig_heat = px.bar(lang_aban, x='Plot Value', y='Language', orientation='h',
                          color='Language', color_discrete_sequence=px.colors.qualitative.Vivid,
                          log_x=True,
                          hover_data={'Plot Value': False, 'ABAN Calls': True, 'Language': False},
                          labels={'ABAN Calls': 'Actual Abandoned Calls'})
        
        fig_heat.update_layout(
            template=get_plotly_template(),
            margin=dict(t=30, b=30, l=10, r=10),
            showlegend=False
        )
    else:
        fig_heat = px.pie(title="No Language Data")

    # Chart 3: AHT by Time of Day (Stacked Bar Chart)
    if all(c in df_current.columns for c in ['ACD Calls', 'ACD Time', 'ACW Time', 'Hold Time']):
        aht_grp = df_current.groupby('TimeStr').sum(numeric_only=True).reset_index()
        aht_grp['Talk Time'] = (aht_grp['ACD Time'] / aht_grp['ACD Calls']).fillna(0)
        aht_grp['Wrap Time'] = (aht_grp['ACW Time'] / aht_grp['ACD Calls']).fillna(0)
        aht_grp['Hold Time Avg'] = (aht_grp['Hold Time'] / aht_grp['ACD Calls']).fillna(0)
        
        fig_aht = go.Figure()
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Talk Time'], name='Talk Time', marker_color='#4299E1'))
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Wrap Time'], name='Wrap Time', marker_color='#48BB78'))
        fig_aht.add_trace(go.Bar(x=aht_grp['TimeStr'], y=aht_grp['Hold Time Avg'], name='Hold Time', marker_color='#ED8936'))
        
        fig_aht.update_layout(
            barmode='stack',
            template=get_plotly_template(),
            margin=dict(t=30, b=30, l=10, r=10),
            xaxis=dict(title='Time of Day'),
            yaxis=dict(title='Average Time (s)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    else:
        fig_aht = px.pie(title="No AHT Data")

    return fig_intraday, fig_heat, fig_aht

# CSV Export Callback
@callback(
    Output("download-dataframe-csv", "data", allow_duplicate=True),
    Input("btn-export-csv-hourly", "n_clicks"),
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
    if not n_clicks or not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref or not start_date or not end_date:
        return dash.no_update

    token = auth_state.get('token') if auth_state else None
    if not token: return dash.no_update
    
    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))
    if df.empty: return dash.no_update

    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else None
    if date_col:
        df['DateCol'] = pd.to_datetime(df[date_col])
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

# PDF and JPG Page Export Callbacks
dash.clientside_callback(
    dash.ClientsideFunction(
        namespace='clientside',
        function_name='export_pdf'
    ),
    Output('btn-export-pdf-hourly', 'title'), # Dummy output
    Input('btn-export-pdf-hourly', 'n_clicks'),
    prevent_initial_call=True
)

dash.clientside_callback(
    dash.ClientsideFunction(
        namespace='clientside',
        function_name='export_jpg'
    ),
    Output('btn-export-jpg-hourly', 'title'), # Dummy output
    Input('btn-export-jpg-hourly', 'n_clicks'),
    prevent_initial_call=True
)

# Individual Chart JPG Export Callbacks
for graph_id in ['intraday-chart', 'hourly-heatmap', 'aht-time-chart']:
    dash.clientside_callback(
        dash.ClientsideFunction(
            namespace='clientside',
            function_name='export_chart_jpg'
        ),
        Output(f"btn-download-{graph_id}", "title"), # Dummy output
        Input(f"btn-download-{graph_id}", "n_clicks"),
        State(graph_id, "id"),
        prevent_initial_call=True
    )
