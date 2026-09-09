import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/select', name='Select Dashboard')

layout = dbc.Container([
    html.Div([
        html.H2("Select Dashboard", className="text-center mb-2", style={"fontWeight": "700", "color": "#3b5b8c"}),
        html.Div(id="lookback-badge-container", className="text-center mb-5"),
        dbc.Row(id="select-cards-container", className="justify-content-center mt-4")
    ])
], fluid=True, className="px-4")

@callback(
    Output("select-cards-container", "children"),
    Output("lookback-badge-container", "children"),
    Input("auth-state", "data")
)
def render_cards(auth_state):
    perms = auth_state.get("permissions", []) if auth_state else []
    lookback = auth_state.get("data_lookback_days") if auth_state else None
    role = auth_state.get("role", "") if auth_state else ""
    
    lookback_badge = None
    
    def get_style_and_btn(req_perm, base_color, href, btn_text):
        if req_perm in perms or "Admin" in auth_state.get("role", ""):
            return {"transition": "transform 0.3s ease, box-shadow 0.3s ease"}, dbc.Button(btn_text, href=href, color=base_color, className="w-100 mt-auto fw-bold py-2 rounded-pill text-white")
        return {"opacity": "0.5", "pointerEvents": "none"}, dbc.Button("Locked", disabled=True, color="secondary", className="w-100 mt-auto fw-bold py-2 rounded-pill")

    ccf_style, ccf_btn = get_style_and_btn("can_view_ccf", "primary", "/ccf/dashboard", "Go to CCF")
    unimate_style, unimate_btn = get_style_and_btn("can_view_unimate", "success", "/unimate/dashboard", "Go to UniMate")
    cdr_style, cdr_btn = get_style_and_btn("can_view_cdr", "info", "/cdr/dashboard", "Go to CDR")
    apr_style, apr_btn = get_style_and_btn("can_view_apr", "secondary", "/apr/dashboard", "Go to APR")

    return [
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="bi bi-bar-chart-fill display-4 mb-3", style={"color": "var(--bs-primary)"}),
                    html.H4("CCF Data", className="card-title fw-bold"),
                    html.P("View Customer Contact Feedback analytics.", className="card-text text-muted flex-grow-1"),
                    ccf_btn
                ], className="text-center p-5 d-flex flex-column h-100")
            ], className="shadow h-100 border-0 rounded-4 hover-elevate", style=ccf_style)
        ], xs=12, md=6, lg=5, className="mb-4"),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="bi bi-telephone-fill display-4 mb-3", style={"color": "var(--bs-success)"}),
                    html.H4("UniMate Data", className="card-title fw-bold"),
                    html.P("View UniMate contact center metrics.", className="card-text text-muted flex-grow-1"),
                    unimate_btn
                ], className="text-center p-5 d-flex flex-column h-100")
            ], className="shadow h-100 border-0 rounded-4 hover-elevate", style=unimate_style)
        ], xs=12, md=6, lg=5, className="mb-4"),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="bi bi-journal-text display-4 mb-3", style={"color": "var(--bs-info)"}),
                    html.H4("CDR Data", className="card-title fw-bold"),
                    html.P("View Call Detail Record insights.", className="card-text text-muted flex-grow-1"),
                    cdr_btn
                ], className="text-center p-5 d-flex flex-column h-100")
            ], className="shadow h-100 border-0 rounded-4 hover-elevate", style=cdr_style)
        ], xs=12, md=6, lg=5, className="mb-4"),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="bi bi-graph-up-arrow display-4 mb-3", style={"color": "var(--bs-secondary)"}),
                    html.H4("APR Reports", className="card-title fw-bold"),
                    html.P("Agent Performance Reporting analytics.", className="card-text text-muted flex-grow-1"),
                    apr_btn
                ], className="text-center p-5 d-flex flex-column h-100")
            ], className="shadow h-100 border-0 rounded-4 hover-elevate", style=apr_style)
        ], xs=12, md=6, lg=5, className="mb-4")
    ], lookback_badge
