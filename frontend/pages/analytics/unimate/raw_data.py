import dash
from dash import html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import numpy as np
import pandas as pd
from frontend.shared.api_client import get_dataframe

dash.register_page(__name__, path='/unimate/raw_data', name='UniMate Raw Data Explorer')

layout = html.Div([
    html.Div([
        html.H3("Raw Data Explorer", className="display-xl mb-0"),
        html.P("View, sort, and filter the raw UniMate authentication logs. Use the column headers to further filter data on this page.", className="text-muted mb-4 mt-2"),
    ]),
    html.Div(
        id='unimate-raw-data-table-container',
        className="custom-card shadow-sm bg-white p-4",
        style={"borderRadius": "16px", "border": "1px solid #e2e8f0"}
    )
], className="container-fluid py-4")


@callback(
    Output('unimate-raw-data-table-container', 'children'),
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

    if df is None or df.empty:
        return html.Div("No data available.", className="text-center p-5 text-muted")

    mask = pd.Series(True, index=df.index)

    if companies and 'Company' in df.columns:
        mask = mask & df['Company'].isin(companies)

    if languages and 'Language' in df.columns:
        mask = mask & df['Language'].isin(languages)

    date_col = None
    if 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'
    elif 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'

    if date_col in df.columns:
        df['Temp_Date'] = pd.to_datetime(df[date_col], errors='coerce')
        if start_date and not end_date: end_date = start_date
        if start_date and end_date and not df['Temp_Date'].isna().all():
            s = pd.to_datetime(start_date)
            e = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            mask = mask & (df['Temp_Date'] >= s) & (df['Temp_Date'] < e)

    df_filtered = df[mask].copy()

    if df_filtered.empty:
        return html.Div("No data matches the selected filters.", className="text-center p-5 text-muted")

    if 'Temp_Date' in df_filtered.columns:
        df_filtered = df_filtered.drop(columns=['Temp_Date'])

    # Round numeric columns for cleaner display
    numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns
    df_filtered[numeric_cols] = df_filtered[numeric_cols].round(2)

    # Convert Authentication to more readable string format
    if 'Authentication' in df_filtered.columns:
        df_filtered['Authentication'] = np.where(
            df_filtered['Authentication'].astype(str).str.lower().isin(['true', '1', '1.0']), 
            "Authenticated", 
            "Not Authenticated"
        )

    # Format Date and Call Timestamp for display
    if 'Call Start Time' in df_filtered.columns:
        df_filtered['Call Start Time'] = pd.to_datetime(df_filtered['Call Start Time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'Call End Time' in df_filtered.columns:
        df_filtered['Call End Time'] = pd.to_datetime(df_filtered['Call End Time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'Date' in df_filtered.columns:
        df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    if 'Call Timestamp' in df_filtered.columns:
        df_filtered['Call Timestamp'] = pd.to_datetime(df_filtered['Call Timestamp'], errors='coerce').dt.strftime('%H:%M:%S')

    return dag.AgGrid(
        rowData=df_filtered.to_dict("records"),
        columnDefs=[{"field": i} for i in df_filtered.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        className="ag-theme-alpine",
        style={"height": "600px", "width": "100%"},
        dashGridOptions={"pagination": True, "paginationPageSize": 50}
    )
