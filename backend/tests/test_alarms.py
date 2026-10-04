import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.destination import Destination
from app.models.user import User


def create_sample_destination(client: TestClient) -> dict:
    payload = {
        "name": "Campus Library",
        "type": "college",
        "latitude": 37.4275,
        "longitude": -122.1697,
        "address": "Stanford, CA 94305",
        "provider": "mapbox",
        "is_favorite": True,
    }
    res = client.post("/api/v1/destinations", json=payload)
    assert res.status_code == 201
    return res.json()


def test_alarm_lifecycle_and_recurrence(client: TestClient):
    dest = create_sample_destination(client)
    dest_id = dest["id"]

    # 1. Create Alarm with custom schedule
    alarm_payload = {
        "title": "Morning Algorithms Lecture",
        "destination_id": dest_id,
        "arrival_time": "09:00:00",
        "preparation_time": 40,
        "safety_buffer": 20,
        "transportation_mode": "bicycling",
        "enabled": True,
        "schedule": {
            "schedule_type": "custom",
            "repeat_days": "MON,WED,FRI",
        },
    }
    create_res = client.post("/api/v1/alarms", json=alarm_payload)
    assert create_res.status_code == 201, create_res.text
    alarm_data = create_res.json()
    alarm_id = alarm_data["id"]

    assert alarm_data["title"] == "Morning Algorithms Lecture"
    assert alarm_data["arrival_time"] == "09:00:00"
    assert alarm_data["preparation_time"] == 40
    assert alarm_data["safety_buffer"] == 20
    assert alarm_data["transportation_mode"] == "bicycling"
    assert alarm_data["schedule"]["schedule_type"] == "custom"
    assert alarm_data["schedule"]["repeat_days"] == "MON,WED,FRI"

    # 2. Get Alarm by ID
    get_res = client.get(f"/api/v1/alarms/{alarm_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == alarm_id
    assert fetched["destination"]["name"] == "Campus Library"

    # 3. List Alarms
    list_res = client.get("/api/v1/alarms")
    assert list_res.status_code == 200
    alarms = list_res.json()
    assert any(a["id"] == alarm_id for a in alarms)

    # 4. Update Alarm
    patch_payload = {
        "arrival_time": "09:30:00",
        "preparation_time": 30,
        "schedule": {
            "schedule_type": "daily",
        },
    }
    patch_res = client.patch(f"/api/v1/alarms/{alarm_id}", json=patch_payload)
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["arrival_time"] == "09:30:00"
    assert patched["preparation_time"] == 30
    assert patched["schedule"]["schedule_type"] == "daily"

    # 5. Delete Alarm
    del_res = client.delete(f"/api/v1/alarms/{alarm_id}")
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_after_del = client.get(f"/api/v1/alarms/{alarm_id}")
    assert get_after_del.status_code == 404


def test_alarm_validation_errors(client: TestClient):
    dest = create_sample_destination(client)
    dest_id = dest["id"]

    # Negative preparation time
    bad_prep = {
        "title": "Bad Prep",
        "destination_id": dest_id,
        "arrival_time": "08:00:00",
        "preparation_time": -10,
    }
    res = client.post("/api/v1/alarms", json=bad_prep)
    assert res.status_code == 422

    # Preparation time > 360
    too_large_prep = {
        "title": "Too Long",
        "destination_id": dest_id,
        "arrival_time": "08:00:00",
        "preparation_time": 400,
    }
    res = client.post("/api/v1/alarms", json=too_large_prep)
    assert res.status_code == 422

    # Invalid repeat days
    bad_days = {
        "title": "Invalid Days",
        "destination_id": dest_id,
        "arrival_time": "08:00:00",
        "schedule": {
            "schedule_type": "custom",
            "repeat_days": "MON,FUNDAY",
        },
    }
    res = client.post("/api/v1/alarms", json=bad_days)
    assert res.status_code == 422


def test_alarm_destination_not_found(client: TestClient):
    bad_dest_id = uuid.uuid4()
    payload = {
        "title": "Orphan Alarm",
        "destination_id": str(bad_dest_id),
        "arrival_time": "10:00:00",
    }
    res = client.post("/api/v1/alarms", json=payload)
    assert res.status_code == 404
    assert res.json()["title"] == "NOT_FOUND"


def test_database_relationships_and_cascades(
    client: TestClient, db_session: Session, test_user: User
):
    # Create destination via API
    dest = create_sample_destination(client)
    dest_id = uuid.UUID(dest["id"])

    # Create alarm via API
    alarm_payload = {
        "title": "Cascade Test Alarm",
        "destination_id": str(dest_id),
        "arrival_time": "11:00:00",
        "schedule": {
            "schedule_type": "weekdays",
        },
    }
    alarm_res = client.post("/api/v1/alarms", json=alarm_payload)
    assert alarm_res.status_code == 201
    alarm_id = uuid.UUID(alarm_res.json()["id"])

    # Query DB directly to verify ORM relationships
    db_dest = db_session.get(Destination, dest_id)
    assert db_dest is not None
    assert len(db_dest.alarms) == 1
    assert db_dest.alarms[0].id == alarm_id
    assert db_dest.alarms[0].schedule is not None
    assert db_dest.alarms[0].schedule.schedule_type.value == "weekdays"

    # Verify User relationships
    db_user = db_session.get(User, test_user.id)
    assert db_user is not None
    assert any(a.id == alarm_id for a in db_user.alarms)
    assert any(d.id == dest_id for d in db_user.destinations)

    # Delete destination via API -> Alarm must cascade delete
    del_dest_res = client.delete(f"/api/v1/destinations/{dest_id}")
    assert del_dest_res.status_code == 204

    # Verify alarm is also deleted by cascade
    get_alarm_res = client.get(f"/api/v1/alarms/{alarm_id}")
    assert get_alarm_res.status_code == 404
