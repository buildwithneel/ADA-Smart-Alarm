import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_missing_authorization_header(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["title"] == "UNAUTHORIZED"
    assert "Missing Authorization header" in response.json()["detail"]


def test_invalid_token(unauthenticated_client: TestClient):
    headers = {"Authorization": "Bearer invalid-token"}
    response = unauthenticated_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["title"] == "UNAUTHORIZED"


def test_expired_token(unauthenticated_client: TestClient):
    headers = {"Authorization": "Bearer expired-token"}
    response = unauthenticated_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["title"] == "UNAUTHORIZED"
    assert "expired" in response.json()["detail"].lower()


def test_new_user_synchronization(unauthenticated_client: TestClient, db_session: Session):
    unique_uid = f"firebase-uid-{uuid.uuid4()}"
    email = f"newuser-{uuid.uuid4()}@ada-alarm.com"
    name = "New Synced User"

    headers = {"Authorization": f"Bearer test-token:{unique_uid}:{email}:{name}"}
    response = unauthenticated_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["email"] == email
    assert data["name"] == name
    assert data["firebaseUid"] == unique_uid
    assert data["preference"] is not None
    assert data["preference"]["default_transportation"] == "driving"

    # Verify user exists in PostgreSQL database
    user = db_session.query(User).filter_by(firebase_uid=unique_uid).first()
    assert user is not None
    assert user.email == email


def test_existing_user_synchronization(unauthenticated_client: TestClient, test_user: User):
    headers = {
        "Authorization": f"Bearer test-token:{test_user.firebase_uid}:{test_user.email}:{test_user.name}"
    }
    response = unauthenticated_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["firebaseUid"] == test_user.firebase_uid


def test_cross_user_isolation(unauthenticated_client: TestClient):
    # Setup User A
    uid_a = f"uid-a-{uuid.uuid4()}"
    headers_a = {"Authorization": f"Bearer test-token:{uid_a}:user_a@ada.com:User A"}

    # Setup User B
    uid_b = f"uid-b-{uuid.uuid4()}"
    headers_b = {"Authorization": f"Bearer test-token:{uid_b}:user_b@ada.com:User B"}

    # 1. User A creates a Destination
    dest_payload = {
        "name": "User A Secret HQ",
        "type": "office",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "1 Secret Way, SF",
        "is_favorite": True,
    }
    create_dest_res = unauthenticated_client.post(
        "/api/v1/destinations", json=dest_payload, headers=headers_a
    )
    assert create_dest_res.status_code == 201
    dest_a_id = create_dest_res.json()["id"]

    # 2. User A creates an Alarm
    alarm_payload = {
        "title": "User A Alarm",
        "destination_id": dest_a_id,
        "arrival_time": "08:30:00",
        "preparation_time": 30,
        "safety_buffer": 15,
        "transportation_mode": "driving",
    }
    create_alarm_res = unauthenticated_client.post(
        "/api/v1/alarms", json=alarm_payload, headers=headers_a
    )
    assert create_alarm_res.status_code == 201
    alarm_a_id = create_alarm_res.json()["id"]

    # 3. User B tries to GET User A's Destination -> Must return 404 (Not Found)
    dest_get_b = unauthenticated_client.get(
        f"/api/v1/destinations/{dest_a_id}", headers=headers_b
    )
    assert dest_get_b.status_code == 404

    # 4. User B tries to PATCH User A's Destination -> Must return 404
    dest_patch_b = unauthenticated_client.patch(
        f"/api/v1/destinations/{dest_a_id}",
        json={"name": "Hacked Destination"},
        headers=headers_b,
    )
    assert dest_patch_b.status_code == 404

    # 5. User B tries to DELETE User A's Destination -> Must return 404
    dest_delete_b = unauthenticated_client.delete(
        f"/api/v1/destinations/{dest_a_id}", headers=headers_b
    )
    assert dest_delete_b.status_code == 404

    # 6. User B tries to GET User A's Alarm -> Must return 404
    alarm_get_b = unauthenticated_client.get(
        f"/api/v1/alarms/{alarm_a_id}", headers=headers_b
    )
    assert alarm_get_b.status_code == 404

    # 7. User B tries to create an Alarm targeting User A's Destination -> Must return 404
    alarm_hack_b = unauthenticated_client.post(
        "/api/v1/alarms",
        json={
            "title": "Infiltrator Alarm",
            "destination_id": dest_a_id,
            "arrival_time": "10:00:00",
        },
        headers=headers_b,
    )
    assert alarm_hack_b.status_code == 404

    # 8. User B lists Alarms -> Must NOT contain User A's alarm
    alarms_list_b = unauthenticated_client.get("/api/v1/alarms", headers=headers_b)
    assert alarms_list_b.status_code == 200
    b_alarm_ids = [a["id"] for a in alarms_list_b.json()]
    assert alarm_a_id not in b_alarm_ids
