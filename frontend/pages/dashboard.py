import dash
from dash import html, dcc, callback, Input, Output
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
from utils.theme import get_plotly_template

dash.register_page(__name__, path='/', name='Dashboard')

def make_kpi_card(title, value):
    return Card([
        CardBody([
            html.H6(title, className="text-muted text-uppercase mb-2", style={"fontSize": "12px", "fontWeight": "700", "letterSpacing": "0.5px"}),
            html.H3(value, className="mb-0 display-lg")
        ])
    ], className="custom-card h-100")

layout = Container([
    Row([
        Col([
            html.H2("Authentication Overview", className="display-xl mb-4")
        ], width=12)
    ]),

    # KPI Row
    Row(id='kpi-row'),

    # Charts Row 1
    Row([
        Col([
            Card([
                CardHeader("Authentication Status"),
                CardBody(dcc.Graph(id='status-pie', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=5, className="mb-4"),

        Col([
            Card([
                CardHeader("Volume by State"),
                CardBody(dcc.Graph(id='state-bar', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=7, className="mb-4"),
    ]),

    # Charts Row 2
    Row([
        Col([
            Card([
                CardHeader("Processing Time Distribution (ms)"),
                CardBody(dcc.Graph(id='time-hist', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4"),

        Col([
            Card([
                CardHeader("Recent Authentication Requests"),
                CardBody([
                    html.Div(id='recent-table-container')
                ])
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4")
    ])
], fluid=True, className="px-4")

@callback(
    Output('kpi-row', 'children'),
    Output('status-pie', 'figure'),
    Output('state-bar', 'figure'),
    Output('time-hist', 'figure'),
    Output('recent-table-container', 'children'),
    Input('data-store', 'data'),
    Input('modality-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('compare-toggle', 'value')
)
def update_dashboard(data, modality_filter, start_date, end_date, compare):
    df = pd.DataFrame(data)

    if df.empty:
        empty_fig = px.pie(title="No Data")
        return [], empty_fig, empty_fig, empty_fig, "No data available."

    # Demo Mock Data if real columns are missing
    if 'Company' not in df.columns:
        df['Company'] = df.get('Modality', 'Company A').map({'Biometric': 'Company A', 'Demographic': 'Company B'}).fillna('Company A')
    if 'Date' not in df.columns:
        import numpy as np
        df['Date'] = pd.to_datetime('today') - pd.to_timedelta(np.random.randint(0, 60, size=len(df)), unit='D')
    else:
        df['Date'] = pd.to_datetime(df['Date'])

    # Apply Company Filter
    if modality_filter and len(modality_filter) > 0 and len(modality_filter) < 2:
        df = df[df['Company'].isin(modality_filter)]

    # Time Filter & Compare
    df_current = df.copy()
    df_prev = pd.DataFrame()

    if start_date and end_date:
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        df_current = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)].copy()

        if compare:
            delta = end_dt - start_dt
            prev_start, prev_end = start_dt - delta - pd.Timedelta(days=1), end_dt - delta - pd.Timedelta(days=1)
            df_prev = df[(df['Date'] >= prev_start) & (df['Date'] <= prev_end)].copy()
            df_current['Period'] = 'Current'
            df_prev['Period'] = 'Previous'
            df_combined = pd.concat([df_current, df_prev])
        else:
            df_current['Period'] = 'Current'
            df_combined = df_current
    else:
        df_current['Period'] = 'Current'
        df_combined = df_current

    # Calculate KPIs
    total_auths = len(df_current)
    avg_processing_time = df_current['Processing_Time_ms'].mean() if 'Processing_Time_ms' in df_current.columns else 0
    success_rate = (len(df_current[df_current['Status'] == 'Success']) / total_auths * 100) if (total_auths > 0 and 'Status' in df_current.columns) else 0
    top_state = df_current['State'].mode()[0] if ('State' in df_current.columns and not df_current['State'].empty) else "N/A"

    def kpi_text(curr, prev_df, metric_func):
        if not compare or prev_df.empty: return f"{curr}"
        prev = metric_func(prev_df)
        diff = curr - prev if isinstance(curr, (int, float)) else 0
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "−")
        color = "#10b981" if diff > 0 else "#ef4444"  # --color-success / --color-danger
        return html.Div([f"{curr} ", html.Span(f"({arrow} vs Prev)", style={"color": color, "fontSize": "14px"})])

    kpis = [
        Col(make_kpi_card("Total Authentications", kpi_text(total_auths, df_prev, len)), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Success Rate", f"{success_rate:.1f}%"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Avg Processing Time", f"{avg_processing_time:.0f} ms"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Top State", top_state), width=12, sm=6, lg=3, className="mb-4"),
    ]

    # Status Pie (Current only)
    if 'Status' in df_current.columns:
        status_counts = df_current['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.4, color_discrete_sequence=['#2563eb', '#ef4444', '#f59e0b'])
    else:
        fig_status = px.pie(title="No Status Data")
    fig_status.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))

    # State Bar (Comparative)
    if 'State' in df_combined.columns:
        state_counts = df_combined.groupby(['State', 'Period']).size().reset_index(name='Count')
        fig_state = px.bar(state_counts, x='State', y='Count', color='Period', barmode='group',
                           labels={'Period': 'Comparison Period', 'Count': 'Total Authentications'})
    else:
        fig_state = px.bar(title="No State Data")
    fig_state.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True,
                            legend_title_text='Data Period')

    # Time Hist (Comparative)
    if 'Processing_Time_ms' in df_combined.columns:
        fig_time = px.histogram(df_combined, x='Processing_Time_ms', color='Period', nbins=20, barmode='overlay',
                                labels={'Period': 'Comparison Period', 'Processing_Time_ms': 'Processing Time (ms)'})
    else:
        fig_time = px.histogram(title="No Processing Time Data")
    fig_time.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=True,
                           legend_title_text='Data Period')

    # Table
    table_df = df_current.copy()

    table = dag.AgGrid(
        rowData=table_df.head(100).to_dict("records"),
        columnDefs=[{"field": i} for i in table_df.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        style={"height": "400px", "width": "100%"},
        dashGridOptions={"pagination": True, "paginationPageSize": 10}
    )

    return kpis, fig_status, fig_state, fig_time, table