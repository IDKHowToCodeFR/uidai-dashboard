from dash import html
import dash_bootstrap_components as dbc

def render_empty_state(message="No Data Available", subtext="Adjust your filters or upload new data.", icon_class="bi bi-clipboard-x", graph_id=None):
    """
    Renders a beautifully styled empty state component.
    Use this instead of returning empty Plotly figures when dataframes are empty.
    If graph_id is provided, injects a hidden dcc.Graph to prevent Dash State callback errors during exports.
    """
    from dash import dcc
    import plotly.graph_objects as go
    
    empty_ui = html.Div(
        [
            html.I(className=f"{icon_class} text-muted", style={"fontSize": "3rem"}),
            html.H4(message, className="mt-3 text-muted", style={"fontWeight": "600"}),
            html.P(subtext, className="text-muted mb-0", style={"fontSize": "0.9rem"}),
        ],
        className="text-center p-5 w-100 h-100 d-flex flex-column justify-content-center align-items-center bg-light rounded",
        style={"minHeight": "300px", "border": "2px dashed #e2e8f0"}
    )
    
    children = [empty_ui]
    
    if graph_id:
        empty_fig = go.Figure().update_layout(xaxis={"visible": False}, yaxis={"visible": False})
        children.append(dcc.Graph(id=graph_id, figure=empty_fig, style={'display': 'none'}))
        
    return html.Div(children, className="w-100 h-100")
