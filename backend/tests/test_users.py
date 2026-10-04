from fastapi.testclient import TestClient

from app.models.user import User


def test_get_current_user_profile(client: TestClient, test_user: User):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name
    assert data["preference"] is not None
    assert data["preference"]["default_transportation"] == "driving"


def test_update_user_preferences(client: TestClient, test_user: User):
    update_payload = {
        "default_transportation": "transit",
        "default_preparation_time": 45,
        "default_safety_buffer": 20,
        "theme": "light",
        "sound_enabled": False,
    }
    response = client.patch("/api/v1/users/me/preferences", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["default_transportation"] == "transit"
    assert data["default_preparation_time"] == 45
    assert data["default_safety_buffer"] == 20
    assert data["theme"] == "light"
    assert data["sound_enabled"] is False

    # Verify retrieval reflects changes
    me_resp = client.get("/api/v1/users/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["preference"]["default_preparation_time"] == 45
