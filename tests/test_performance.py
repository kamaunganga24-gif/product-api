# tests/test_performance.py
import pytest

@pytest.mark.benchmark
def test_create_product_performance(client, benchmark):
    prod = {"name": "Benchmark Item", "description": "High performance benchmarking payload item", "price": 10.0, "stock": 100}
    def create():
        return client.post("/products", json=prod)
    res = benchmark(create)
    assert res.status_code == 201