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
    
    # Grid lines - Subtle & Structured
    template.layout.xaxis.showgrid = False       # Remove vertical grid lines for cleaner look
    template.layout.yaxis.showgrid = True
    template.layout.yaxis.gridcolor = 'rgba(226, 232, 240, 0.6)'  # Very faint #e2e8f0
    template.layout.yaxis.gridwidth = 1
    template.layout.yaxis.griddash = 'dash'      # Dashed grid lines
    
    template.layout.xaxis.zeroline = True
    template.layout.xaxis.zerolinecolor = '#cbd5e1'
    template.layout.yaxis.zeroline = False
    
    # Hover aesthetics
    template.layout.hovermode = 'x unified'
    template.layout.hoverlabel = dict(
        bgcolor="rgba(255, 255, 255, 0.95)",
        font_size=13,
        font_family="Inter, sans-serif",
        bordercolor="#e2e8f0"
    )
    
    # Premium Palette aligned with CSS variables
    template.layout.colorway = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
    
    return template
def make_header_with_download(title, graph_id, page_id="dashboard"):
    from dash import html
    import dash_bootstrap_components as dbc
    return html.Div([
        html.Span(title),
        dbc.DropdownMenu(
            [
                dbc.DropdownMenuItem("Export Chart (PDF)", id={'type': f'export-pdf-{page_id}', 'index': graph_id}),
                dbc.DropdownMenuItem("Export Chart (High-Res PNG)", id={'type': f'export-png-{page_id}', 'index': graph_id}),
                dbc.DropdownMenuItem("Export Chart (Interactive HTML)", id={'type': f'export-html-{page_id}', 'index': graph_id}),
            ],
            label=html.I(className="bi bi-download"),
            toggle_style={"background": "transparent", "border": "none", "color": "var(--color-primary)", "padding": "0"},
            align_end=True,
            className="dashboard-export-dropdown"
        )
    ], className="d-flex justify-content-between align-items-center w-100")

def wrap_graph_with_download(graph_id, graph_component, page_id="dashboard"):
    from dash import html, dcc
    return html.Div([
        dcc.Loading(
            custom_spinner=html.Div(className="skeleton-pulse"),
            children=[graph_component]
        ),
        dcc.Download(id={'type': f'download-data-{page_id}', 'index': graph_id})
    ])

def make_export_dropdown(page_id):
    import dash_bootstrap_components as dbc
    return dbc.DropdownMenu(
        label="Export Dashboard",
        children=[
            dbc.DropdownMenuItem("CSV", id={'type': f'export-csv-{page_id}', 'index': page_id}),
            dbc.DropdownMenuItem("PDF", id={'type': f'export-pdf-{page_id}', 'index': page_id}),
            dbc.DropdownMenuItem("High-Res PNG", id={'type': f'export-png-{page_id}', 'index': page_id}),
            dbc.DropdownMenuItem("Interactive HTML", id={'type': f'export-html-{page_id}', 'index': page_id}),
        ],
        color="primary",
        size="sm",
        className="float-end dashboard-export-dropdown"
    )
