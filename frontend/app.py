import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import os

# Initialize the Dash application
app = Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&display=swap"
    ],
    suppress_callback_exceptions=True
)

app.title = "UIDAI Dashboard"

PROCESSED_DATA_DIR = "data/processed"

def get_initial_data():
    target_file = "ivrs_call_logs_sample_processed.csv"
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
            
        import numpy as np
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        object_cols = df.select_dtypes(include=['object', 'string']).columns
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        return df.to_dict('records')
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None

# --- TOPBAR ---
topbar = html.Div(
    [
        html.Div([
            # Hamburger Button
            html.Button(
                html.I(className="bi bi-list", style={"fontSize": "28px"}),
                id="open-offcanvas",
                n_clicks=0,
                className="btn btn-link p-0 me-4 text-decoration-none",
                style={"border": "none", "background": "none", "color": "var(--color-ink)"}
            ), 
            html.H2("UIDAI", className="display-lg mb-0 me-4", style={"display": "inline-block"}),
        ], style={"display": "flex", "alignItems": "center"}),
        
        # Filters and Controls (Right Aligned)
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
            html.Div(
                dbc.DropdownMenu(
                    label="Select Companies...",
                    id="company-dropdown-btn",
                    toggleClassName="btn-outline-secondary bg-white text-dark",
                    children=[
                        html.Div([
                            dbc.Checkbox(id="select-all-companies", label="Select All", value=True, className="fw-bold px-3 pt-2"),
                            html.Hr(className="my-2"),
                            dbc.Checklist(
                                id="modality-filter",
                                options=[],
                                value=[],
                                className="px-3 pb-2"
                            )
                        ], style={"maxHeight": "300px", "overflowY": "auto", "minWidth": "250px"})
                    ]
                ),
                className="me-4"
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

# --- OFFCANVAS SIDEBAR ---
sidebar_content = html.Div([
    html.H6("MAIN", className="utility-xs mb-3"),
    dbc.Nav(
        [
            dbc.NavLink(
                [html.I(className="bi bi-grid-1x2-fill me-3"), page['name']], 
                href=page['relative_path'], 
                active="exact", 
                className="body-strong mb-2 d-flex align-items-center"
            )
            for page in dash.page_registry.values()
        ],
        vertical=True,
        pills=True,
        className="custom-sidebar-nav mb-5"
    ),
    
    html.Hr(style={"borderColor": "#e2e8f0"}),
    
    html.H6("DATA", className="utility-xs mb-3 mt-4"),
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
        className="upload-box"
    )
])

offcanvas = dbc.Offcanvas(
    sidebar_content,
    id="offcanvas-sidebar",
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
    topbar, 
    offcanvas, 
    content
])

# --- APP LEVEL CALLBACKS ---

@callback(
    Output("offcanvas-sidebar", "is_open"),
    Input("open-offcanvas", "n_clicks"),
    State("offcanvas-sidebar", "is_open"),
    prevent_initial_call=True,
)
def toggle_offcanvas(n1, is_open):
    return not is_open

@callback(
    Output("open-offcanvas", "children"),
    Input("offcanvas-sidebar", "is_open"),
)
def toggle_icon(is_open):
    icon = "bi bi-x-lg" if is_open else "bi bi-list"
    return html.I(className=icon, style={"fontSize": "28px"})

@callback(
    Output('modality-filter', 'options'),
    Output('modality-filter', 'value'),
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
    
    options = []
    values = []
    if 'Company' in df.columns:
        companies = df['Company'].dropna().unique().tolist()
        options = [{'label': c, 'value': c} for c in companies]
        values = companies
        
    min_date = max_date = start_date = end_date = None
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        min_date = df['Timestamp'].min().date()
        max_date = df['Timestamp'].max().date()
        start_date = min_date
        end_date = max_date
    elif 'Call Start Time' in df.columns:
        df['Call Start Time'] = pd.to_datetime(df['Call Start Time'])
        min_date = df['Call Start Time'].min().date()
        max_date = df['Call Start Time'].max().date()
        start_date = min_date
        end_date = max_date
        
    return options, values, min_date, max_date, start_date, end_date

@callback(
    Output('data-store', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def update_store(contents, filename):
    if contents is not None:
        new_data = parse_contents(contents, filename)
        if new_data is not None:
            return new_data
    return dash.no_update

@callback(
    Output('modality-filter', 'value', allow_duplicate=True),
    Output('select-all-companies', 'value'),
    Input('select-all-companies', 'value'),
    Input('modality-filter', 'value'),
    State('modality-filter', 'options'),
    prevent_initial_call=True
)
def sync_select_all(select_all, selected_companies, options):
    trigger = ctx.triggered_id
    all_companies = [opt['value'] for opt in options] if options else []
    
    if trigger == 'select-all-companies':
        if select_all:
            return all_companies, True
        else:
            return [], False
    elif trigger == 'modality-filter':
        selected = selected_companies or []
        if len(selected) == len(all_companies) and len(all_companies) > 0:
            return dash.no_update, True
        else:
            return dash.no_update, False
    return dash.no_update, dash.no_update

@callback(
    Output('company-dropdown-btn', 'label'),
    Input('modality-filter', 'value'),
    State('modality-filter', 'options')
)
def update_dropdown_label(selected_companies, options):
    if not options:
        return "Select Companies..."
    
    all_companies = [opt['value'] for opt in options]
    selected = selected_companies or []
    
    if len(selected) == len(all_companies) or len(selected) == 0:
        return "All Companies"
    elif len(selected) == 1:
        return selected[0]
    else:
        return f"{len(selected)} Companies Selected"

if __name__ == '__main__':
    app.run(debug=True, port=8050)