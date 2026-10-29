import pytest

def test_admin_login_happy_path(client):
    response = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_admin_login_invalid_password(client):
    response = client.post("/api/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401

def test_admin_protected_endpoint_rejects_missing_token(client):
    response = client.get("/api/admin/documents")
    assert response.status_code == 401
    assert "Missing or invalid" in response.json()["detail"]

def test_admin_structured_data_entry(client):
    # 1. Login
    login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add Faculty
    fac_payload = {
        "name": "Dr. K. S. Rao",
        "department": "Computer Science & Engineering",
        "designation": "Professor & HOD",
        "cabin": "Room 301",
        "block": "C-Block (Ramanujan Block)",
        "email": "ksrao.cse@geethanjali.edu.in"
    }
    fac_res = client.post("/api/admin/faculty", json=fac_payload, headers=headers)
    assert fac_res.status_code == 200
    assert "Faculty added successfully" in fac_res.json()["message"]

    # 3. Add Timetable
    tt_payload = {
        "section": "CSE-B",
        "day": "Monday",
        "period": 1,
        "start_time": "09:15 AM",
        "end_time": "10:10 AM",
        "subject": "Operating Systems",
        "room": "C-302"
    }
    tt_res = client.post("/api/admin/timetable", json=tt_payload, headers=headers)
    assert tt_res.status_code == 200

    # 4. Query from public chat to verify structured tool grounding
    chat_res = client.post("/api/chat", json={"message": "Where is Dr. K. S. Rao's cabin?", "language": "en"})
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["ticket"] is None
    assert len(chat_data["sources"]) > 0
    assert "Faculty Directory" in chat_data["sources"][0]["title"]
