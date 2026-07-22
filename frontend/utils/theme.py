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
