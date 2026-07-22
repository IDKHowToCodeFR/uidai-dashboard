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
            html.H6(title, className="utility-xs mb-2"),
            html.H3(value, className="mb-0 display-lg")
        ])
    ], className="custom-card h-100")

layout = Container([
    Row([
        Col([
            html.H2("IVRS Call Logs Overview", className="display-xl mb-4")
        ], width=12)
    ]),

    # KPI Row
    Row(id='kpi-row'),

    # Charts Row 1
    Row([
        Col([
            Card([
                CardHeader(html.Div("Call Status", className="heading-md")),
                CardBody(dcc.Graph(id='status-pie', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=5, className="mb-4"),

        Col([
            Card([
                CardHeader(html.Div("Volume by Region", className="heading-md")),
                CardBody(dcc.Graph(id='state-bar', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=7, className="mb-4"),
    ]),

    # Charts Row 2
    Row([
        Col([
            Card([
                CardHeader(html.Div("Call Duration Distribution (s)", className="heading-md")),
                CardBody(dcc.Graph(id='time-hist', config={'displayModeBar': False}))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4"),

        Col([
            Card([
                CardHeader(html.Div("Recent Calls", className="heading-md")),
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
    Input('date-picker-range', 'end_date')
)
def update_dashboard(data, modality_filter, start_date, end_date):
    df = pd.DataFrame(data)

    if df.empty:
        empty_fig = px.pie(title="No Data")
        return [], empty_fig, empty_fig, empty_fig, "No data available."

    # Demo Mock Data if real columns are missing
    if 'Company' not in df.columns:
        df['Company'] = df.get('Modality', 'Company A').map({'Biometric': 'Company A', 'Demographic': 'Company B'}).fillna('Company A')
    if 'Date' not in df.columns and 'Call Start Time' in df.columns:
        df['Date'] = pd.to_datetime(df['Call Start Time'])
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    # Apply Company Filter
    if modality_filter is not None:
        df = df[df['Company'].isin(modality_filter)]

    # Time Filter
    df_current = df.copy()

    if start_date and end_date:
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        df_current = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)].copy()

    df_combined = df_current

    # Calculate KPIs
    total_auths = len(df_current)
    avg_processing_time = df_current['Call Duration (seconds)'].mean() if 'Call Duration (seconds)' in df_current.columns else 0
    success_rate = (len(df_current[df_current['Resolution Status'] == 'Resolved']) / total_auths * 100) if (total_auths > 0 and 'Resolution Status' in df_current.columns) else 0
    top_state = df_current['Region'].mode()[0] if ('Region' in df_current.columns and not df_current['Region'].empty) else "N/A"

    def kpi_text(curr):
        return html.Div([f"{curr}"])

    kpis = [
        Col(make_kpi_card("Total Calls", kpi_text(total_auths)), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Resolution Rate", f"{success_rate:.1f}%"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Avg Call Duration", f"{avg_processing_time:.0f} s"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Top Region", top_state), width=12, sm=6, lg=3, className="mb-4"),
    ]

    # Status Pie (Current only)
    if 'Call Status' in df_current.columns:
        status_counts = df_current['Call Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.5, color_discrete_sequence=['#2c84e0', '#cd4239', '#f7a501'])
        fig_status.update_traces(textposition='inside', textinfo='percent+label', hoverinfo='label+percent+name', pull=[0.05]*len(status_counts))
    else:
        fig_status = px.pie(title="No Call Status Data")
    fig_status.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False)

    # State Bar
    if 'Region' in df_combined.columns:
        state_counts = df_combined.groupby('Region').size().reset_index(name='Count')
        state_counts = state_counts.sort_values(by='Count', ascending=False)
        fig_state = px.bar(state_counts, x='Region', y='Count', text='Count',
                           labels={'Count': 'Total Calls'})
        fig_state.update_traces(texttemplate='%{text:.2s}', textposition='outside', marker_line_width=1.5, marker_line_color="rgba(0,0,0,0.1)")
    else:
        fig_state = px.bar(title="No Region Data")
    fig_state.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False,
                            uniformtext_minsize=8, uniformtext_mode='hide')

    # Time Hist
    if 'Call Duration (seconds)' in df_combined.columns:
        fig_time = px.histogram(df_combined, x='Call Duration (seconds)', nbins=30, marginal='box')
        fig_time.update_traces(opacity=0.75)
    else:
        fig_time = px.histogram(title="No Duration Data")
    fig_time.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False)

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