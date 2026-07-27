import dash
from dash import html, dcc, callback, Input, Output
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
from utils.theme import get_plotly_template

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
        ], width=12)
    ]),

    # KPI Row
    Row(id='kpi-row'),

    # Charts Row 1
    Row([
        Col([
            Card([
                CardHeader("Service Level Trend (%)"),
                CardBody(dcc.Graph(id='sl-trend', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=7, className="mb-4"),

        Col([
            Card([
                CardHeader("Volume by Language"),
                CardBody(dcc.Graph(id='lang-pie', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=5, className="mb-4"),
    ]),

    # Charts Row 2
    Row([
        Col([
            Card([
                CardHeader(html.Div([
                    html.Span("AHT vs Abandonment (Daily)"),
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
                ])),
                CardBody(dcc.Graph(id='aht-scatter', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4"),

        Col([
            Card([
                CardHeader("Daily SLA & Abandonment Log"),
                CardBody([
                    html.Div(id='recent-table-container')
                ])
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4")
    ])
], fluid=True, className="px-4")

@callback(
    Output('kpi-row', 'children'),
    Output('sl-trend', 'figure'),
    Output('lang-pie', 'figure'),
    Output('aht-scatter', 'figure'),
    Output('recent-table-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('aht-dropdown', 'value')
)
def update_dashboard(data, company_filter, language_filter, start_date, end_date, aht_metric):
    df = pd.DataFrame(data)

    if df.empty:
        empty_fig = px.pie(title="No Data")
        return [], empty_fig, empty_fig, empty_fig, "No data available."

    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
    elif 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'

    if date_col:
        df['Date'] = pd.to_datetime(df[date_col])
    else:
        df['Date'] = pd.NaT

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
        empty_fig = px.pie(title="No Data for Selection")
        return [], empty_fig, empty_fig, empty_fig, "No data available."

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

    # Chart 3: AHT vs Abandonment Scatter
    if all(c in df_current.columns for c in ['Date', 'Company', 'Call Offered', 'ABAN Calls', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        daily_comp_grp = df_current.groupby(['Date', 'Company']).sum(numeric_only=True).reset_index()
        
        daily_comp_grp['Abandon Rate (%)'] = (daily_comp_grp['ABAN Calls'] / daily_comp_grp['Call Offered'] * 100).fillna(0)
        den = daily_comp_grp['ACD Calls']
        
        daily_comp_grp['Talk Time'] = (daily_comp_grp['ACD Time'] / den).fillna(0)
        daily_comp_grp['Wrap Time'] = (daily_comp_grp['ACW Time'] / den).fillna(0)
        daily_comp_grp['Hold Time Avg'] = (daily_comp_grp['Hold Time'] / den).fillna(0)
        daily_comp_grp['Total AHT'] = daily_comp_grp['Talk Time'] + daily_comp_grp['Wrap Time'] + daily_comp_grp['Hold Time Avg']
        
        # Determine fallback if empty selection
        if daily_comp_grp.empty:
            fig_agent = px.scatter(title="No Data")
        else:
            fig_agent = px.scatter(daily_comp_grp, x='Abandon Rate (%)', y=aht_metric, color='Company',
                                   hover_name='Date', size='Call Offered',
                                   color_discrete_sequence=px.colors.qualitative.Set1,
                                   labels={aht_metric: f'{aht_metric} (s)'})
            if aht_metric == 'Total AHT':
                fig_agent.add_hline(y=240, line_dash="dash", line_color="red", annotation_text="SLA 240s")
    else:
        fig_agent = px.scatter(title="No Company AHT Data")
    fig_agent.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True)

    # Table: Daily SLA Log
    import numpy as np
    if all(c in df_current.columns for c in ['Date', 'Company', 'Call Offered', 'ABAN Calls', 'ACD Calls in 20 Sec', 'ABAN Calls in 10 Sec', 'ACD Time', 'ACW Time', 'Hold Time', 'ACD Calls']):
        log_grp = df_current.groupby(['Date', 'Company']).sum(numeric_only=True).reset_index()
        
        log_grp['Abandon Rate (%)'] = (log_grp['ABAN Calls'] / log_grp['Call Offered'] * 100).fillna(0).round(1)
        
        den_sl = log_grp['Call Offered'] - log_grp['ABAN Calls in 10 Sec']
        log_grp['Service Level (%)'] = np.where(den_sl > 0, (log_grp['ACD Calls in 20 Sec'] / den_sl * 100), 0)
        log_grp['Service Level (%)'] = log_grp['Service Level (%)'].round(1)
        
        den_aht = log_grp['ACD Calls']
        num_aht = log_grp['ACD Time'] + log_grp.get('ACW Time', 0) + log_grp.get('Hold Time', 0)
        log_grp['Total AHT (s)'] = np.where(den_aht > 0, (num_aht / den_aht), 0)
        log_grp['Total AHT (s)'] = log_grp['Total AHT (s)'].round(1)
        
        log_grp['DateStr'] = log_grp['Date'].dt.strftime('%Y-%m-%d')
        
        log_table_df = log_grp[['DateStr', 'Company', 'Call Offered', 'Abandon Rate (%)', 'Service Level (%)', 'Total AHT (s)']].sort_values(by='Abandon Rate (%)', ascending=False)
        log_table_df.rename(columns={'DateStr': 'Date'}, inplace=True)
        
        table = dag.AgGrid(
            rowData=log_table_df.to_dict("records"),
            columnDefs=[
                {"field": "Date"},
                {"field": "Company"},
                {"field": "Call Offered", "type": "numericColumn"},
                {"field": "Abandon Rate (%)", "valueFormatter": {"function": "d3.format('.1f')(params.value) + '%'"}},
                {"field": "Service Level (%)", "valueFormatter": {"function": "d3.format('.1f')(params.value) + '%'"}},
                {"field": "Total AHT (s)", "valueFormatter": {"function": "d3.format('.1f')(params.value) + 's'"}}
            ],
            defaultColDef={"sortable": True, "filter": True, "resizable": True},
            className="ag-theme-alpine",
            style={"height": "400px", "width": "100%"},
            dashGridOptions={"pagination": True, "paginationPageSize": 10}
        )
    else:
        # Fallback
        table_df = df_current.copy()
        if 'Date' in table_df.columns:
            table_df['Date'] = table_df['Date'].dt.strftime('%Y-%m-%d')
            
        table = dag.AgGrid(
            rowData=table_df.head(100).to_dict("records"),
            columnDefs=[{"field": i} for i in table_df.columns],
            defaultColDef={"sortable": True, "filter": True, "resizable": True},
            className="ag-theme-alpine",
            style={"height": "400px", "width": "100%"},
            dashGridOptions={"pagination": True, "paginationPageSize": 10}
        )

    return kpis, fig_sl, fig_lang, fig_agent, table