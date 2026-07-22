import plotly.io as pio
import plotly.graph_objects as go

def get_plotly_template():
    """
    Returns a Plotly graph template matching the PostHog cream canvas theme.
    """
    template = pio.templates["plotly_white"]
    
    # Customize the template
    template.layout.paper_bgcolor = 'rgba(0,0,0,0)'  # Transparent to let surface-card show
    template.layout.plot_bgcolor = 'rgba(0,0,0,0)'   # Transparent
    template.layout.font.color = '#4d4f46'     # --color-body
    template.layout.font.family = 'IBM Plex Sans, sans-serif'
    
    # Grid lines
    template.layout.xaxis.gridcolor = '#dcdfd2' # --color-hairline-soft
    template.layout.yaxis.gridcolor = '#dcdfd2'
    template.layout.xaxis.zerolinecolor = '#bfc1b7' # --color-hairline
    template.layout.yaxis.zerolinecolor = '#bfc1b7'
    
    # Premium Palette (PostHog Accent Colors)
    template.layout.colorway = ['#2c84e0', '#cd4239', '#2c8c66', '#f7a501', '#7c44a6', '#1078a3']
    
    return template
