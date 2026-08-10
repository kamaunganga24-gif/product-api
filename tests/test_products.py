# tests/test_products.py
def test_create_and_get_product(client, auth_headers):
    prod = {"name": "Test Product", "description": "A long enough valid description", "price": 99.99, "stock": 10}
    create_res = client.post("/products", json=prod)
    assert create_res.status_code == 201
    pid = create_res.json()["id"]
    
    get_res = client.get(f"/products/{pid}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == prod["name"]