def test_chat_empty_db_triggers_escalation_ticket(client):
    """When DB is clean/empty, unanswerable college inquiry triggers deterministic ticket creation."""
    payload = {
        "message": "When is the last date to pay semester fees?",
        "language": "en"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "When is the last date to pay semester fees?"
    assert data["language"] == "en"
    assert data["ticket"] is not None
    assert data["ticket"]["id"].startswith("TKT-")
    assert "ticket" in data["answer_text"].lower()
    assert data["stt_ms"] == 0.0

def test_chat_telugu_empty_db_triggers_escalation_ticket(client):
    """Telugu question on unseeded DB triggers ticket in Telugu."""
    payload = {
        "message": "ఫీజు చెల్లించడానికి చివరి తేదీ ఎప్పుడు?",
        "language": "te"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "te"
    assert data["ticket"] is not None
    assert "టికెట్" in data["answer_text"]

def test_chat_empty_message_validation(client):
    payload = {
        "message": "   ",
        "language": "en"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 400
