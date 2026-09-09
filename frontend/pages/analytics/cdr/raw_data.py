import dash
from dash import html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import numpy as np
import pandas as pd
from frontend.shared.api_client import get_dataframe

dash.register_page(__name__, path='/cdr/raw_data', name='CDR Raw Data Explorer')

layout = html.Div([
    html.Div([
        html.H3("Raw Data Explorer", className="display-xl mb-0"),
        html.P("View, sort, and filter the raw CDR call logs. Use the column headers to further filter data on this page.", className="text-muted mb-4 mt-2"),
    ]),
    html.Div(
        id='cdr-raw-data-table-container',
        className="custom-card shadow-sm bg-white p-4",
        style={"borderRadius": "16px", "border": "1px solid #e2e8f0"}
    )
], className="container-fluid py-4")


@callback(
    Output('cdr-raw-data-table-container', 'children'),
    Input('data-store', 'data'),
    Input('company-filter', 'value'),
    Input('language-filter', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    State('auth-state', 'data')
)
def update_table(data_ref, companies, languages, start_date, end_date, auth_state):
    if not data_ref or not isinstance(data_ref, dict) or 'filename' not in data_ref:
        return html.Div("No data available. Please upload a file.", className="text-center p-5 text-muted")

    token = auth_state.get('token') if auth_state else None
    if not token:
        return html.Div("Unauthorized.", className="text-center p-5 text-muted")

    df = get_dataframe(token, data_ref['filename'], data_ref.get('impersonate'))

    if companies and 'Company' in df.columns:
        df = df[df['Company'].isin(companies)]

    if languages and 'Language' in df.columns:
        df = df[df['Language'].isin(languages)]

    if start_date and not end_date: end_date = start_date
    if start_date and end_date:
        date_col = None
        if 'segstart' in df.columns:
            date_col = 'segstart'
        elif 'Timestamp' in df.columns:
            date_col = 'Timestamp'
        elif 'Date' in df.columns:
            date_col = 'Date'

        if date_col in df.columns:
            parsed_dates = pd.to_datetime(df[date_col], errors='coerce')
            # Bridge to show the standard format in the UI table
            df[date_col] = parsed_dates.dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[date_col])
            temp_date = parsed_dates.dt.date
                
            valid_mask = temp_date.notna()
            df = df[valid_mask]
            temp_date = temp_date[valid_mask]
            df = df[(temp_date >= pd.to_datetime(start_date).date()) &
                    (temp_date <= pd.to_datetime(end_date).date())]

    if df.empty:
        return html.Div("No data matches the selected filters.", className="text-center p-5 text-muted")

    # Round numeric columns for cleaner display
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].round(2)
    
    # Format all possible date columns for the UI bridge
    for col in ['segstart', 'segstop', 'segstartutc', 'segstoputc', 'Date']:
        if col in df.columns:
            # Reformat so YYYY-MM-DD HH:MM:SS is strictly displayed to user
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[col])

    return dag.AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=[{"field": i} for i in df.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        style={"height": "600px", "width": "100%"},
        dashGridOptions={"pagination": True, "paginationPageSize": 50}
    )
