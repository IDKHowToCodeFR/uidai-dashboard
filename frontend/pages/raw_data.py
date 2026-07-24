import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from dash import dash_table
import numpy as np
import pandas as pd

dash.register_page(__name__, path='/raw-data')

layout = html.Div([
    html.H3("Raw Data Explorer", className="display-xl mb-4"),
    html.P("View, sort, and filter the raw IVRS call logs. Use the column headers to further filter data on this page.", className="text-muted mb-4"),

    html.Div(
        id='raw-data-table-container',
        className="custom-card shadow-sm bg-white p-4",
        style={"borderRadius": "16px", "border": "1px solid #e2e8f0"}
    )
], className="container-fluid py-4")


@callback(
    Output('raw-data-table-container', 'children'),
    Input('data-store', 'data'),
    Input('modality-filter', 'value'),
    Input('queue-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_table(data, companies, queues, languages, start_date, end_date):
    if not data:
        return html.Div("No data available. Please upload a file.", className="text-center p-5 text-muted")

    df = pd.DataFrame(data)

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]

    if queues and 'Queue Name' in df.columns:
        df = df[df['Queue Name'].isin(queues)]

    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if start_date and end_date:
        date_col = 'Timestamp' if 'Timestamp' in df.columns else 'Call Start Time'
        if date_col in df.columns:
            temp_date = pd.to_datetime(df[date_col]).dt.date
            df = df[(temp_date >= pd.to_datetime(start_date).date()) &
                    (temp_date <= pd.to_datetime(end_date).date())]

    if df.empty:
        return html.Div("No data matches the selected filters.", className="text-center p-5 text-muted")

    # Round numeric columns for cleaner display
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].round(2)

    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns],
        page_size=20,
        sort_action="native",
        filter_action="native",
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '12px',
            'fontFamily': "'Inter', sans-serif",
            'fontSize': '14px',
            'color': '#334155',
            'borderBottom': '1px solid #e2e8f0'
        },
        style_header={
            'backgroundColor': '#f8fafc',
            'fontWeight': '600',
            'color': '#0f172a',
            'border': 'none',
            'borderBottom': '2px solid #e2e8f0'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8fafc'
            }
        ],
        css=[{
            'selector': '.dash-table-tooltip',
            'rule': 'background-color: #1e293b; color: white; border-radius: 8px;'
        }]
    )