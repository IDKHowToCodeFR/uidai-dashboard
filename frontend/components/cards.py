from dash import html
import dash_bootstrap_components as dbc

def make_kpi_card(title, value, status="neutral"):
    color_class = "text-primary"
    if status == "good":
        color_class = "text-success"
    elif status == "bad":
        color_class = "text-danger"
        
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="text-muted text-uppercase mb-2", style={"fontSize": "11px", "letterSpacing": "0.5px"}),
            html.H3(str(value), className=f"mb-0 {color_class}", style={"fontWeight": "600"})
        ]),
        className="custom-card shadow-sm border-0 h-100",
        style={"borderRadius": "12px", "padding": "0.5rem"}
    )

def wrap_chart_card(graph_id, title=None, page_id="dashboard"):
    """
    Creates a standardized chart card container that includes:
    1. A skeleton loader spinner while callbacks are running
    2. An export dropdown header (if a title is provided)
    3. A target Div (graph_id + '-container') where callbacks inject Graph or EmptyState
    """
    from dash import dcc
    from frontend.shared.theme import make_header_with_download
    
    container_id = f"{graph_id}-container"
    header = html.H5(make_header_with_download(title, graph_id, page_id), className="section-title mb-3") if title else None
    
    return html.Div([
        header,
        dbc.Card(
            dbc.CardBody([
                dcc.Loading(
                    custom_spinner=html.Div(className="skeleton-pulse"),
                    children=[html.Div(id=container_id, children=[
                        dcc.Graph(id=graph_id, style={'display': 'none'}, figure={})
                    ])]
                ),
                dcc.Download(id={'type': f'download-data-{page_id}', 'index': graph_id})
            ]),
            className="custom-card shadow-sm border-0 flex-grow-1",
            style={"borderRadius": "16px", "minHeight": "300px"}
        )
    ], className="h-100 d-flex flex-column mb-4")
