# tests/test_integration.py
def test_full_crud_flow(client):
    user = {"username": "flowuser", "email": "flow@example.com", "password": "pass1234password"}
    client.post("/register", json=user)
    login_res = client.post("/login", data={"username": user["username"], "password": user["password"]})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    prod = {"name": "Integration Laptop", "description": "A high performance developer laptop", "price": 1299.99, "stock": 5}
    create_res = client.post("/products", json=prod, headers=headers)
    assert create_res.status_code == 201
    pid = create_res.json()["id"]

    patch_res = client.patch(f"/products/{pid}", json={"price": 1199.99}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["price"] == 1199.99

    del_res = client.delete(f"/products/{pid}", headers=headers)
    assert del_res.status_code == 204