ADMIN_HEADERS = {"X-User-Id": "admin_1", "X-User-Role": "admin"}
CUST_HEADERS = {"X-User-Id": "cust_1", "X-User-Role": "customer"}

def test_create_product(client):
    response = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Test Product", "description": "A test product", "price": 19.99, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "PROD001"
    assert data["price"] == 19.99
    assert data["total_quantity"] == 10
    assert data["available_quantity"] == 10
    assert "id" in data

def test_customer_cannot_create_product(client):
    response = client.post(
        "/products/",
        json={"sku": "PROD_CUST", "name": "Cust Product", "price": 19.99, "total_quantity": 10},
        headers=CUST_HEADERS
    )
    assert response.status_code == 403
    json_data = response.json()
    assert json_data["error_code"] == "HTTP_ERROR"
    assert "Admin role required" in json_data["message"]

def test_create_duplicate_sku(client):
    client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Product 1", "price": 9.99, "total_quantity": 5},
        headers=ADMIN_HEADERS
    )
    response = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Product 2", "price": 14.99, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["error_code"] == "INVALID_STATE"
    assert "already exists" in json_data["message"]

def test_read_product(client):
    create_resp = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Test Product", "price": 25.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = create_resp.json()["id"]

    response = client.get(f"/products/{product_id}", headers=CUST_HEADERS)
    assert response.status_code == 200
    assert response.json()["name"] == "Test Product"

def test_read_product_not_found(client):
    response = client.get("/products/9999", headers=CUST_HEADERS)
    assert response.status_code == 404
    assert response.json()["error_code"] == "RESOURCE_NOT_FOUND"

def test_update_product(client):
    create_resp = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Test Product", "price": 25.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = create_resp.json()["id"]

    response = client.put(
        f"/products/{product_id}",
        json={"name": "Updated Product Name", "price": 29.99, "total_quantity": 15},
        headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Product Name"
    assert data["price"] == 29.99
    assert data["total_quantity"] == 15
    assert data["available_quantity"] == 15

def test_customer_cannot_update_product(client):
    create_resp = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Test Product", "price": 25.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = create_resp.json()["id"]

    response = client.put(
        f"/products/{product_id}",
        json={"name": "Updated Product Name"},
        headers=CUST_HEADERS
    )
    assert response.status_code == 403

def test_delete_product(client):
    create_resp = client.post(
        "/products/",
        json={"sku": "PROD001", "name": "Test Product", "price": 25.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/products/{product_id}", headers=ADMIN_HEADERS)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/products/{product_id}", headers=CUST_HEADERS)
    assert get_resp.status_code == 404

def test_invalid_negative_price(client):
    response = client.post(
        "/products/",
        json={"sku": "PROD_NEG", "name": "Bad Product", "price": -5.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "price" in json_data["message"]
