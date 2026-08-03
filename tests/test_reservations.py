from datetime import datetime, timedelta, timezone
from app.models.reservation import Reservation, ReservationStatus

ADMIN_HEADERS = {"X-User-Id": "admin_1", "X-User-Role": "admin"}
CUST1_HEADERS = {"X-User-Id": "cust_1", "X-User-Role": "customer"}
CUST2_HEADERS = {"X-User-Id": "cust_2", "X-User-Role": "customer"}

def test_create_reservation_success(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_A", "name": "Product A", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    # Reserve 4 units
    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 4},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_data = res_resp.json()
    assert res_data["quantity"] == 4
    assert res_data["status"] == "RESERVED"
    assert res_data["user_id"] == "cust_1"
    assert "expires_at" in res_data

    # Check available stock is now 6
    product_resp_after = client.get(f"/products/{product_id}", headers=CUST1_HEADERS)
    assert product_resp_after.json()["available_quantity"] == 6

def test_create_reservation_insufficient_stock(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_B", "name": "Product B", "price": 10.0, "total_quantity": 5},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    # Try to reserve 6 units (total is 5)
    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 6},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 400
    json_data = res_resp.json()
    assert json_data["error_code"] == "INSUFFICIENT_STOCK"
    assert "Insufficient stock" in json_data["message"]

