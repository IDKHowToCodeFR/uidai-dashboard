def test_login_success(client):
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_failure(client):
    response = client.post("/login", data={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401

def test_access_protected_route_without_token(client):
    response = client.get("/users")
    assert response.status_code == 401
