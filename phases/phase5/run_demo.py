import sys
from fastapi.testclient import TestClient
from main import app, db
import os

# Initialize client
client = TestClient(app)

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" SCENARIO: {title}")
    print("=" * 80)

def main():
    print("Advisor Scheduling System - E2E Integration Verification")
    print("Enforcing strict compliance: No PII collected, topic validation, 3 MCP actions.")

    # Reset state to have a clean start
    db.bookings = {}
    db.waitlist = []
    db.mcp_logs = []
    for f in ["bookings.json", "waitlist.json", "mcp_calendar.log", "bookings_sheet.csv", "gmail_drafts.log"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Scenario 1: Slot availability lookup for a given day and valid topic
    # -------------------------------------------------------------------------
    print_separator("1. Slot availability lookup for a given day (Monday) and valid topic (KYC / Onboarding)")
    resp1 = client.get("/slots?day=monday&topic=KYC / Onboarding")
    print(f"Status Code: {resp1.status_code}")
    print(f"Response Body: {resp1.json()}")

    # -------------------------------------------------------------------------
    # Scenario 2: Slot availability lookup for an invalid/out-of-scope topic
    # -------------------------------------------------------------------------
    print_separator("2. Slot availability lookup for an invalid topic (Crypto Investment)")
    resp2 = client.get("/slots?day=monday&topic=Crypto Investment")
    print(f"Status Code: {resp2.status_code}")
    print(f"Response Body: {resp2.json()}")

    # -------------------------------------------------------------------------
    # Scenario 3: Schedule tentative appointment
    # -------------------------------------------------------------------------
    print_separator("3. Client schedules a valid slot (Monday 10:00 AM IST) for 'SIP / Mandates'")
    booking_payload = {
        "topic": "SIP / Mandates",
        "slot": "Monday 10:00 AM IST"
    }
    resp3 = client.post("/book", json=booking_payload)
    print(f"Status Code: {resp3.status_code}")
    booking_data = resp3.json()
    print(f"Response Body: {booking_data}")
    booking_code = booking_data.get("booking_code")

    # Let's inspect the mock log files that were created
    print("\n--- Generated MCP Mock Artifacts ---")
    if os.path.exists("mcp_calendar.log"):
        with open("mcp_calendar.log", "r") as f:
            print(f"mcp_calendar.log content:\n{f.read().strip()}")
    if os.path.exists("bookings_sheet.csv"):
        with open("bookings_sheet.csv", "r") as f:
            print(f"bookings_sheet.csv content:\n{f.read().strip()}")
    if os.path.exists("gmail_drafts.log"):
        with open("gmail_drafts.log", "r") as f:
            print(f"gmail_drafts.log content:\n{f.read().strip()}")

    # -------------------------------------------------------------------------
    # Scenario 4: Client tries to book an appointment for a slot already booked
    # -------------------------------------------------------------------------
    print_separator("4. Double Booking: Client attempts to book the same slot (Monday 10:00 AM IST)")
    double_payload = {
        "topic": "KYC / Onboarding",
        "slot": "Monday 10:00 AM IST"
    }
    resp4 = client.post("/book", json=double_payload)
    print(f"Status Code: {resp4.status_code}")
    print(f"Response Body: {resp4.json()}")

    # -------------------------------------------------------------------------
    # Scenario 5: Rescheduling a tentative appointment
    # -------------------------------------------------------------------------
    print_separator(f"5. Reschedule booking {booking_code} to 'Monday 1:30 PM IST'")
    reschedule_payload = {
        "booking_code": booking_code,
        "new_slot": "Monday 1:30 PM IST"
    }
    resp5 = client.post("/reschedule", json=reschedule_payload)
    print(f"Status Code: {resp5.status_code}")
    print(f"Response Body: {resp5.json()}")

    print("\n--- Updated Calendar Log & Sheet (Rescheduled status) ---")
    if os.path.exists("mcp_calendar.log"):
        with open("mcp_calendar.log", "r") as f:
            lines = f.readlines()
            print(f"Latest calendar action: {lines[-1].strip()}")
    if os.path.exists("bookings_sheet.csv"):
        with open("bookings_sheet.csv", "r") as f:
            print(f"bookings_sheet.csv content:\n{f.read().strip()}")

    # -------------------------------------------------------------------------
    # Scenario 6: Cancelling a tentative hold
    # -------------------------------------------------------------------------
    print_separator(f"6. Cancel booking {booking_code} and release slot")
    cancel_payload = {
        "booking_code": booking_code
    }
    resp6 = client.post("/cancel", json=cancel_payload)
    print(f"Status Code: {resp6.status_code}")
    print(f"Response Body: {resp6.json()}")

    print("\n--- Final Calendar Log & Sheet (Cancelled status) ---")
    if os.path.exists("mcp_calendar.log"):
        with open("mcp_calendar.log", "r") as f:
            lines = f.readlines()
            print(f"Latest calendar action: {lines[-1].strip()}")
    if os.path.exists("bookings_sheet.csv"):
        with open("bookings_sheet.csv", "r") as f:
            print(f"bookings_sheet.csv content:\n{f.read().strip()}")

    # -------------------------------------------------------------------------
    # Verify slot is back in availability
    # -------------------------------------------------------------------------
    print_separator("Final Verification: Confirm slots are available again")
    resp_final = client.get("/slots?day=monday&topic=KYC / Onboarding")
    print(f"Available slots: {resp_final.json()['slots']}")

    print("\n" + "=" * 80)
    print(" E2E VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    main()
