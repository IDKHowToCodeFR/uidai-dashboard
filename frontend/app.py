import os
import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
from datetime import datetime, timedelta

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'),
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
    suppress_callback_exceptions=True
)
app.title = "UIDAI Dashboard"

# Directory for processed data
PROCESSED_DATA_DIR = "data/processed"

def get_initial_data():
    target_file = "july_trend_data_processed.csv"
    if os.path.exists(os.path.join(PROCESSED_DATA_DIR, target_file)):
        df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, target_file))
        return df.to_dict('records')

    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    if not files:
        return pd.DataFrame().to_dict('records')
    df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, files[0]))
    return df.to_dict('records')

def get_history_options():
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    
    file_times = []
    for f in files:
        file_path = os.path.join(PROCESSED_DATA_DIR, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        file_times.append({'name': f, 'time': mtime})
        
    file_times.sort(key=lambda x: x['time'], reverse=True)
    
    now = datetime.now()
    today = now.date()
    
    options = []
    current_group = None
    
    for item in file_times:
        mtime = item['time']
        date = mtime.date()
        age_days = (today - date).days
        
        if age_days == 0:
            group_name = "Today"
        elif age_days == 1:
            group_name = "Yesterday"
        elif age_days <= 30:
            group_name = mtime.strftime("%b %d")
        elif age_days <= 90:
            group_name = mtime.strftime("%B")
        else:
            group_name = "Earlier"
            
        if group_name != current_group:
            options.append({
                'label': html.Div(group_name, className="history-group-header small text-muted fw-bold mt-3 mb-1 text-uppercase", style={'fontSize': '10px', 'letterSpacing': '1px'}), 
                'value': f'HEADER_{group_name}', 
                'disabled': True
            })
            current_group = group_name
            
        label = html.Span(item['name'], className="text-truncate ms-2")
        options.append({'label': label, 'value': item['name']})
        
    return options

def parse_contents(contents, filename):
    out_filename = os.path.splitext(filename)[0] + "_processed.csv"
    save_path = os.path.join(PROCESSED_DATA_DIR, out_filename)
    
    if os.path.exists(save_path):
        try:
            df = pd.read_csv(save_path)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error reading existing file: {e}")
            
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            excel_file = pd.ExcelFile(io.BytesIO(decoded), engine='openpyxl')
            dfs = []
            for sheet_name in excel_file.sheet_names:
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if 'Company' not in sheet_df.columns:
                    sheet_df['Company'] = sheet_name
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
        else:
            return None
        
        import numpy as np
        numeric_cols = df.select_dtypes(include='number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        object_cols = df.select_dtypes(include=['object', 'string']).columns # type: ignore
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        # Save to processed directory for history
        if not os.path.exists(PROCESSED_DATA_DIR):
            os.makedirs(PROCESSED_DATA_DIR)
        df.to_csv(save_path, index=False)
        
        return df.to_dict('records')
    except Exception as e:
        print(e)
        return None

style_dropdown_toggle = {
    "backgroundColor": "var(--color-surface)",
    "color": "var(--color-text-heading)",
    "border": "1px solid var(--color-border)",
    "borderRadius": "8px",
    "padding": "8px 16px",
    "fontFamily": "'Inter', sans-serif",
    "fontSize": "14px",
    "fontWeight": "600",
    "boxShadow": "0 2px 4px -1px rgba(0,0,0,0.05)",
    "transition": "all 0.2s ease"
}

# --- FILTER DRAWER (Right Side) ---
filter_drawer = dbc.Offcanvas(
    html.Div([
        html.H6("TIME RANGE", className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date_placeholder_text="Start",
            end_date_placeholder_text="End",
            display_format='YYYY-MM-DD',
            className="mb-4 w-100"
        ),
        
        html.H6("COMPANY", className="text-muted text-uppercase mb-2 mt-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.Dropdown(
            id="company-filter",
            options=[],
            value=[],
            multi=True,
            placeholder="Search Companies...",
            className="mb-4"
        ),

        html.H6("LANGUAGE", className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "1px"}),
        dcc.Dropdown(
            id="language-filter",
            options=[],
            value=[],
            multi=True,
            placeholder="Search Languages...",
            className="mb-4"
        ),
    ]),
    id="filter-drawer",
    title="Dashboard Filters",
    is_open=False,
    placement="end",
    className="offcanvas border-0 shadow-lg"
)

# --- TOPBAR ---
topbar = html.Div(
    [
        html.Div([
            # Hamburger Menu Button
            html.Button(
                html.I(className="bi bi-list fs-4"),
                id="btn-sidebar-toggle",
                n_clicks=0,
                className="btn btn-light me-3 body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
            ),
            html.H2("UIDAI", className="display-lg mb-0 me-4", style={"display": "inline-block"}),
        ], style={"display": "flex", "alignItems": "center"}),
        
        # Right aligned action buttons
        html.Div([
            # Filters Drawer Button
            html.Button(
                html.I(className="bi bi-funnel-fill"),
                id="btn-filters",
                n_clicks=0,
                className="btn btn-light me-3 body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center", "border": "1px solid var(--color-border)"}
            ),
            # Export Data Button
            html.Button(
                html.I(className="bi bi-download"),
                id="btn-export",
                className="btn btn-primary body-strong rounded-circle shadow-sm",
                style={"width": "42px", "height": "42px", "display": "flex", "alignItems": "center", "justifyContent": "center"}
            )
        ], style={"display": "flex", "alignItems": "center"})
    ],
    className="topbar custom-card px-4",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "right": 0,
        "height": "80px",
        "zIndex": 1000,
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between"
    }
)

