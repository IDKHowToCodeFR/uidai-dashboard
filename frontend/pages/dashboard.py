import dash
from dash import html, dcc, callback, Input, Output
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody, Table
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
    Input('modality-filter', 'value')
)
def update_dashboard(data, modality_filter):
    df = pd.DataFrame(data)
    
    if df.empty:
        empty_fig = px.pie(title="No Data")
        return [], empty_fig, empty_fig, empty_fig, "No data available."
        
    # Apply filtering logic: if neither is selected or both are selected, show all data
    if modality_filter and len(modality_filter) > 0 and len(modality_filter) < 2:
        if 'Modality' in df.columns:
            df = df[df['Modality'].isin(modality_filter)]

    # Calculate KPIs
    total_auths = len(df)
    avg_processing_time = df['Processing_Time_ms'].mean() if 'Processing_Time_ms' in df.columns else 0
    success_rate = (len(df[df['Status'] == 'Success']) / total_auths * 100) if (total_auths > 0 and 'Status' in df.columns) else 0
    top_state = df['State'].mode()[0] if ('State' in df.columns and not df['State'].empty) else "N/A"

    kpis = [
        Col(make_kpi_card("Total Authentications", f"{total_auths:,}"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Success Rate", f"{success_rate:.1f}%"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Avg Processing Time", f"{avg_processing_time:.0f} ms"), width=12, sm=6, lg=3, className="mb-4"),
        Col(make_kpi_card("Top State", top_state), width=12, sm=6, lg=3, className="mb-4"),
    ]

    # Status Pie
    if 'Status' in df.columns:
        status_counts = df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.4, color_discrete_sequence=['#2c8c66', '#cd4239', '#f7a501'])
    else:
        fig_status = px.pie(title="No Status Data")
    fig_status.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))

    # State Bar
    if 'State' in df.columns:
        state_counts = df['State'].value_counts().reset_index()
        state_counts.columns = ['State', 'Count']
        fig_state = px.bar(state_counts, x='State', y='Count', color='State', color_discrete_sequence=px.colors.qualitative.Set2)
    else:
        fig_state = px.bar(title="No State Data")
    fig_state.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10), showlegend=False)

    # Time Hist
    if 'Processing_Time_ms' in df.columns:
        fig_time = px.histogram(df, x='Processing_Time_ms', nbins=20, color_discrete_sequence=['#2c84e0'])
    else:
        fig_time = px.histogram(title="No Processing Time Data")
    fig_time.update_layout(template=get_plotly_template(), margin=dict(t=30, b=30, l=10, r=10))

    # Table
    table = Table.from_dataframe(df.head(8), striped=True, bordered=False, hover=True, responsive=True, size="sm")

    return kpis, fig_status, fig_state, fig_time, table
