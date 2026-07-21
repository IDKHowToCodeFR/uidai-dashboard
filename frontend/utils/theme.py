import plotly.io as pio
import plotly.graph_objects as go

def get_plotly_template():
    """
    Returns a Plotly graph template matching the PostHog light theme.
    """
    template = pio.templates["plotly_white"]
    
    # Customize the template
    template.layout.paper_bgcolor = '#ffffff'  # Card background color
    template.layout.plot_bgcolor = '#ffffff'   # Inner plot background
    template.layout.font.color = '#4d4f46'     # Body text color
    template.layout.font.family = 'IBM Plex Sans Variable, IBM Plex Sans, sans-serif'
    
    # Grid lines
    template.layout.xaxis.gridcolor = '#dcdfd2' # Hairline soft
    template.layout.yaxis.gridcolor = '#dcdfd2'
    template.layout.xaxis.zerolinecolor = '#bfc1b7' # Hairline
    template.layout.yaxis.zerolinecolor = '#bfc1b7'
    
    # Default colors (PostHog Primary Yellow, Accent Blue, Accent Red)
    template.layout.colorway = ['#f7a501', '#2c84e0', '#cd4239', '#2c8c66']
    
    return template
