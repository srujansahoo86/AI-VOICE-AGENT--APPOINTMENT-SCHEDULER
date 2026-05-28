import os
import json
import random
import string
from typing import Dict, List, Optional

# Approved list of topics from Section 3 of the PRD
APPROVED_TOPICS = [
    "KYC / Onboarding",
    "SIP / Mandates",
    "Statements / Tax Docs",
    "Withdrawals & Timelines",
    "Account Changes / Nominee"
]

# Hardcoded base slots available for scheduling as specified in Section 6
# Format is: { day_lower: [slots_list] }
BASE_SLOTS = {
    "friday": [
        "Friday 3:00 PM IST",
        "Friday 5:30 PM IST"
    ],
    "monday": [
        "Monday 10:00 AM IST",
        "Monday 1:30 PM IST"
    ],
    "tuesday": [
        "Tuesday 11:00 AM IST",
        "Tuesday 4:00 PM IST"
    ]
}

BOOKINGS_FILE = "bookings.json"
WAITLIST_FILE = "waitlist.json"

class SchedulerDB:
    def __init__(self):
        self.bookings_path = BOOKINGS_FILE
        self.waitlist_path = WAITLIST_FILE
        self._load_data()

    def _load_data(self):
        # Load Bookings
        if os.path.exists(self.bookings_path):
            try:
                with open(self.bookings_path, 'r', encoding='utf-8') as f:
                    self.bookings = json.load(f)
            except Exception:
                self.bookings = {}
        else:
            self.bookings = {}

        # Load Waitlist
        if os.path.exists(self.waitlist_path):
            try:
                with open(self.waitlist_path, 'r', encoding='utf-8') as f:
                    self.waitlist = json.load(f)
            except Exception:
                self.waitlist = []
        else:
            self.waitlist = []

    def _save_bookings(self):
        with open(self.bookings_path, 'w', encoding='utf-8') as f:
            json.dump(self.bookings, f, indent=2, ensure_ascii=False)

    def _save_waitlist(self):
        with open(self.waitlist_path, 'w', encoding='utf-8') as f:
            json.dump(self.waitlist, f, indent=2, ensure_ascii=False)

    def is_valid_topic(self, topic: str) -> bool:
        # Standardize topic matching to handle minor casing or spacing differences
        cleaned_topic = topic.strip().lower()
        for t in APPROVED_TOPICS:
            if t.lower() == cleaned_topic:
                return True
        return False

    def get_canonical_topic(self, topic: str) -> str:
        cleaned_topic = topic.strip().lower()
        for t in APPROVED_TOPICS:
            if t.lower() == cleaned_topic:
                return t
        return topic # fallback to original

    def generate_booking_code(self) -> str:
        # Code format: NL-XXXX where XXXX is 4 alphanumeric chars
        # Ensure uniqueness across active bookings
        characters = string.ascii_uppercase + string.digits
        while True:
            code = "NL-" + "".join(random.choices(characters, k=4))
            if code not in self.bookings:
                return code

    def get_booked_slots(self) -> List[str]:
        # Return all slots currently locked by active (non-cancelled) bookings
        return [b["slot"] for b in self.bookings.values() if b.get("status") != "Cancelled"]

    def get_available_slots(self, day: str) -> List[str]:
        day_key = day.strip().lower()
        slots = BASE_SLOTS.get(day_key, [])
        
        # Filter out slots that have already been booked
        booked_slots = self.get_booked_slots()
        available = [s for s in slots if s not in booked_slots]
        return available

    def create_booking(self, topic: str, slot: str) -> Optional[Dict]:
        canonical_topic = self.get_canonical_topic(topic)
        
        # Check slot availability
        booked_slots = self.get_booked_slots()
        if slot in booked_slots:
            return None # Slot is already taken
            
        booking_code = self.generate_booking_code()
        booking = {
            "booking_code": booking_code,
            "topic": canonical_topic,
            "slot": slot,
            "secure_link": f"https://advisor.example.com/complete/{booking_code}",
            "status": "Tentative"
        }
        
        self.bookings[booking_code] = booking
        self._save_bookings()
        return booking

    def reschedule_booking(self, booking_code: str, new_slot: str) -> Optional[Dict]:
        if booking_code not in self.bookings:
            return None # Booking not found
            
        booking = self.bookings[booking_code]
        if booking.get("status") == "Cancelled":
            return None # Cannot reschedule a cancelled booking
            
        # Ensure new slot is not already taken
        booked_slots = self.get_booked_slots()
        # Exclude the slot currently held by this booking from the overlap check
        if new_slot in booked_slots and booking["slot"] != new_slot:
            return None # New slot already taken
            
        booking["slot"] = new_slot
        booking["status"] = "Rescheduled"
        self._save_bookings()
        return booking

    def cancel_booking(self, booking_code: str) -> Optional[Dict]:
        if booking_code not in self.bookings:
            return None # Booking not found
            
        booking = self.bookings[booking_code]
        if booking.get("status") == "Cancelled":
            return booking # Already cancelled
            
        booking["status"] = "Cancelled"
        self._save_bookings()
        return booking

    def join_waitlist(self, topic: str, preferred_day: str) -> Dict:
        canonical_topic = self.get_canonical_topic(topic)
        entry = {
            "topic": canonical_topic,
            "preferred_day": preferred_day.strip().capitalize()
        }
        self.waitlist.append(entry)
        self._save_waitlist()
        return entry
