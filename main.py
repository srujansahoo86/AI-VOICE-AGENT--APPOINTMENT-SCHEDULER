from dotenv import load_dotenv
load_dotenv()  # Load .env file before any env variable reads

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
from mcp_actions import MCPActionsManager

app = FastAPI(
    title="Advisor Appointment Scheduler API",
    description="Backend API for managing tentative advisor appointment scheduling and MCP notifications."
)

# Initialize database and MCP Actions Manager
db = SchedulerDB()
mcp_manager = MCPActionsManager(db)

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
        
    # Trigger all 3 MCP actions: Calendar Hold, Sheets Row append, and Gmail draft compose
    mcp_res = mcp_manager.execute_all_mcp_book(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    mcp_status_str = f"Calendar: {mcp_res['calendar']}, Sheets: {mcp_res['sheets']}, Gmail: {mcp_res['gmail']}"
    
    return BookingResponse(
        booking_code=booking["booking_code"],
        secure_link=booking["secure_link"],
        mcp_status=mcp_status_str,
        message="Booking tentative slot successful and MCP actions triggered."
    )

@app.post("/reschedule", response_model=RescheduleResponse)
def reschedule_appointment(request: RescheduleRequest):
    booking = db.reschedule_booking(request.booking_code, request.new_slot)
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="Could not reschedule. Either the booking code was not found, the booking is cancelled, or the target slot is unavailable."
        )
        
    # Trigger MCP reschedule actions
    mcp_res = mcp_manager.execute_all_mcp_reschedule(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    mcp_status_str = f"Calendar: {mcp_res['calendar']}, Sheets: {mcp_res['sheets']}"
    
    return RescheduleResponse(
        status="success",
        booking_code=booking["booking_code"],
        new_slot=booking["slot"],
        mcp_status=mcp_status_str
    )

@app.post("/cancel", response_model=CancelResponse)
def cancel_appointment(request: CancelRequest):
    booking = db.cancel_booking(request.booking_code)
    if not booking:
        raise HTTPException(status_code=400, detail="Booking code not found.")
        
    # Trigger MCP cancellation actions
    mcp_res = mcp_manager.execute_all_mcp_cancel(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    mcp_status_str = f"Calendar: {mcp_res['calendar']}, Sheets: {mcp_res['sheets']}"
    
    return CancelResponse(
        status="cancelled",
        booking_code=booking["booking_code"],
        mcp_status=mcp_status_str
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

# ═══════════════════════════════════════════════════════════════════════════════
# Retell AI Webhook-Compatible Routes
# Retell sends tool calls as POST with body: {"args": {<actual_params>}}
# These routes unwrap the args and call existing logic.
# ═══════════════════════════════════════════════════════════════════════════════
from fastapi import Request

@app.post("/retell/get_slots")
async def retell_get_slots(req: Request):
    body = await req.json()
    args = body.get("args", body)
    day = args.get("day", "")
    topic = args.get("topic", "")
    
    if not db.is_valid_topic(topic):
        return {"result": f"Sorry, '{topic}' is not an approved topic. Approved topics are: KYC / Onboarding, SIP / Mandates, Statements / Tax Docs, Withdrawals & Timelines, Account Changes / Nominee."}
    
    slots = db.get_available_slots(day)
    if not slots:
        return {"result": f"No available slots on {day}. We offer slots on Monday, Tuesday, and Friday."}
    return {"result": f"Available slots on {day}: {', '.join(slots)}"}

@app.post("/retell/book_appointment")
async def retell_book(req: Request):
    body = await req.json()
    args = body.get("args", body)
    topic = args.get("topic", "")
    slot = args.get("slot", "")
    
    if not db.is_valid_topic(topic):
        return {"result": f"Sorry, '{topic}' is not an approved topic."}
    
    booking = db.create_booking(topic, slot)
    if not booking:
        return {"result": "That slot is already booked or unavailable. Please pick another slot."}
    
    mcp_res = mcp_manager.execute_all_mcp_book(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    return {"result": f"Booking confirmed! Your booking code is {booking['booking_code']}. A secure link will be sent to complete your registration: {booking['secure_link']}. Please note down your booking code."}

@app.post("/retell/reschedule_appointment")
async def retell_reschedule(req: Request):
    body = await req.json()
    args = body.get("args", body)
    booking_code = args.get("booking_code", "")
    new_slot = args.get("new_slot", "")
    
    booking = db.reschedule_booking(booking_code, new_slot)
    if not booking:
        return {"result": f"Could not reschedule. Either booking code {booking_code} was not found, the booking is cancelled, or the new slot is unavailable."}
    
    mcp_res = mcp_manager.execute_all_mcp_reschedule(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    return {"result": f"Successfully rescheduled booking {booking['booking_code']} to {booking['slot']}."}

@app.post("/retell/cancel_appointment")
async def retell_cancel(req: Request):
    body = await req.json()
    args = body.get("args", body)
    booking_code = args.get("booking_code", "")
    
    booking = db.cancel_booking(booking_code)
    if not booking:
        return {"result": f"Booking code {booking_code} was not found."}
    
    mcp_res = mcp_manager.execute_all_mcp_cancel(
        booking["booking_code"], booking["topic"], booking["slot"]
    )
    return {"result": f"Booking {booking['booking_code']} has been cancelled successfully."}

@app.post("/retell/join_waitlist")
async def retell_waitlist(req: Request):
    body = await req.json()
    args = body.get("args", body)
    topic = args.get("topic", "")
    preferred_day = args.get("preferred_day", "")
    
    if not db.is_valid_topic(topic):
        return {"result": f"Sorry, '{topic}' is not an approved topic."}
    
    entry = db.join_waitlist(topic, preferred_day)
    return {"result": f"You have been added to the waitlist for {entry['topic']} on {entry['preferred_day']}. We will notify you when a slot opens up."}
