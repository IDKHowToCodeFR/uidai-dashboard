import os
import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io

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
    target_file = "ivrs_call_logs_sample_processed.xlsx"
    if os.path.exists(os.path.join(PROCESSED_DATA_DIR, target_file)):
        df = pd.read_excel(os.path.join(PROCESSED_DATA_DIR, target_file), engine='openpyxl')
        return df.to_dict('records')

    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.xlsx')]
    if not files:
        return pd.DataFrame().to_dict('records')
    df = pd.read_excel(os.path.join(PROCESSED_DATA_DIR, files[0]), engine='openpyxl')
    return df.to_dict('records')

def get_history_options():
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.xlsx')]
    return [{'label': f, 'value': f} for f in files]

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded), engine='openpyxl')
        else:
            return None
        
        import numpy as np
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        object_cols = df.select_dtypes(include=['object', 'string']).columns
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        # Save to processed directory for history
        if not os.path.exists(PROCESSED_DATA_DIR):
            os.makedirs(PROCESSED_DATA_DIR)
        save_path = os.path.join(PROCESSED_DATA_DIR, filename)
        df.to_excel(save_path, index=False, engine='openpyxl')
        
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

# --- TOPBAR (Combined with Filters) ---
topbar = html.Div(
    [
        html.Div([
            # Hamburger Button
            html.Button(
                html.I(className="bi bi-list", style={"fontSize": "28px"}),
                id="btn-sidebar",
                n_clicks=0,
                className="btn btn-link text-dark p-0 me-4 text-decoration-none",
                style={"border": "none", "background": "none"}
            ),
            html.H2("UIDAI", className="display-lg mb-0 me-4", style={"display": "inline-block"}),
        ], style={"display": "flex", "alignItems": "center"}),
        
        # Filters (Right Aligned in Header)
        html.Div([
            # Date Picker
            dcc.DatePickerRange(
                id='date-picker-range',
                start_date_placeholder_text="Start",
                end_date_placeholder_text="End",
                display_format='YYYY-MM-DD',
                className="me-4"
            ),
            
            # Company Filter
            html.Span("Company: ", className="me-2 body-strong"),
            dbc.DropdownMenu(
                label="All Companies",
                id="company-dropdown-btn",
                toggleClassName="btn",
                toggle_style=style_dropdown_toggle,
                children=[
                    html.Div([
                        dbc.Checkbox(id="select-all-companies", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "var(--color-text-heading)"}),
                        html.Hr(className="my-2", style={"borderColor": "var(--color-border)"}),
                        dbc.Checklist(id="modality-filter", options=[], value=[], className="px-3 pb-2", style={"color": "var(--color-text-body)"})
                    ], style={"maxHeight": "300px", "overflowY": "auto", "overflowX": "hidden", "minWidth": "250px", "backgroundColor": "var(--color-surface)", "borderRadius": "12px", "boxShadow": "0 10px 15px -3px rgba(0,0,0,0.1)", "border": "1px solid var(--color-border)", "padding": "8px 0"})
                ]
            ),

            # Queue Filter
            html.Span("Queue: ", className="ms-4 me-2 body-strong"),
            dbc.DropdownMenu(
                label="All Queues",
                id="queue-dropdown-btn",
                toggleClassName="btn",
                toggle_style=style_dropdown_toggle,
                children=[
                    html.Div([
                        dbc.Checkbox(id="select-all-queues", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "var(--color-text-heading)"}),
                        html.Hr(className="my-2", style={"borderColor": "var(--color-border)"}),
                        dbc.Checklist(id="queue-filter", options=[], value=[], className="px-3 pb-2", style={"color": "var(--color-text-body)"})
                    ], style={"maxHeight": "300px", "overflowY": "auto", "overflowX": "hidden", "minWidth": "250px", "backgroundColor": "var(--color-surface)", "borderRadius": "12px", "boxShadow": "0 10px 15px -3px rgba(0,0,0,0.1)", "border": "1px solid var(--color-border)", "padding": "8px 0"})
                ]
            ),

            # Language Filter
            html.Span("Language: ", className="ms-4 me-2 body-strong"),
            dbc.DropdownMenu(
                label="All Languages",
                id="language-dropdown-btn",
                toggleClassName="btn",
                toggle_style=style_dropdown_toggle,
                children=[
                    html.Div([
                        dbc.Checkbox(id="select-all-languages", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "var(--color-text-heading)"}),
                        html.Hr(className="my-2", style={"borderColor": "var(--color-border)"}),
                        dbc.Checklist(id="language-filter", options=[], value=[], className="px-3 pb-2", style={"color": "var(--color-text-body)"})
                    ], style={"maxHeight": "300px", "overflowY": "auto", "overflowX": "hidden", "minWidth": "250px", "backgroundColor": "var(--color-surface)", "borderRadius": "12px", "boxShadow": "0 10px 15px -3px rgba(0,0,0,0.1)", "border": "1px solid var(--color-border)", "padding": "8px 0"})
                ]
            ),
            
            # Export Data Button
            html.Button(
                [html.I(className="bi bi-download me-2"), "Export"],
                id="btn-export",
                className="btn btn-primary ms-4 body-strong"
            ),
            
            # Avatar Icon
            html.I(className="bi bi-person-circle fs-3 text-secondary ms-4")
            
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
    html.H6("MAIN", className="text-muted text-uppercase mb-3", style={"fontSize": "11px", "letterSpacing": "1px"}),
    dbc.Nav(
        [
            dbc.NavLink(
                [html.I(className="bi bi-grid-1x2-fill me-3"), "Dashboard"],
                href="/",
                active="exact",
                className="body-strong mb-2 d-flex align-items-center"
            ),
            dbc.NavLink(
                [html.I(className="bi bi-table me-3"), "Raw Data Explorer"],
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
    
    html.H6("DATA", className="text-muted text-uppercase mb-3 mt-4", style={"fontSize": "11px", "letterSpacing": "1px"}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            html.I(className="bi bi-cloud-arrow-up fs-4 mb-2 d-block"),
            'Drag and Drop or ', html.A('Select Files', className="text-primary text-decoration-none")
        ]),
        style={
            'width': '100%',
            'padding': '1.5rem',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderColor': '#cbd5e1',
            'borderRadius': '12px',
            'textAlign': 'center',
            'backgroundColor': '#f8fafc',
            'cursor': 'pointer',
            'color': '#64748b',
            'transition': 'all 0.2s ease'
        },
        multiple=False,
        className="upload-box mb-4"
    ),
    html.Div(id='upload-status', className="text-muted small mt-2"),

    html.H6("HISTORY", className="text-muted text-uppercase mb-3", style={"fontSize": "11px", "letterSpacing": "1px"}),
    dbc.RadioItems(
        id="file-history",
        options=get_history_options(),
        value=get_history_options()[0]['value'] if get_history_options() else None,
        className="mb-4"
    )
])

