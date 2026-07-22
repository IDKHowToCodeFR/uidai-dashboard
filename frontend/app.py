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
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
    ],
    suppress_callback_exceptions=True
)
app.title = "IVRS Dashboard"

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
        return df.to_dict('records')
    except Exception as e:
        print(e)
        return None

style_dropdown_toggle = {
    "backgroundColor": "#ffffff",
    "color": "#23251d",
    "border": "1px solid #bfc1b7",
    "borderRadius": "6px",
    "padding": "6px 12px",
    "fontFamily": "'IBM Plex Sans', sans-serif",
    "fontSize": "14px",
    "boxShadow": "none"
}

# --- TOPBAR (Combined with Filters) ---
topbar = html.Div(
    [
        html.Div([
            html.Button(
                html.I(className="bi bi-list", style={"fontSize": "1.5rem", "color": "#23251d"}),
                id="btn-sidebar",
                className="btn me-3 border-0 bg-transparent",
                style={"padding": "0"}
            )
        ], style={"display": "flex", "alignItems": "center"}),
        
        # Filters (Right Aligned in Header)
        html.Div([
            html.Div([
                html.Span("Date:", className="me-2 body-strong", style={"color": "#4d4f46", "fontWeight": "600"}),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    start_date_placeholder_text="Start",
                    end_date_placeholder_text="End",
                    display_format='YYYY-MM-DD',
                    className="me-4"
                )
            ], className="d-flex align-items-center mb-0"),
            
            html.Div([
                html.Span("Company:", className="me-2 body-strong", style={"color": "#4d4f46", "fontWeight": "600"}),
                dbc.DropdownMenu(
                    label="All Companies",
                    id="company-dropdown-btn",
                    toggleClassName="btn",
                    toggle_style=style_dropdown_toggle,
                    children=[
                        html.Div([
                            dbc.Checkbox(id="select-all-companies", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "#23251d"}),
                            html.Hr(className="my-2", style={"borderColor": "#dcdfd2"}),
                            dbc.Checklist(id="modality-filter", options=[], value=[], className="px-3 pb-2", style={"color": "#4d4f46"})
                        ], style={"maxHeight": "300px", "overflowY": "auto", "minWidth": "250px", "backgroundColor": "#ffffff"})
                    ]
                )
            ], className="d-flex align-items-center me-4 mb-0"),

            html.Div([
                html.Span("Queue:", className="me-2 body-strong", style={"color": "#4d4f46", "fontWeight": "600"}),
                dbc.DropdownMenu(
                    label="All Queues",
                    id="queue-dropdown-btn",
                    toggleClassName="btn",
                    toggle_style=style_dropdown_toggle,
                    children=[
                        html.Div([
                            dbc.Checkbox(id="select-all-queues", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "#23251d"}),
                            html.Hr(className="my-2", style={"borderColor": "#dcdfd2"}),
                            dbc.Checklist(id="queue-filter", options=[], value=[], className="px-3 pb-2", style={"color": "#4d4f46"})
                        ], style={"maxHeight": "300px", "overflowY": "auto", "minWidth": "250px", "backgroundColor": "#ffffff"})
                    ]
                )
            ], className="d-flex align-items-center me-4 mb-0"),

            html.Div([
                html.Span("Language:", className="me-2 body-strong", style={"color": "#4d4f46", "fontWeight": "600"}),
                dbc.DropdownMenu(
                    label="All Languages",
                    id="language-dropdown-btn",
                    toggleClassName="btn",
                    toggle_style=style_dropdown_toggle,
                    children=[
                        html.Div([
                            dbc.Checkbox(id="select-all-languages", label="Select All", value=True, className="px-3 pt-2", style={"fontWeight": "600", "color": "#23251d"}),
                            html.Hr(className="my-2", style={"borderColor": "#dcdfd2"}),
                            dbc.Checklist(id="language-filter", options=[], value=[], className="px-3 pb-2", style={"color": "#4d4f46"})
                        ], style={"maxHeight": "300px", "overflowY": "auto", "minWidth": "250px", "backgroundColor": "#ffffff"})
                    ]
                )
            ], className="d-flex align-items-center mb-0")
        ], style={"display": "flex", "alignItems": "center"})
    ],
    className="topbar custom-card px-4",
    style={
        "height": "72px",
        "position": "fixed",
        "top": 0,
        "left": 0,
        "right": 0,
        "zIndex": 1030,
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "backgroundColor": "#ffffff",
        "borderBottom": "1px solid #bfc1b7"
    }
)

# --- SIDEBAR ---
sidebar = dbc.Offcanvas(
    html.Div([
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderColor': '#f7a501',
                    'borderRadius': '6px',
                    'textAlign': 'center',
                    'margin': '10px 0',
                    'backgroundColor': '#e5e7e0',
                    'cursor': 'pointer'
                },
                multiple=False
            ),
            html.Div(id='upload-status', className="text-muted small mt-2")
        ], className="mb-4"),
        
        html.H6("CONTENTS", className="text-muted fw-bold mb-3 mt-4"),
        dbc.Nav(
            [
                dbc.NavLink("Dashboard", href="/", active="exact", className="py-2"),
                dbc.NavLink("Raw Data Explorer", href="/raw-data", active="exact", className="py-2"),
            ],
            vertical=True,
            pills=True,
            className="mb-4"
        ),
    ]),
    id="sidebar",
    title="IVRS Dashboard Navigation",
    is_open=False,
    className="offcanvas border-0 shadow-lg"
)

content = html.Div([
    dash.page_container
], style={"marginTop": "96px", "padding": "2rem"})

app.layout = html.Div([
    dcc.Store(id='data-store', data=get_initial_data()),
    topbar,
    sidebar,
    content
], style={"minHeight": "100vh", "backgroundColor": "#eeefe9"})

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
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def update_output(contents, filename):
    if contents is not None:
        data = parse_contents(contents, filename)
        if data is not None:
            return data, f"Loaded {filename} successfully."
        return dash.no_update, "Error parsing file."
    return dash.no_update, ""

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