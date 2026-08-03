import plotly.io as pio
import plotly.graph_objects as go

def get_plotly_template():
    """
    Returns a Plotly graph template matching the PostHog light theme.
    """
    template = pio.templates["plotly_white"]
    
    # Customize the template
    template.layout.paper_bgcolor = 'rgba(0,0,0,0)'  # Transparent
    template.layout.plot_bgcolor = 'rgba(0,0,0,0)'   # Transparent
    template.layout.font.color = '#334155'     # Body text color
    template.layout.font.family = 'Inter, sans-serif'
    
    # Grid lines
    template.layout.xaxis.gridcolor = '#f1f5f9' 
    template.layout.yaxis.gridcolor = '#f1f5f9'
    template.layout.xaxis.zerolinecolor = '#e2e8f0' 
    template.layout.yaxis.zerolinecolor = '#e2e8f0'
    
    # Premium Palette
    template.layout.colorway = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
    
    return template

def make_header_with_download(title, graph_id):
    from dash import html
    return html.Span(title)

def wrap_graph_with_download(graph_id, graph_component):
    from dash import html
    return html.Div([
        html.Button(
            html.I(className="bi bi-download"),
            id=f"btn-download-{graph_id}",
            className="btn btn-sm btn-link p-0 download-chart-btn",
            style={"position": "absolute", "top": "10px", "right": "10px", "zIndex": 10, "color": "var(--color-primary)", "border": "none", "background": "transparent", "cursor": "pointer"},
            title="Download as JPG"
        ),
        graph_component
    ], style={"position": "relative"})

def make_export_dropdown(page_id):
    import dash_bootstrap_components as dbc
    return dbc.DropdownMenu(
        label="Export Dashboard",
        children=[
            dbc.DropdownMenuItem("CSV", id=f"btn-export-csv-{page_id}"),
            dbc.DropdownMenuItem("PDF", id=f"btn-export-pdf-{page_id}"),
            dbc.DropdownMenuItem("JPG", id=f"btn-export-jpg-{page_id}"),
        ],
        color="primary",
        size="sm",
        className="float-end dashboard-export-dropdown"
    )
