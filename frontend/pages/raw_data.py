import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from dash import dash_table
import pandas as pd

dash.register_page(__name__, path='/raw-data')

layout = html.Div([
    html.H3("Raw Data Explorer", className="mb-4", style={"color": "#23251d", "fontFamily": "'IBM Plex Sans', sans-serif", "fontWeight": "700"}),
    html.P("View, sort, and filter the raw IVRS call logs. Use the column headers to further filter data on this page.", className="text-muted mb-4"),
    
    html.Div(
        id='raw-data-table-container',
        className="custom-card shadow-sm bg-white p-4",
        style={"borderRadius": "8px", "border": "1px solid #bfc1b7"}
    )
], className="container-fluid py-4", style={"backgroundColor": "#eeefe9", "minHeight": "100vh"})

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
            df['temp_date'] = pd.to_datetime(df[date_col]).dt.date
            df = df[(df['temp_date'] >= pd.to_datetime(start_date).date()) & 
                    (df['temp_date'] <= pd.to_datetime(end_date).date())]
            df = df.drop('temp_date', axis=1)

    if df.empty:
        return html.Div("No data matches the selected filters.", className="text-center p-5 text-muted")

    # Round numeric columns for cleaner display
    import numpy as np
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        df[col] = df[col].round(2)

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
            'fontFamily': "'IBM Plex Sans', sans-serif",
            'fontSize': '14px',
            'color': '#4d4f46',
            'borderBottom': '1px solid #dcdfd2'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#23251d',
            'border': 'none',
            'borderBottom': '2px solid #bfc1b7'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#fcfdfb'
            }
        ],
        css=[{
            'selector': '.dash-table-tooltip',
            'rule': 'background-color: #23251d; color: white; border-radius: 4px;'
        }]
    )