def test_confirm_reservation(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_C", "name": "Product C", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # Confirm reservation
    confirm_resp = client.post(f"/reservations/{res_id}/confirm", headers=CUST1_HEADERS)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "CONFIRMED"

def test_cancel_reservation(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_D", "name": "Product D", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # Cancel reservation
    cancel_resp = client.post(f"/reservations/{res_id}/cancel", headers=CUST1_HEADERS)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Stock should be freed up
    product_resp_after = client.get(f"/products/{product_id}", headers=CUST1_HEADERS)
    assert product_resp_after.json()["available_quantity"] == 10

def test_expired_reservation_cannot_confirm(client, db):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_E", "name": "Product E", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # Modify expires_at in the db to make it expired
    db_res = db.get(Reservation, res_id)
    db_res.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.add(db_res)
    db.commit()

    # Try to confirm the expired reservation
    confirm_resp = client.post(f"/reservations/{res_id}/confirm", headers=CUST1_HEADERS)
    assert confirm_resp.status_code == 400
    json_data = confirm_resp.json()
    assert json_data["error_code"] == "INVALID_STATE"
    assert "expired" in json_data["message"].lower()

    # Available stock should be back to 10
    product_resp_after = client.get(f"/products/{product_id}", headers=CUST1_HEADERS)
    assert product_resp_after.json()["available_quantity"] == 10

def test_cleanup_expired(client, db):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_F", "name": "Product F", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 3},
        headers=CUST1_HEADERS
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # Make it expired
    db_res = db.get(Reservation, res_id)
    db_res.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.add(db_res)
    db.commit()

    # Call cleanup
    cleanup_resp = client.post("/reservations/cleanup", headers=ADMIN_HEADERS)
    assert cleanup_resp.status_code == 200
    assert cleanup_resp.json()["message"] == "Successfully cleaned up 1 expired reservations."

    # Status should be EXPIRED
    get_resp = client.get(f"/reservations/{res_id}", headers=ADMIN_HEADERS)
    assert get_resp.json()["status"] == "EXPIRED"

def test_customer_cleanup_denied(client):
    response = client.post("/reservations/cleanup", headers=CUST1_HEADERS)
    assert response.status_code == 403

def test_concurrency_reservation_no_overselling(client):
    import concurrent.futures

    # Create product with stock 5
    product_resp = client.post(
        "/products/",
        json={"sku": "CONCUR_PROD", "name": "Concur Product", "price": 10.0, "total_quantity": 5},
        headers=ADMIN_HEADERS
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    # Target function for concurrent threads
    def make_reservation():
        response = client.post(
            "/reservations/",
            json={"product_id": product_id, "quantity": 1},
            headers=CUST1_HEADERS
        )
        return response.status_code

    # Spawn 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_reservation) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Exactly 5 reservations must succeed (201) and exactly 5 must fail (400)
    success_count = results.count(201)
    fail_count = results.count(400)

    assert success_count == 5
    assert fail_count == 5

    # Check available stock is 0
    product_resp_after = client.get(f"/products/{product_id}", headers=CUST1_HEADERS)
    assert product_resp_after.json()["available_quantity"] == 0

    # Verify reservations database integrity via API list endpoint
    res_list_resp = client.get("/reservations/", headers=ADMIN_HEADERS)
    assert res_list_resp.status_code == 200
    prod_reservations = [r for r in res_list_resp.json() if r["product_id"] == product_id]
    assert len(prod_reservations) == 5
    for r in prod_reservations:
        assert r["status"] == "RESERVED"
        assert r["quantity"] == 1

def test_strict_transitions_and_duplicate_cancels(client, db):
    # Create product
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_TRANS", "name": "Transition Product", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = product_resp.json()["id"]

    # Create reservation
    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 2},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # 1. Cancel once -> succeeds
    cancel_resp1 = client.post(f"/reservations/{res_id}/cancel", headers=CUST1_HEADERS)
    assert cancel_resp1.status_code == 200
    assert cancel_resp1.json()["status"] == "CANCELLED"

    # 2. Cancel again -> fails (400)
    cancel_resp2 = client.post(f"/reservations/{res_id}/cancel", headers=CUST1_HEADERS)
    assert cancel_resp2.status_code == 400
    json_data = cancel_resp2.json()
    assert json_data["error_code"] == "INVALID_STATE"
    assert "already been cancelled" in json_data["message"]

    # 3. Confirm cancelled reservation -> fails (400)
    confirm_resp = client.post(f"/reservations/{res_id}/confirm", headers=CUST1_HEADERS)
    assert confirm_resp.status_code == 400
    assert confirm_resp.json()["error_code"] == "INVALID_STATE"
    assert "Cannot confirm" in confirm_resp.json()["message"]

def test_cannot_cancel_confirmed_reservation(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_TRANS_2", "name": "Transition Product 2", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = product_resp.json()["id"]

    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 2},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # Confirm first
    confirm_resp = client.post(f"/reservations/{res_id}/confirm", headers=CUST1_HEADERS)
    assert confirm_resp.status_code == 200

    # Attempt to cancel confirmed reservation -> fails (400)
    cancel_resp = client.post(f"/reservations/{res_id}/cancel", headers=CUST1_HEADERS)
    assert cancel_resp.status_code == 400
    assert cancel_resp.json()["error_code"] == "INVALID_STATE"
    assert "Cannot cancel a purchased reservation" in cancel_resp.json()["message"]

def test_ownership_authorization(client):
    product_resp = client.post(
        "/products/",
        json={"sku": "PROD_OWNER", "name": "Owner Product", "price": 10.0, "total_quantity": 10},
        headers=ADMIN_HEADERS
    )
    product_id = product_resp.json()["id"]

    # Cust 1 reserves
    res_resp = client.post(
        "/reservations/",
        json={"product_id": product_id, "quantity": 2},
        headers=CUST1_HEADERS
    )
    res_id = res_resp.json()["id"]

    # Cust 2 tries to read Cust 1's reservation -> fails (403)
    read_resp = client.get(f"/reservations/{res_id}", headers=CUST2_HEADERS)
    assert read_resp.status_code == 403
    assert read_resp.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # Cust 2 tries to cancel Cust 1's reservation -> fails (403)
    cancel_resp = client.post(f"/reservations/{res_id}/cancel", headers=CUST2_HEADERS)
    assert cancel_resp.status_code == 403
    assert cancel_resp.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # Cust 2 tries to confirm Cust 1's reservation -> fails (403)
    confirm_resp = client.post(f"/reservations/{res_id}/confirm", headers=CUST2_HEADERS)
    assert confirm_resp.status_code == 403
    assert confirm_resp.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # Admin CAN read Cust 1's reservation -> succeeds (200)
    admin_read = client.get(f"/reservations/{res_id}", headers=ADMIN_HEADERS)
    assert admin_read.status_code == 200

def test_invalid_negative_quantity(client):
    response = client.post(
        "/reservations/",
        json={"product_id": 1, "quantity": -5},
        headers=CUST1_HEADERS
    )
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "quantity" in json_data["message"]
