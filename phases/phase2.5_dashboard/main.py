from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
import os
from models import (
    SlotResponse, BookingRequest, BookingResponse,
    RescheduleRequest, RescheduleResponse,
    CancelRequest, CancelResponse,
    WaitlistRequest, WaitlistResponse
)
from database import SchedulerDB

app = FastAPI(
    title="Advisor Appointment Scheduler API",
    description="Backend API for managing tentative advisor appointment scheduling and MCP notifications."
)

# Initialize database
db = SchedulerDB()

@app.get("/", response_class=HTMLResponse)
def read_root():
    dashboard_path = os.path.join("templates", "dashboard.html")
    if not os.path.exists(dashboard_path):
        return """
        <html>
            <head><title>Dashboard Not Found</title></head>
            <body style="background-color: #0d0f14; color: #a9b2c3; font-family: sans-serif; text-align: center; padding-top: 100px;">
                <h2>Advisor Dashboard HTML file not found</h2>
                <p>Ensure templates/dashboard.html exists in the project workspace.</p>
            </body>
        </html>
        """
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/dashboard-data")
def get_dashboard_data():
    return {
        "bookings": list(db.bookings.values()),
        "waitlist": db.waitlist,
        "mcp_logs": db.mcp_logs
    }

@app.get("/slots", response_model=SlotResponse)
def get_slots(
    day: str = Query(..., description="Day to look up slots for, e.g. 'friday'"),
    topic: str = Query(..., description="Approved topic, e.g. 'SIP/Mandates'")
):
    # Validate topic
    if not db.is_valid_topic(topic):
        raise HTTPException(status_code=400, detail=f"Topic '{topic}' is not in the approved list of topics.")
        
    slots = db.get_available_slots(day)
    return SlotResponse(slots=slots)

@app.post("/book", response_model=BookingResponse)
def book_appointment(request: BookingRequest):
    # Validate topic
    if not db.is_valid_topic(request.topic):
        raise HTTPException(status_code=400, detail=f"Topic '{request.topic}' is not in the approved list.")
        
    booking = db.create_booking(request.topic, request.slot)
    if not booking:
        raise HTTPException(status_code=400, detail="The selected slot is already booked or unavailable.")
        
    # Phase 2 placeholder for MCP actions
    return BookingResponse(
        booking_code=booking["booking_code"],
        secure_link=booking["secure_link"],
        mcp_status="pending_phase_3",
        message="Booking tentative slot successful."
    )

@app.post("/reschedule", response_model=RescheduleResponse)
def reschedule_appointment(request: RescheduleRequest):
    booking = db.reschedule_booking(request.booking_code, request.new_slot)
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="Could not reschedule. Either the booking code was not found, the booking is cancelled, or the target slot is unavailable."
        )
        
    return RescheduleResponse(
        status="success",
        booking_code=booking["booking_code"],
        new_slot=booking["slot"],
        mcp_status="pending_phase_3"
    )

@app.post("/cancel", response_model=CancelResponse)
def cancel_appointment(request: CancelRequest):
    booking = db.cancel_booking(request.booking_code)
    if not booking:
        raise HTTPException(status_code=400, detail="Booking code not found.")
        
    return CancelResponse(
        status="cancelled",
        booking_code=booking["booking_code"],
        mcp_status="pending_phase_3"
    )

@app.post("/waitlist", response_model=WaitlistResponse)
def join_waitlist(request: WaitlistRequest):
    if not db.is_valid_topic(request.topic):
        raise HTTPException(status_code=400, detail=f"Topic '{request.topic}' is not in the approved list.")
        
    entry = db.join_waitlist(request.topic, request.preferred_day)
    return WaitlistResponse(
        status="waitlisted",
        message=f"Added to waitlist for topic '{entry['topic']}' on preferred day '{entry['preferred_day']}'."
    )
