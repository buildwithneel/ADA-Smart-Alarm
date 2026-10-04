import uuid

from fastapi.testclient import TestClient


def test_destination_lifecycle(client: TestClient):
    # 1. Create Destination
    payload = {
        "name": "Downtown Office",
        "type": "office",
        "latitude": 37.789172,
        "longitude": -122.401449,
        "address": "100 California St, San Francisco, CA 94111",
        "place_id": "ChIJb8r2y5mAhYARz-0",
        "provider": "google",
        "is_favorite": True,
    }
    create_res = client.post("/api/v1/destinations", json=payload)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    dest_id = created["id"]
    assert created["name"] == "Downtown Office"
    assert created["type"] == "office"
    assert created["is_favorite"] is True

    # 2. Get Destination by ID
    get_res = client.get(f"/api/v1/destinations/{dest_id}")
    assert get_res.status_code == 200
    assert get_res.json()["address"] == payload["address"]

    # 3. List Destinations
    list_res = client.get("/api/v1/destinations")
    assert list_res.status_code == 200
    dest_list = list_res.json()
    assert any(d["id"] == dest_id for d in dest_list)

    # 4. Update Destination
    patch_payload = {
        "name": "Main Headquarters",
        "is_favorite": False,
    }
    patch_res = client.patch(f"/api/v1/destinations/{dest_id}", json=patch_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Main Headquarters"
    assert patch_res.json()["is_favorite"] is False

    # 5. Delete Destination
    del_res = client.delete(f"/api/v1/destinations/{dest_id}")
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_after_del = client.get(f"/api/v1/destinations/{dest_id}")
    assert get_after_del.status_code == 404


def test_destination_validation_errors(client: TestClient):
    # Invalid latitude (> 90)
    bad_lat = {
        "name": "North Pole Extreme",
        "type": "custom",
        "latitude": 95.0,
        "longitude": 10.0,
        "address": "Invalid Lat 95",
    }
    res = client.post("/api/v1/destinations", json=bad_lat)
    assert res.status_code == 422
    assert "validation_errors" in res.json()["details"]

    # Invalid longitude (< -180)
    bad_lng = {
        "name": "West Extreme",
        "type": "custom",
        "latitude": 10.0,
        "longitude": -195.0,
        "address": "Invalid Lng -195",
    }
    res = client.post("/api/v1/destinations", json=bad_lng)
    assert res.status_code == 422


def test_destination_not_found(client: TestClient):
    random_id = uuid.uuid4()
    res = client.get(f"/api/v1/destinations/{random_id}")
    assert res.status_code == 404
    data = res.json()
    assert data["title"] == "NOT_FOUND"
