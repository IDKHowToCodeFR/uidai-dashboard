import dash
from dash import html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import numpy as np
import pandas as pd
from frontend.utils.api import get_dataframe

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

    if start_date and end_date:
        date_col = None
        if 'Timestamp' in df.columns:
            date_col = 'Timestamp'
        elif 'Date' in df.columns:
            date_col = 'Date'
        elif 'Call Start Time' in df.columns:
            date_col = 'Call Start Time'

        if date_col in df.columns:
            temp_date = pd.to_datetime(df[date_col]).dt.date
            df = df[(temp_date >= pd.to_datetime(start_date).date()) &
                    (temp_date <= pd.to_datetime(end_date).date())]

    if df.empty:
        return html.Div("No data matches the selected filters.", className="text-center p-5 text-muted")

    # Round numeric columns for cleaner display
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].round(2)

    return dag.AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=[{"field": i} for i in df.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        style={"height": "600px", "width": "100%"},
        dashGridOptions={"pagination": True, "paginationPageSize": 50}
    )