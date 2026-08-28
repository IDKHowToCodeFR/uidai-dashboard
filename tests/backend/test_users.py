def test_get_users(auth_client):
    response = auth_client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, dict)
    # the admin user should be seeded
    assert "admin" in users

def test_add_user(auth_client):
    new_user = {
        "username": "testuser",
        "password": "testpassword",
        "companies": ["Digitech"],
        "permissions": []
    }
    response = auth_client.post("/users/add", json=new_user)
    assert response.status_code == 200
    
    # Verify user was added
    response = auth_client.get("/users")
    users = response.json()
    assert "testuser" in users
