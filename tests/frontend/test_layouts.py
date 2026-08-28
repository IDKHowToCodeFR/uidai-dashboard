def test_app_layout_generation():
    from frontend.app import app
    assert app.layout is not None

def test_login_page_layout():
    from frontend.pages.login import layout
    assert layout is not None

def test_admin_logs_layout():
    from frontend.pages.admin.admin_logs import layout
    assert layout is not None
