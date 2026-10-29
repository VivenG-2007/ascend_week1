"""
Test User & Admin Authentication and User-Stamped Ticket Escalation
"""
import pytest

def test_user_registration_and_login(client):
    # 1. Register a student
    reg_payload = {
        "username": "student_rahul",
        "email": "rahul.sharma@gcet.edu.in",
        "password": "Password123!",
        "full_name": "Rahul Sharma",
        "role": "student",
        "department": "CSE",
        "phone": "+91 9876543210",
        "student_id": "21BD1A0501"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["username"] == "student_rahul"
    assert reg_data["user"]["role"] == "student"

    # 2. Login as the student
    login_res = client.post("/api/auth/login", json={
        "username": "student_rahul",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    student_token = login_data["access_token"]
    assert student_token is not None

    # 3. Check /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "rahul.sharma@gcet.edu.in"
    assert me_res.json()["full_name"] == "Rahul Sharma"

def test_admin_login_via_auth_router(client):
    # Admin login via unified auth endpoint
    admin_res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert admin_res.status_code == 200
    data = admin_res.json()
    assert data["user"]["role"] == "admin"
    assert "access_token" in data

def test_ticket_raised_with_user_details(client):
    # 1. Register user Anita (Hostel inquiry)
    reg_res = client.post("/api/auth/register", json={
        "username": "anita_k",
        "email": "anita.k@gcet.edu.in",
        "password": "SecretPassword1",
        "full_name": "Anita Kumari",
        "role": "student",
        "department": "ECE",
        "phone": "+91 9848012345",
        "student_id": "22BD1A0412"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ask question with no official doc in DB -> triggers escalation ticket
    chat_res = client.post("/api/chat", json={
        "message": "When is the girls hostel gate closing time on weekends?",
        "language": "en"
    }, headers=headers)

    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    ticket = chat_data["ticket"]
    assert ticket is not None
    assert ticket["department"] == "Hostel"
    assert ticket["user_name"] == "Anita Kumari"
    assert ticket["user_email"] == "anita.k@gcet.edu.in"
    assert ticket["user_phone"] == "+91 9848012345"

    # Personalized answer addressing Anita
    assert "Anita" in chat_data["answer_text"]

    # 3. Anita checks her tickets
    my_tickets_res = client.get("/api/auth/my-tickets", headers=headers)
    assert my_tickets_res.status_code == 200
    user_tickets = my_tickets_res.json()
    assert len(user_tickets) >= 1
    assert any(t["id"] == ticket["id"] for t in user_tickets)

    # 4. Admin logs in and checks /api/admin/tickets - sees Anita's details on the ticket
    admin_login = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    admin_tickets_res = client.get("/api/admin/tickets", headers=admin_headers)
    assert admin_tickets_res.status_code == 200
    all_tickets = admin_tickets_res.json()
    matched = [t for t in all_tickets if t["id"] == ticket["id"]]
    assert len(matched) == 1
    assert matched[0]["user_name"] == "Anita Kumari"
    assert matched[0]["user_email"] == "anita.k@gcet.edu.in"
    assert matched[0]["user_phone"] == "+91 9848012345"
