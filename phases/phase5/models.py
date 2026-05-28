from pydantic import BaseModel, Field
from typing import List

# Slots Endpoint Models
class SlotResponse(BaseModel):
    slots: List[str] = Field(..., description="List of available scheduling slots in IST format")

# Booking Endpoint Models
class BookingRequest(BaseModel):
    topic: str = Field(..., description="Approved topic, e.g., 'SIP/Mandates'")
    slot: str = Field(..., description="Target slot string, e.g., 'Friday 3:00 PM IST'")

class BookingResponse(BaseModel):
    booking_code: str = Field(..., description="Unique booking code NL-XXXX")
    secure_link: str = Field(..., description="Link to securely complete personal details later")
    mcp_status: str = Field(..., description="Integration status for Calendar, Sheets, and Gmail drafts")
    message: str = Field(..., description="Status description message")

# Reschedule Endpoint Models
class RescheduleRequest(BaseModel):
    booking_code: str = Field(..., description="Existing unique booking code NL-XXXX")
    new_slot: str = Field(..., description="New target slot in IST format")

class RescheduleResponse(BaseModel):
    status: str = Field(..., description="Outcome status, e.g., 'success'")
    booking_code: str = Field(..., description="Target booking code NL-XXXX")
    new_slot: str = Field(..., description="Updated slot in IST format")
    mcp_status: str = Field(..., description="Integrations update status")

# Cancellation Endpoint Models
class CancelRequest(BaseModel):
    booking_code: str = Field(..., description="Active unique booking code NL-XXXX")

class CancelResponse(BaseModel):
    status: str = Field(..., description="Outcome status, e.g., 'cancelled'")
    booking_code: str = Field(..., description="Target booking code NL-XXXX")
    mcp_status: str = Field(..., description="Integrations cancellation status")

# Waitlist Endpoint Models
class WaitlistRequest(BaseModel):
    topic: str = Field(..., description="Approved topic, e.g., 'SIP/Mandates'")
    preferred_day: str = Field(..., description="User's preferred day, e.g., 'Friday'")

class WaitlistResponse(BaseModel):
    status: str = Field(..., description="Outcome status, e.g., 'waitlisted'")
    message: str = Field(..., description="Information message regarding waitlist confirmation")