# --- SIDEBAR ---
sidebar_content = html.Div([
    html.H6("MAIN", className="sidebar-section-title text-muted text-uppercase mb-3", style={"fontSize": "11px", "letterSpacing": "1px"}),
    dbc.Nav(
        [
            dbc.NavLink(
                [html.I(className="bi bi-grid-1x2-fill me-3"), html.Span("Dashboard", className="nav-link-text")],
                href="/",
                active="exact",
                className="body-strong mb-2 d-flex align-items-center"
            ),
            dbc.NavLink(
                [html.I(className="bi bi-table me-3"), html.Span("Raw Data Explorer", className="nav-link-text")],
                href="/raw-data",
                active="exact",
                className="body-strong mb-2 d-flex align-items-center"
            ),
        ],
        vertical=True,
        pills=True,
        className="custom-sidebar-nav mb-5"
    ),
    
    html.Hr(style={"borderColor": "#e2e8f0"}),
    
    html.H6("DATA", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.I(className="bi bi-cloud-arrow-up fs-4 mb-2 d-block"),
                html.Span(['Drag and Drop or ', html.A('Select Files', className="text-primary text-decoration-none")], className="nav-link-text")
            ]),
            multiple=False,
            className="upload-box mb-4"
        )
    ]),
    html.Div(id='upload-status', className="nav-link-text text-muted small mt-2"),

    html.H6("HISTORY", className="sidebar-section-title text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
    html.Div(
        dbc.RadioItems(
            id="file-history",
            options=get_history_options(),
            value=get_history_options()[0]['value'] if get_history_options() else None,
            className="mb-4 history-radio-group"
        )
    )
], className="sidebar-content-wrapper")

sidebar = dbc.Offcanvas(
    sidebar_content,
    id="sidebar",
    title="Main Menu",
    placement="start",
    is_open=False,
    className="premium-offcanvas sidebar-container"
)

content = html.Div(
    dash.page_container,
    id="main-content",
    className="main-content"
)

app.layout = html.Div([
    dcc.Store(id='data-store', data=get_initial_data()),
    dcc.Download(id="download-dataframe-csv"),
    topbar,
    sidebar,
    filter_drawer,
    content
])

@callback(
    Output("filter-drawer", "is_open"),
    Input("btn-filters", "n_clicks"),
    State("filter-drawer", "is_open"),
)
def toggle_filter_drawer(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output("sidebar", "is_open"),
    Input("btn-sidebar-toggle", "n_clicks"),
    State("sidebar", "is_open"),
)
def toggle_left_sidebar(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output('company-filter', 'options'),
    Output('company-filter', 'value'),
    Output('language-filter', 'options'),
    Output('language-filter', 'value'),
    Output('date-picker-range', 'min_date_allowed'),
    Output('date-picker-range', 'max_date_allowed'),
    Output('date-picker-range', 'start_date'),
    Output('date-picker-range', 'end_date'),
    Input('data-store', 'data')
)
def sync_filters(data):
    if not data:
        return dash.no_update
    
    df = pd.DataFrame(data)
    
    c_options, c_values = [], []
    l_options, l_values = [], []
    
    if 'Company' in df.columns:
        companies = df['Company'].dropna().unique().tolist()
        c_options = [{'label': c, 'value': c} for c in companies]
        c_values = companies
        
        
    if 'Language' in df.columns:
        langs = df['Language'].dropna().unique().tolist()
        l_options = [{'label': l, 'value': l} for l in langs]
        l_values = langs
        
    min_date = max_date = start_date = end_date = None
    date_col = None
    if 'Timestamp' in df.columns:
        date_col = 'Timestamp'
    elif 'Date' in df.columns:
        date_col = 'Date'
    elif 'Call Start Time' in df.columns:
        date_col = 'Call Start Time'

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()
        start_date = min_date
        end_date = max_date
        
    return c_options, c_values, l_options, l_values, min_date, max_date, start_date, end_date

@callback(
    Output('data-store', 'data', allow_duplicate=True),
    Output('upload-status', 'children'),
    Output('file-history', 'options'),
    Output('file-history', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def update_output(contents, filename):
    if contents is not None:
        data = parse_contents(contents, filename)
        if data is not None:
            opts = get_history_options()
            return data, f"Loaded {filename} successfully.", opts, filename
        return dash.no_update, "Error parsing file.", dash.no_update, dash.no_update
    return dash.no_update, "", dash.no_update, dash.no_update

@callback(
    Output('data-store', 'data', allow_duplicate=True),
    Input('file-history', 'value'),
    prevent_initial_call=True
)
def load_from_history(filename):
    if filename:
        file_path = os.path.join(PROCESSED_DATA_DIR, filename)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            return df.to_dict('records')
    return dash.no_update

@callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-export", "n_clicks"),
    State('data-store', 'data'),
    State('company-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True
)
def export_data(n_clicks, data, companies, languages, start_date, end_date):
    if not data:
        return dash.no_update
        
    df = pd.DataFrame(data)
    
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
                    
    return dcc.send_data_frame(df.to_csv, "export.csv", index=False)

# (Redundant sync callbacks removed)

if __name__ == '__main__':
    app.run(debug=True, port=8050)