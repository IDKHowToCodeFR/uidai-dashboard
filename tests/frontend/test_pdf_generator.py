import pytest
from frontend.shared.pdf_generator import generate_single_chart_png, generate_single_chart_pdf

def test_generate_single_chart_png():
    fig_dict = {
        "data": [{"type": "bar", "x": [1, 2], "y": [3, 4]}],
        "layout": {"title": "Test"}
    }
    png_bytes = generate_single_chart_png(fig_dict)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 0

def test_generate_single_chart_pdf():
    fig_dict = {
        "data": [{"type": "scatter", "x": [1], "y": [2]}],
        "layout": {"title": "Test"}
    }
    pdf_bytes = generate_single_chart_pdf(fig_dict)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