sidebar = dbc.Offcanvas(
    sidebar_content,
    id="sidebar",
    title="",
    is_open=False,
    className="offcanvas border-0 shadow-lg"
)

content = html.Div(
    dash.page_container,
    style={"marginTop": "80px", "padding": "2rem"}
)

app.layout = html.Div([
    dcc.Store(id='data-store', data=get_initial_data()),
    dcc.Download(id="download-dataframe-csv"),
    topbar,
    sidebar,
    content
])

@callback(
    Output("sidebar", "is_open"),
    Input("btn-sidebar", "n_clicks"),
    State("sidebar", "is_open"),
)
def toggle_sidebar(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output('modality-filter', 'options'),
    Output('modality-filter', 'value'),
    Output('queue-filter', 'options'),
    Output('queue-filter', 'value'),
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
    q_options, q_values = [], []
    l_options, l_values = [], []
    
    if 'Company' in df.columns:
        companies = df['Company'].dropna().unique().tolist()
        c_options = [{'label': c, 'value': c} for c in companies]
        c_values = companies
        
    if 'Queue Name' in df.columns:
        queues = df['Queue Name'].dropna().unique().tolist()
        q_options = [{'label': q, 'value': q} for q in queues]
        q_values = queues
        
    if 'Language' in df.columns:
        langs = df['Language'].dropna().unique().tolist()
        l_options = [{'label': l, 'value': l} for l in langs]
        l_values = langs
        
    min_date = max_date = start_date = end_date = None
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        min_date = df['Timestamp'].min().date()
        max_date = df['Timestamp'].max().date()
        start_date = min_date
        end_date = max_date
        
    return c_options, c_values, q_options, q_values, l_options, l_values, min_date, max_date, start_date, end_date

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
            df = pd.read_excel(file_path, engine='openpyxl')
            return df.to_dict('records')
    return dash.no_update

@callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-export", "n_clicks"),
    State('data-store', 'data'),
    State('modality-filter', 'value'),
    State('queue-filter', 'value'),
    State('language-filter', 'value'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True
)
def export_data(n_clicks, data, companies, queues, languages, start_date, end_date):
    if not data:
        return dash.no_update
        
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
                    
    return dcc.send_data_frame(df.to_csv, "export.csv", index=False)

def sync_checklist_all(select_all, selected_items, options, trigger_id, select_all_id, filter_id):
    all_items = [opt['value'] for opt in options] if options else []
    
    if trigger_id == select_all_id:
        if select_all:
            return all_items, True
        else:
            return [], False
    elif trigger_id == filter_id:
        selected = selected_items or []
        if len(selected) == len(all_items) and len(all_items) > 0:
            return dash.no_update, True
        else:
            return dash.no_update, False
    return dash.no_update, dash.no_update

def update_btn_label(selected_items, options, entity_name):
    if not options:
        return f"Select {entity_name}..."
    all_items = [opt['value'] for opt in options]
    selected = selected_items or []
    if len(selected) == len(all_items) or len(selected) == 0:
        return f"All {entity_name}"
    elif len(selected) == 1:
        return selected[0]
    else:
        return f"{len(selected)} {entity_name} Selected"

@callback(
    Output('modality-filter', 'value', allow_duplicate=True),
    Output('select-all-companies', 'value'),
    Input('select-all-companies', 'value'),
    Input('modality-filter', 'value'),
    State('modality-filter', 'options'),
    prevent_initial_call=True
)
def sync_companies(select_all, selected, options):
    return sync_checklist_all(select_all, selected, options, ctx.triggered_id, 'select-all-companies', 'modality-filter')

@callback(
    Output('company-dropdown-btn', 'label'),
    Input('modality-filter', 'value'),
    State('modality-filter', 'options')
)
def label_companies(selected, options):
    return update_btn_label(selected, options, "Companies")

@callback(
    Output('queue-filter', 'value', allow_duplicate=True),
    Output('select-all-queues', 'value'),
    Input('select-all-queues', 'value'),
    Input('queue-filter', 'value'),
    State('queue-filter', 'options'),
    prevent_initial_call=True
)
def sync_queues(select_all, selected, options):
    return sync_checklist_all(select_all, selected, options, ctx.triggered_id, 'select-all-queues', 'queue-filter')

@callback(
    Output('queue-dropdown-btn', 'label'),
    Input('queue-filter', 'value'),
    State('queue-filter', 'options')
)
def label_queues(selected, options):
    return update_btn_label(selected, options, "Queues")

@callback(
    Output('language-filter', 'value', allow_duplicate=True),
    Output('select-all-languages', 'value'),
    Input('select-all-languages', 'value'),
    Input('language-filter', 'value'),
    State('language-filter', 'options'),
    prevent_initial_call=True
)
def sync_languages(select_all, selected, options):
    return sync_checklist_all(select_all, selected, options, ctx.triggered_id, 'select-all-languages', 'language-filter')

@callback(
    Output('language-dropdown-btn', 'label'),
    Input('language-filter', 'value'),
    State('language-filter', 'options')
)
def label_languages(selected, options):
    return update_btn_label(selected, options, "Languages")

if __name__ == '__main__':
    app.run(debug=True, port=8050)