from datetime import datetime, timedelta, timezone
from app.models.reservation import Reservation

ADMIN_HEADERS = {"X-User-Id": "admin_1", "X-User-Role": "admin"}
CUST1_HEADERS = {"X-User-Id": "cust_1", "X-User-Role": "customer"}
CUST2_HEADERS = {"X-User-Id": "cust_2", "X-User-Role": "customer"}

def test_direct_purchase_success(client):
    # Create product
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P1", "name": "Product P1", "price": 100.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["id"]

    # Direct purchase 3 units
    purchase_resp = client.post(
        "/purchases/",
        json={"product_id": prod_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert purchase_resp.status_code == 201
    pur_data = purchase_resp.json()
    assert pur_data["product_id"] == prod_id
    assert pur_data["quantity"] == 3
    assert pur_data["user_id"] == "cust_1"
    assert pur_data["total_price"] == 300.0
    assert pur_data["reservation_id"] is None

    # Verify product total stock is now 7
    prod_get = client.get(f"/products/{prod_id}", headers=CUST1_HEADERS)
    assert prod_get.json()["total_quantity"] == 7
    assert prod_get.json()["available_quantity"] == 7

def test_direct_purchase_insufficient_stock(client):
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P2", "name": "Product P2", "price": 50.0, "total_quantity": 5},
        headers=ADMIN_HEADERS
    )
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["id"]

    # Try to purchase 6 units direct
    purchase_resp = client.post(
        "/purchases/",
        json={"product_id": prod_id, "quantity": 6},
        headers=CUST1_HEADERS
    )
    assert purchase_resp.status_code == 400
    json_data = purchase_resp.json()
    assert json_data["error_code"] == "INSUFFICIENT_STOCK"
    assert "Insufficient available stock" in json_data["message"]

def test_purchase_from_reservation_success(client):
    # Create product
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P3", "name": "Product P3", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    prod_id = prod_resp.json()["id"]

    # Create reservation
    res_resp = client.post(
        "/reservations/",
        json={"product_id": prod_id, "quantity": 4},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # Available stock should be 6, total stock should be 10
    prod_get_res = client.get(f"/products/{prod_id}", headers=CUST1_HEADERS)
    assert prod_get_res.json()["available_quantity"] == 6
    assert prod_get_res.json()["total_quantity"] == 10

    # Purchase from reservation
    purchase_resp = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST1_HEADERS
    )
    assert purchase_resp.status_code == 201
    pur_data = purchase_resp.json()
    assert pur_data["product_id"] == prod_id
    assert pur_data["reservation_id"] == res_id
    assert pur_data["user_id"] == "cust_1"
    assert pur_data["quantity"] == 4
    assert pur_data["total_price"] == 40.0

    # Verify product total stock is now 6, available stock is also 6
    prod_get = client.get(f"/products/{prod_id}", headers=CUST1_HEADERS)
    assert prod_get.json()["total_quantity"] == 6
    assert prod_get.json()["available_quantity"] == 6

    # Verify reservation is CONFIRMED
    res_get = client.get(f"/reservations/{res_id}", headers=CUST1_HEADERS)
    assert res_get.json()["status"] == "CONFIRMED"

def test_purchase_from_expired_reservation_fails(client, db):
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P4", "name": "Product P4", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    prod_id = prod_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": prod_id, "quantity": 4},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # Expire reservation manually
    db_res = db.get(Reservation, res_id)
    db_res.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.add(db_res)
    db.commit()

    # Try to purchase from the expired reservation
    purchase_resp = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST1_HEADERS
    )
    assert purchase_resp.status_code == 400
    json_data = purchase_resp.json()
    assert json_data["error_code"] == "INVALID_STATE"
    assert "expired" in json_data["message"].lower()

def test_purchase_from_reservation_duplicate_fails(client):
    # Create product
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P5", "name": "Product P5", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["id"]

    # Create reservation
    res_resp = client.post(
        "/reservations/",
        json={"product_id": prod_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # 1. Purchase from reservation first -> succeeds (201)
    pur_resp1 = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST1_HEADERS
    )
    assert pur_resp1.status_code == 201

    # 2. Purchase from reservation again -> fails (400)
    pur_resp2 = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST1_HEADERS
    )
    assert pur_resp2.status_code == 400
    json_data = pur_resp2.json()
    assert json_data["error_code"] == "INVALID_STATE"
    assert "already been confirmed" in json_data["message"]

    # Verify stock decremented only once (total stock should be 7, not 4)
    prod_get = client.get(f"/products/{prod_id}", headers=CUST1_HEADERS)
    assert prod_get.json()["total_quantity"] == 7
    assert prod_get.json()["available_quantity"] == 7

def test_purchase_ownership_authorization(client):
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P6", "name": "Product P6", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    prod_id = prod_resp.json()["id"]

    # Cust 1 reserves
    res_resp = client.post(
        "/reservations/",
        json={"product_id": prod_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # Cust 2 tries to purchase Cust 1's reservation -> fails (403)
    pur_resp = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST2_HEADERS
    )
    assert pur_resp.status_code == 403
    assert pur_resp.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # Cust 1 purchases -> succeeds (201)
    pur_resp_ok = client.post(
        "/purchases/",
        json={"reservation_id": res_id},
        headers=CUST1_HEADERS
    )
    assert pur_resp_ok.status_code == 201
    pur_id = pur_resp_ok.json()["id"]

    # Cust 2 tries to read Cust 1's purchase details -> fails (403)
    read_resp = client.get(f"/purchases/{pur_id}", headers=CUST2_HEADERS)
    assert read_resp.status_code == 403
    assert read_resp.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # Admin CAN read Cust 1's purchase details -> succeeds (200)
    admin_read = client.get(f"/purchases/{pur_id}", headers=ADMIN_HEADERS)
    assert admin_read.status_code == 200

def test_invalid_negative_purchase_quantity(client):
    prod_resp = client.post(
        "/products/",
        json={"sku": "PROD_P7", "name": "Product P7", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    prod_id = prod_resp.json()["id"]

    response = client.post(
        "/purchases/",
        json={"product_id": prod_id, "quantity": -5},
        headers=CUST1_HEADERS
    )
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "quantity" in json_data["message"]
