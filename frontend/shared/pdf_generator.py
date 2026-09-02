import io
import plotly.graph_objects as go

def generate_single_chart_pdf(fig_dict):
    """Generate a single-page PDF containing one Plotly figure."""
    fig = go.Figure(fig_dict)
    pdf_bytes = fig.to_image(format="pdf")
    return pdf_bytes

def generate_single_chart_png(fig_dict):
    """Generate a single high-res PNG containing one Plotly figure."""
    fig = go.Figure(fig_dict)
    # Scale=4 gives 300+ DPI equivalent for PPT
    png_bytes = fig.to_image(format="png", scale=4)
    return png_bytes

def generate_single_chart_html(fig_dict):
    """Generate a standalone interactive HTML for one Plotly figure."""
    fig = go.Figure(fig_dict)
    html_str = fig.to_html(include_plotlyjs='cdn', full_html=True)
    return html_str

def generate_dashboard_html(fig_dicts, title="Dashboard Export"):
    """Combine multiple Plotly figures into a single HTML file."""
    html_parts = [f"<html><head><title>{title}</title><script src='https://cdn.plot.ly/plotly-latest.min.js'></script></head><body style='font-family: sans-serif; padding: 20px; background-color: #f8f9fa;'>"]
    html_parts.append(f"<h1 style='text-align: center; color: #1a365d;'>{title}</h1>")
    
    for chart_title, fig_dict in fig_dicts.items():
        if not fig_dict: continue
        fig = go.Figure(fig_dict)
        # We don't need full_html or include_plotlyjs here because we manually included the script tag
        chart_html = fig.to_html(include_plotlyjs=False, full_html=False)
        
        html_parts.append(f"<div style='background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>")
        html_parts.append(f"<h3 style='color: #4a5568; margin-bottom: 15px;'>{chart_title}</h3>")
        html_parts.append(chart_html)
        html_parts.append("</div>")
        
    html_parts.append("</body></html>")
    return "\n".join(html_parts)

def generate_dashboard_pdf(fig_dicts, title="Dashboard Export"):
    """Generate a multi-page PDF containing multiple Plotly figures."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.utils import ImageReader
    
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    c.setFont("Helvetica-Bold", 16)
    
    for i, (chart_title, fig_dict) in enumerate(fig_dicts.items()):
        if not fig_dict:
            continue
            
        # Draw Title
        c.drawString(50, height - 40, f"{title} - {chart_title}")
        
        # Render Plotly figure to PNG for ReportLab
        fig = go.Figure(fig_dict)
        # Configure layout for a cleaner export
        fig.update_layout(paper_bgcolor='white', plot_bgcolor='white')
        
        img_bytes = fig.to_image(format="png", width=1200, height=700)
        img = ImageReader(io.BytesIO(img_bytes))
        
        # Draw Image
        c.drawImage(img, 50, 50, width=width-100, preserveAspectRatio=True)
        c.showPage()
        
    c.save()
    return buf.getvalue()
