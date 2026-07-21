import dash
from dash import Dash, html, dcc, Input, Output, State, callback
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
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    if not files:
        return pd.DataFrame().to_dict('records')
    df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, files[0]))
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
        object_cols = df.select_dtypes(include=['object']).columns
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
                ">>",
                id="open-offcanvas",
                n_clicks=0,
                className="btn btn-link text-dark p-0 me-4 text-decoration-none",
                style={"border": "none", "background": "none", "fontWeight": "bold", "fontSize": "24px"}
            ),
            html.H2("UIDAI", className="display-lg mb-0 me-4", style={"display": "inline-block"}),
        ], style={"display": "flex", "alignItems": "center"}),
        
        # Modality Filter (Right Aligned)
        html.Div([
            html.Span("Modality: ", className="me-2 body-strong"),
            dbc.Checklist(
                options=[
                    {"label": "Biometric", "value": "Biometric"},
                    {"label": "Demographic", "value": "Demographic"}
                ],
                value=[],
                id="modality-filter",
                inline=True,
                className="d-inline-flex gap-3"
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
        "borderRadius": "0", 
        "borderLeft": "none", 
        "borderRight": "none", 
        "borderTop": "none", 
        "zIndex": 1000,
        "backgroundColor": "#eeefe9",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between"
    }
)

# --- OFFCANVAS SIDEBAR ---
sidebar_content = html.Div([
    html.H4("Navigation", className="mb-3"),
    dbc.Nav(
        [
            dbc.NavLink(
                [html.I(className="bi bi-graph-up me-2"), page['name']], 
                href=page['relative_path'], 
                active="exact", 
                className="body-strong mb-2"
            )
            for page in dash.page_registry.values()
        ],
        vertical=True,
        pills=True,
        className="custom-sidebar-nav mb-5"
    ),
    
    html.Hr(style={"borderColor": "#bfc1b7"}),
    
    html.H5("Data Upload", className="mb-3 mt-4"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '6px',
            'textAlign': 'center',
            'backgroundColor': '#ffffff',
            'cursor': 'pointer'
        },
        multiple=False
    )
])

offcanvas = dbc.Offcanvas(
    sidebar_content,
    id="offcanvas-sidebar",
    title="UIDAI Menu",
    is_open=False,
    style={"backgroundColor": "#eeefe9", "borderRight": "1px solid #bfc1b7"}
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
    Output("open-offcanvas", "children"),
    Input("open-offcanvas", "n_clicks"),
    [State("offcanvas-sidebar", "is_open")],
)
def toggle_offcanvas(n1, is_open):
    if n1:
        new_is_open = not is_open
        return new_is_open, "<<" if new_is_open else ">>"
    return is_open, "<<" if is_open else ">>"

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

if __name__ == '__main__':
    app.run(debug=True, port=8050)