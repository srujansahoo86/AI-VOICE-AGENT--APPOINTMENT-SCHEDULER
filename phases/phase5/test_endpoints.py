import os
import json
import pytest
from fastapi.testclient import TestClient
from main import app, db
from database import BOOKINGS_FILE, WAITLIST_FILE

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # Reset in-memory database cache
    db.bookings = {}
    db.waitlist = []
    db.mcp_logs = []
    # Cleanup on-disk files
    for f in [BOOKINGS_FILE, WAITLIST_FILE, "mcp_calendar.log", "bookings_sheet.csv", "gmail_drafts.log"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    yield
    db.bookings = {}
    db.waitlist = []
    db.mcp_logs = []
    for f in [BOOKINGS_FILE, WAITLIST_FILE, "mcp_calendar.log", "bookings_sheet.csv", "gmail_drafts.log"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

def test_get_slots_valid():
    # Test slots retrieval for valid topic and day
    response = client.get("/slots?day=friday&topic=KYC / Onboarding")
    assert response.status_code == 200
    data = response.json()
    assert "slots" in data
    assert len(data["slots"]) == 2
    assert "Friday 3:00 PM IST" in data["slots"]
    assert "Friday 5:30 PM IST" in data["slots"]

def test_get_slots_invalid_topic():
    # Test slots retrieval for out-of-scope topic
    response = client.get("/slots?day=friday&topic=Stocks investment")
    assert response.status_code == 400
    assert "not in the approved list" in response.json()["detail"]

def test_booking_happy_path():
    # Test booking a valid slot
    response = client.post("/book", json={
        "topic": "SIP / Mandates",
        "slot": "Friday 3:00 PM IST"
    })
    assert response.status_code == 200
    data = response.json()
    assert "booking_code" in data
    assert data["booking_code"].startswith("NL-")
    assert data["secure_link"] == f"https://advisor.example.com/complete/{data['booking_code']}"
    assert "mock_event_created" in data["mcp_status"]
    assert "mock_sheet_appended" in data["mcp_status"]
    assert "mock_draft_created" in data["mcp_status"]

    # Verify slot is now removed from availability
    slots_resp = client.get("/slots?day=friday&topic=SIP / Mandates")
    assert "Friday 3:00 PM IST" not in slots_resp.json()["slots"]
    assert "Friday 5:30 PM IST" in slots_resp.json()["slots"]

def test_booking_taken_slot():
    # Book once
    resp1 = client.post("/book", json={
        "topic": "SIP / Mandates",
        "slot": "Friday 3:00 PM IST"
    })
    assert resp1.status_code == 200

    # Try booking same slot again
    resp2 = client.post("/book", json={
        "topic": "KYC / Onboarding",
        "slot": "Friday 3:00 PM IST"
    })
    assert resp2.status_code == 400
    assert "already booked" in resp2.json()["detail"]

def test_reschedule_happy_path():
    # Book first
    book_resp = client.post("/book", json={
        "topic": "SIP / Mandates",
        "slot": "Friday 3:00 PM IST"
    })
    code = book_resp.json()["booking_code"]

    # Reschedule
    res_resp = client.post("/reschedule", json={
        "booking_code": code,
        "new_slot": "Friday 5:30 PM IST"
    })
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "success"
    assert res_resp.json()["new_slot"] == "Friday 5:30 PM IST"
    assert "mock_event_rescheduled" in res_resp.json()["mcp_status"]
    assert "mock_sheet_appended" in res_resp.json()["mcp_status"]

    # Verify old slot is freed and new slot is taken
    slots_resp = client.get("/slots?day=friday&topic=SIP / Mandates")
    assert "Friday 3:00 PM IST" in slots_resp.json()["slots"]
    assert "Friday 5:30 PM IST" not in slots_resp.json()["slots"]

def test_cancel_happy_path():
    # Book first
    book_resp = client.post("/book", json={
        "topic": "SIP / Mandates",
        "slot": "Friday 3:00 PM IST"
    })
    code = book_resp.json()["booking_code"]

    # Cancel
    cancel_resp = client.post("/cancel", json={
        "booking_code": code
    })
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
    assert "mock_event_cancelled" in cancel_resp.json()["mcp_status"]
    assert "mock_sheet_appended" in cancel_resp.json()["mcp_status"]

    # Verify slot is freed
    slots_resp = client.get("/slots?day=friday&topic=SIP / Mandates")
    assert "Friday 3:00 PM IST" in slots_resp.json()["slots"]

def test_waitlist_happy_path():
    response = client.post("/waitlist", json={
        "topic": "Withdrawals & Timelines",
        "preferred_day": "Monday"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "waitlisted"
    assert "Withdrawals & Timelines" in response.json()["message"]
    assert "Monday" in response.json()["message"]

def test_dashboard_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Advisor Appointment Scheduler" in response.text

def test_dashboard_data_empty():
    response = client.get("/api/dashboard-data")
    assert response.status_code == 200
    data = response.json()
    assert "bookings" in data
    assert "waitlist" in data
    assert "mcp_logs" in data
    assert len(data["bookings"]) == 0
    assert len(data["waitlist"]) == 0
    assert len(data["mcp_logs"]) == 0
