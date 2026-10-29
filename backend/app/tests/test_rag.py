import io
import pytest

def test_document_ingestion_and_rag_precedence(client):
    # 1. Admin Login
    login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Document 1 (Older Circular)
    doc1_content = b"Circular No. ACAD/2026/04 Dated 15 September 2026. The last date to pay Odd Semester Tuition Fees is 15 October 2026. Late fine of Rs. 500 applies."
    files1 = {
        "file": ("circular_fee_v1.txt", io.BytesIO(doc1_content), "text/plain")
    }
    data1 = {
        "title": "Circular No. ACAD/2026/04: Tuition Fee Schedule (Initial)",
        "category": "Circular",
        "department": "Accounts",
        "source_date": "2026-09-15"
    }
    res1 = client.post("/api/admin/documents", files=files1, data=data1, headers=headers)
    assert res1.status_code == 200
    doc1_id = res1.json()["document_id"]
    assert res1.json()["status"] == "completed"

    # 3. Upload Document 2 (Revised Circular superseding Document 1)
    doc2_content = b"Circular No. ACAD/2026/12 Dated 10 October 2026. In supersession of Circular No. ACAD/2026/04, the last date to pay Odd Semester Tuition Fees without late fine is extended to 10 November 2026."
    files2 = {
        "file": ("circular_fee_v2.txt", io.BytesIO(doc2_content), "text/plain")
    }
    data2 = {
        "title": "Circular No. ACAD/2026/12: Revised Tuition Fee Payment Schedule",
        "category": "Circular",
        "department": "Accounts",
        "source_date": "2026-10-10",
        "replaces_doc_id": doc1_id
    }
    res2 = client.post("/api/admin/documents", files=files2, data=data2, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "completed"

    # 4. Query RAG via public chat: check that query is grounded and revised document takes precedence
    chat_res = client.post("/api/chat", json={
        "message": "When is the last date to pay semester fees?",
        "language": "en"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["ticket"] is None
    assert len(chat_data["sources"]) > 0

    # The top source should be the revised circular dated 2026-10-10
    top_source = chat_data["sources"][0]
    assert top_source["source_date"] == "2026-10-10"
    assert "Revised" in top_source["title"]
