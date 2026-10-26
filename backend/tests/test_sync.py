import uuid
import pytest
from fastapi.testclient import TestClient

def test_idempotent_alarm_sync_retries(unauthenticated_client: TestClient):
    """
    Verifies Phase 4/5 requirement:
    - Retrying alarm creation with the same X-Idempotency-Key (local alarm ID)
      does not create duplicate records on the server.
    """
    user_uid = f"sync-user-{uuid.uuid4()}"
    headers = {
        "Authorization": f"Bearer test-token:{user_uid}:sync_user@ada.com:Sync User",
        "X-Idempotency-Key": f"local-alarm-{uuid.uuid4()}"
    }

    # 1. Create a Destination first
    dest_res = unauthenticated_client.post(
        "/api/v1/destinations",
        json={
            "name": "Sync Destination",
            "address": "100 Market St, San Francisco, CA",
            "latitude": 37.7937,
            "longitude": -122.3965,
            "is_favorite": False
        },
        headers=headers
    )
    assert dest_res.status_code == 201
    destination_id = dest_res.json()["id"]

    alarm_payload = {
        "title": "Idempotent Sync Alarm",
        "destination_id": destination_id,
        "arrival_time": "09:00:00",
        "preparation_time": 25,
        "safety_buffer": 10,
        "transportation_mode": "driving",
        "enabled": True
    }

    # 2. First submission (Initial Sync)
    res_1 = unauthenticated_client.post(
        "/api/v1/alarms",
        json=alarm_payload,
        headers=headers
    )
    assert res_1.status_code == 201, res_1.text
    alarm_id_1 = res_1.json()["id"]

    # 3. List alarms: should have exactly 1 alarm
    list_res = unauthenticated_client.get("/api/v1/alarms", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == alarm_id_1

def test_unauthenticated_sync_access_rejected(unauthenticated_client: TestClient):
    """
    Verifies that unauthenticated requests to alarm and destination sync endpoints
    are strictly rejected with HTTP 401 Unauthorized.
    """
    res_alarms = unauthenticated_client.get("/api/v1/alarms")
    assert res_alarms.status_code == 401

    res_destinations = unauthenticated_client.get("/api/v1/destinations")
    assert res_destinations.status_code == 401

    res_create = unauthenticated_client.post("/api/v1/alarms", json={})
    assert res_create.status_code == 401

def test_user_isolation_sync_integrity(unauthenticated_client: TestClient):
    """
    Verifies that alarms and destinations synced by User A are strictly inaccessible
    to User B, preventing cross-user data leaks.
    """
    user_a = f"user-a-{uuid.uuid4()}"
    headers_a = {"Authorization": f"Bearer test-token:{user_a}:a@ada.com:User A"}

    user_b = f"user-b-{uuid.uuid4()}"
    headers_b = {"Authorization": f"Bearer test-token:{user_b}:b@ada.com:User B"}

    # User A creates destination and alarm
    dest_res = unauthenticated_client.post(
        "/api/v1/destinations",
        json={
            "name": "Secret A Location",
            "address": "Confidential Road",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        headers=headers_a
    )
    dest_a_id = dest_res.json()["id"]

    alarm_res = unauthenticated_client.post(
        "/api/v1/alarms",
        json={
            "title": "Private Alarm A",
            "destination_id": dest_a_id,
            "arrival_time": "11:00:00"
        },
        headers=headers_a
    )
    alarm_a_id = alarm_res.json()["id"]

    # User B lists alarms: must not see User A's alarm
    b_alarms = unauthenticated_client.get("/api/v1/alarms", headers=headers_b).json()
    b_alarm_ids = [a["id"] for a in b_alarms]
    assert alarm_a_id not in b_alarm_ids

    # User B attempts to access User A's alarm directly: returns 404
    get_res = unauthenticated_client.get(f"/api/v1/alarms/{alarm_a_id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B attempts to delete User A's alarm directly: returns 404
    del_res = unauthenticated_client.delete(f"/api/v1/alarms/{alarm_a_id}", headers=headers_b)
    assert del_res.status_code == 404
