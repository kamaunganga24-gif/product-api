# tests/test_auth.py
def test_register_user(client, test_user):
    response = client.post("/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == test_user["username"]
    assert "password" not in data

def test_login_user(client, test_user):
    client.post("/register", json=test_user)
    response = client.post("/login", data={"username": test_user["username"], "password": test_user["password"]})
    assert response.status_code == 200
    assert "access_token" in response.json()