import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.theme import get_plotly_template, make_header_with_download, make_export_dropdown, wrap_graph_with_download
import dash_bootstrap_components as dbc

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

layout = Container([
    Row([
        Col([
            html.H2("Call Center Performance", className="display-xl mb-4")
        ], width=8),
        Col([
            make_export_dropdown("dashboard")
        ], width=4, className="d-flex align-items-center justify-content-end mb-4")
    ]),

    # KPI Row
    Row(id='kpi-row'),

    # Charts Row 1
    Row([
        Col([
            Card([
                CardHeader(make_header_with_download("Service Level Trend (%)", "sl-trend")),
                CardBody(wrap_graph_with_download("sl-trend", dcc.Graph(id='sl-trend', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, lg=7, className="mb-4"),

        Col([
            Card([
                CardHeader(make_header_with_download("Volume by Language", "lang-pie")),
                CardBody(wrap_graph_with_download("lang-pie", dcc.Graph(id='lang-pie', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, lg=5, className="mb-4"),
    ]),

    # Charts Row 2: Histograms
    Row([
        Col([
            Card([
                CardHeader(make_header_with_download("Talk Time Distribution (s)", "talk-hist")),
                CardBody(wrap_graph_with_download("talk-hist", dcc.Graph(id='talk-hist', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, lg=4, className="mb-4"),

        Col([
            Card([
                CardHeader(make_header_with_download("Wrap Time (ACW) Distribution (s)", "wrap-hist")),
                CardBody(wrap_graph_with_download("wrap-hist", dcc.Graph(id='wrap-hist', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, lg=4, className="mb-4"),
        
        Col([
            Card([
                CardHeader(make_header_with_download("Hold Time Distribution (s)", "hold-hist")),
                CardBody(wrap_graph_with_download("hold-hist", dcc.Graph(id='hold-hist', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, lg=4, className="mb-4")
    ]),

    # Charts Row 3: Intraday Performance
    Row([
        Col([
            Card([
                CardHeader(make_header_with_download("Average Intraday Performance (Volume & SL)", "intraday-chart-overall")),
                CardBody(wrap_graph_with_download("intraday-chart-overall", dcc.Graph(id='intraday-chart-overall', config={'displayModeBar': False}, style={'height': '400px'})))
            ], className="custom-card h-100")
        ], width=12, className="mb-4")
    ]),

    # Charts Row 4: Scatter Plot
    Row([
        Col([
            Card([
                CardHeader(html.Div([
                    html.Span("Company Performance Comparison"),
                    dcc.Dropdown(
                        id="aht-dropdown",
                        options=[
                            {'label': 'Total AHT', 'value': 'Total AHT'},
                            {'label': 'Talk Time', 'value': 'Talk Time'},
                            {'label': 'Hold Time', 'value': 'Hold Time Avg'},
                            {'label': 'Wrap Time', 'value': 'Wrap Time'},
                        ],
                        value='Total AHT',
                        clearable=False,
                        style={"width": "180px", "display": "inline-block", "float": "right", "marginTop": "-5px"}
                    )
                ], className="d-flex justify-content-between align-items-center w-100")),
                CardBody(wrap_graph_with_download("aht-line-chart", dcc.Graph(id='aht-line-chart', config={'displayModeBar': False})))
            ], className="custom-card h-100")
        ], width=12, className="mb-4")
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
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('aht-dropdown', 'value')
)
def update_dashboard(data, company_filter, language_filter, start_date, end_date, aht_metric):
    df = pd.DataFrame(data)

    empty_fig = px.pie(title="No Data")
    if df.empty:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    date_candidates = ['Timestamp', 'Call Timestamp', 'Date', 'Call Start Time']
    df['Date'] = pd.NaT
    for col in date_candidates:
        if col in df.columns:
            df['Date'] = df['Date'].fillna(pd.to_datetime(df[col], errors='coerce'))
    
    date_col = 'Date' if not df['Date'].isna().all() else None

    # Apply Filters
    if company_filter and 'Company' in df.columns:
        df = df[df['Company'].isin(company_filter)]
    if language_filter and 'Language' in df.columns:
        df = df[df['Language'].isin(language_filter)]

    df_current = df.copy()
    if start_date and end_date and date_col:
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        df_current = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)].copy()
        
    if df_current.empty:
        return [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    # Calculate KPIs
    if 'Call Offered' in df_current.columns:
        total_calls = df_current['Call Offered'].sum()
    else:
        total_calls = len(df_current)
        
    # Service Level (Overall)
    overall_sl = 0
    sl_status = "neutral"
    if all(c in df_current.columns for c in ['ACD Calls in 20 Sec', 'Call Offered', 'ABAN Calls in 10 Sec']):
        num = df_current['ACD Calls in 20 Sec'].sum()
        den = df_current['Call Offered'].sum() - df_current['ABAN Calls in 10 Sec'].sum()
        overall_sl = (num / den * 100) if den > 0 else 0
        sl_status = "Good" if overall_sl > 85 else "Penalty"

    # AHT (Overall)
    overall_aht = 0
    aht_status = "neutral"
    if all(c in df_current.columns for c in ['ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        num = df_current['ACD Time'].sum() + df_current['ACW Time'].sum() + df_current['Hold Time'].sum()
        den = df_current['ACD Calls'].sum()
        overall_aht = (num / den) if den > 0 else 0
        aht_status = "Good" if overall_aht <= 240 else "Penalty"

    # Avg Hold Time (Overall)
    overall_hold = 0
    hold_status = "neutral"
    if 'Hold Time' in df_current.columns and 'ACD Calls' in df_current.columns:
        num = df_current['Hold Time'].sum()
        den = df_current['ACD Calls'].sum()
        overall_hold = (num / den) if den > 0 else 0
        hold_status = "Good" if overall_hold <= 20 else "Penalty"

    # Abandonment Rate
    aban_rate = 0
    if 'ABAN Calls' in df_current.columns and total_calls > 0:
        aban_rate = (df_current['ABAN Calls'].sum() / total_calls) * 100

    kpis = [
        Col(make_kpi_card("Total Calls", f"{int(total_calls):,}"), className="col-6 col-lg mb-4"),
        Col(make_kpi_card("Service Level", f"{overall_sl:.1f}%", sl_status), className="col-6 col-lg mb-4"),
        Col(make_kpi_card("Abandon Rate", f"{aban_rate:.1f}%"), className="col-6 col-lg mb-4"),
        Col(make_kpi_card("Avg Handle Time", f"{overall_aht:.0f}s", aht_status), className="col-6 col-lg mb-4"),
        Col(make_kpi_card("Avg Hold Time", f"{overall_hold:.0f}s", hold_status), className="col-6 col-lg mb-4"),
    ]

    # Chart 1: SL Trend
    if all(c in df_current.columns for c in ['Date', 'ACD Calls in 20 Sec', 'Call Offered', 'ABAN Calls in 10 Sec']):
        daily_grp = df_current.groupby('Date').sum(numeric_only=True).reset_index()
        denom = daily_grp['Call Offered'] - daily_grp['ABAN Calls in 10 Sec']
        daily_grp['SL %'] = (daily_grp['ACD Calls in 20 Sec'] / denom * 100).fillna(0)
        
        fig_sl = px.line(daily_grp, x='Date', y='SL %')
        fig_sl.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="85% Target")
    else:
        fig_sl = px.line(title="No SL Data")
    fig_sl.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))

    # Chart 2: Language Pie
    if 'Language' in df_current.columns and 'Call Offered' in df_current.columns:
        lang_grp = df_current.groupby('Language')['Call Offered'].sum().reset_index()
        fig_lang = px.pie(lang_grp, names='Language', values='Call Offered', hole=0.6,
                          color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_lang.update_traces(textposition='inside', textinfo='percent+label', hoverinfo='label+value',
                               marker=dict(line=dict(color='#ffffff', width=2)))
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
    else:
        fig_lang = px.pie(title="No Language Data")
        fig_lang.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False)

    # Chart 3, 4, 5: Histograms
    if all(c in df_current.columns for c in ['ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        df_valid = df_current[df_current['ACD Calls'] > 0].copy()
        
        df_valid['Talk Time'] = df_valid['ACD Time'] / df_valid['ACD Calls']
        df_valid['Wrap Time'] = df_valid['ACW Time'] / df_valid['ACD Calls']
        df_valid['Hold Time Avg'] = df_valid['Hold Time'] / df_valid['ACD Calls']
        
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

    # Chart 6: Intraday Performance (Averaged across days)
    if 'Date' in df_current.columns and not df_current['Date'].isna().all():
        # Extract just the time part for grouping
        df_current['Time'] = df_current['Date'].dt.time
        intraday_grp = df_current.groupby(['Date', 'Time']).sum(numeric_only=True).reset_index()
        # Now average across days for each Time
        avg_intraday = intraday_grp.groupby('Time').mean(numeric_only=True).reset_index()
        avg_intraday['TimeStr'] = avg_intraday['Time'].astype(str)
        
        denom_in = avg_intraday['Call Offered'] - avg_intraday['ABAN Calls in 10 Sec']
        avg_intraday['SL %'] = (avg_intraday['ACD Calls in 20 Sec'] / denom_in * 100).fillna(0)
        
        fig_intra = go.Figure()
        fig_intra.add_trace(go.Bar(
            x=avg_intraday['TimeStr'], y=avg_intraday['Call Offered'],
            name='Avg Volume', marker_color='#3182ce', opacity=0.7, yaxis='y'
        ))
        fig_intra.add_trace(go.Scatter(
            x=avg_intraday['TimeStr'], y=avg_intraday['SL %'],
            name='Avg SL %', mode='lines+markers', line=dict(color='#38a169', width=2), yaxis='y2'
        ))
        fig_intra.update_layout(
            template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10),
            xaxis=dict(title='Time of Day'),
            yaxis=dict(title='Avg Volume', side='left', showgrid=False),
            yaxis2=dict(title='Avg SL %', side='right', overlaying='y', range=[0, 105], showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    else:
        fig_intra = px.line(title="No Timestamp Data")

    # Chart 7: Company Performance Comparison Line Chart
    if all(c in df_current.columns for c in ['Date', 'Company', 'Call Offered', 'ABAN Calls', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        daily_comp_grp = df_current.groupby(['Date', 'Company']).sum(numeric_only=True).reset_index()
        
        daily_comp_grp['Abandon Rate (%)'] = (daily_comp_grp['ABAN Calls'] / daily_comp_grp['Call Offered'] * 100).fillna(0)
        den = daily_comp_grp['ACD Calls']
        
        daily_comp_grp['Talk Time'] = (daily_comp_grp['ACD Time'] / den).fillna(0)
        daily_comp_grp['Wrap Time'] = (daily_comp_grp['ACW Time'] / den).fillna(0)
        daily_comp_grp['Hold Time Avg'] = (daily_comp_grp['Hold Time'] / den).fillna(0)
        daily_comp_grp['Total AHT'] = daily_comp_grp['Talk Time'] + daily_comp_grp['Wrap Time'] + daily_comp_grp['Hold Time Avg']
        
        if daily_comp_grp.empty:
            fig_agent = px.line(title="No Data")
        else:
            fig_agent = px.line(daily_comp_grp, x='Date', y=aht_metric, color='Company',
                                markers=True,
                                color_discrete_sequence=px.colors.qualitative.Set1,
                                labels={aht_metric: f'{aht_metric} (s)'})
            if aht_metric == 'Total AHT':
                fig_agent.add_hline(y=240, line_dash="dash", line_color="red", annotation_text="SLA 240s")
    else:
        fig_agent = px.line(title="No Company AHT Data")
    fig_agent.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True)

    return kpis, fig_sl, fig_lang, fig_talk, fig_wrap, fig_hold, fig_intra, fig_agent

# CSV Export Callback
@callback(
    Output("download-dataframe-csv", "data", allow_duplicate=True),
    Input("btn-export-csv-dashboard", "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True
)
def export_csv_dashboard(n_clicks, data, company_filter, language_filter, start_date, end_date):
    if not n_clicks or not data:
        return dash.no_update
    df = pd.DataFrame(data)
    
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
    dash.ClientsideFunction(
        namespace='clientside',
        function_name='export_pdf'
    ),
    Output('btn-export-pdf-dashboard', 'title'), # Dummy output
    Input('btn-export-pdf-dashboard', 'n_clicks'),
    prevent_initial_call=True
)

dash.clientside_callback(
    dash.ClientsideFunction(
        namespace='clientside',
        function_name='export_jpg'
    ),
    Output('btn-export-jpg-dashboard', 'title'), # Dummy output
    Input('btn-export-jpg-dashboard', 'n_clicks'),
    prevent_initial_call=True
)

# Individual Chart JPG Export Callbacks
for graph_id in ['sl-trend', 'lang-pie', 'talk-hist', 'wrap-hist', 'hold-hist', 'intraday-chart-overall', 'aht-line-chart']:
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