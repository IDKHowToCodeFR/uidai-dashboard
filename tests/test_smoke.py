import pytest

def test_backend_import():
    try:
        from backend.main import app
        assert app is not None
        assert app.title == "UIDAI Backend API"
    except Exception as e:
        pytest.fail(f"Backend import failed: {e}")

def test_frontend_import():
    try:
        from frontend.app import app
        assert app is not None
    except Exception as e:
        pytest.fail(f"Frontend import failed: {e}")
