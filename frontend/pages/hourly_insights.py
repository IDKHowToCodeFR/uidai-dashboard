import dash
from dash import html, dcc, callback, Input, Output, State
from dash_bootstrap_components import Container, Row, Col, Card, CardHeader, CardBody
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.theme import get_plotly_template

dash.register_page(__name__, path='/hourly', name='Hourly Insights')

layout = Container([
    Row([
        Col([
            html.Div([
                html.H2("Hourly Insights", className="display-xl mb-0"),
                html.Div([
                    html.Span("Select Date: ", className="text-muted small text-uppercase me-2 fw-bold"),
                    dcc.DatePickerSingle(
                        id='hourly-date-picker',
                        display_format='YYYY-MM-DD',
                        className="ms-2"
                    )
                ], className="d-flex align-items-center bg-white border rounded px-3 py-2 shadow-sm")
            ], className="d-flex justify-content-between align-items-center mb-4")
        ], width=12)
    ]),

    Row([
        Col([
            Card([
                CardHeader("Intraday Performance (Volume & Service Level)"),
                CardBody(dcc.Graph(id='intraday-chart', config={'displayModeBar': False}, style={'height': '400px'}))
            ], className="custom-card h-100")
        ], width=12, className="mb-4")
    ]),
    
    Row([
        Col([
            Card([
                CardHeader("Highest Abandonment by Language"),
                CardBody(dcc.Graph(id='hourly-heatmap', config={'displayModeBar': False}, style={'height': '400px'}))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4"),
        
        Col([
            Card([
                CardHeader("Average Handle Time (AHT) by Time of Day"),
                CardBody(dcc.Graph(id='aht-time-chart', config={'displayModeBar': False}, style={'height': '400px'}))
            ], className="custom-card h-100")
        ], width=12, lg=6, className="mb-4")
    ])
], fluid=True, className="px-4")


@callback(
    Output('hourly-date-picker', 'date'),
    Output('hourly-date-picker', 'min_date_allowed'),
    Output('hourly-date-picker', 'max_date_allowed'),
    Input('data-store', 'data')
)
def set_date_picker(data):
    if not data:
        return dash.no_update, dash.no_update, dash.no_update
    
    df = pd.DataFrame(data)
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
        
    if not date_col or df.empty:
        return dash.no_update, dash.no_update, dash.no_update
        
    df[date_col] = pd.to_datetime(df[date_col])
    max_date = df[date_col].max().date()
    min_date = df[date_col].min().date()
    
    return max_date, min_date, max_date

@callback(
    Output('intraday-chart', 'figure'),
    Output('hourly-heatmap', 'figure'),
    Output('aht-time-chart', 'figure'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('hourly-date-picker', 'date')
)
def update_hourly_insights(data, company_filter, language_filter, selected_date):
    if not data or not selected_date:
        empty_fig = px.pie(title="No Data")
        return empty_fig, empty_fig
        
    df = pd.DataFrame(data)
    
    date_col = 'Date' if 'Date' in df.columns else 'Timestamp' if 'Timestamp' in df.columns else None
    if not date_col:
        empty_fig = px.pie(title="No Data")
        return empty_fig, empty_fig

    df['DateCol'] = pd.to_datetime(df[date_col]).dt.date
    target_date = pd.to_datetime(selected_date).date()
    
    df_current = df[df['DateCol'] == target_date].copy()
    
    # Apply global filters
    if company_filter and 'Company' in df_current.columns:
        df_current = df_current[df_current['Company'].isin(company_filter)]
    if language_filter and 'Language' in df_current.columns:
        df_current = df_current[df_current['Language'].isin(language_filter)]
        
    if df_current.empty or 'Call Timestamp' not in df_current.columns:
        empty_fig = px.pie(title="No Data or Missing Timestamp Info")
        return empty_fig, empty_fig, empty_fig

    df_current['Time'] = pd.to_datetime(df_current['Call Timestamp']).dt.time
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
