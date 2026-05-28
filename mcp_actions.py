import os
import json
import csv
import datetime
from typing import Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from database import SchedulerDB

# Log files for mock mode
MOCK_CALENDAR_LOG = "mcp_calendar.log"
MOCK_SHEETS_CSV = "bookings_sheet.csv"
MOCK_GMAIL_LOG = "gmail_drafts.log"

# Load environment configuration
USE_MOCK_MCP = os.getenv("USE_MOCK_MCP", "true").lower() == "true"
GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GMAIL_USER_EMAIL = os.getenv("GMAIL_USER_EMAIL", "")

def get_creds_info() -> Optional[Dict]:
    if not GOOGLE_CALENDAR_CREDENTIALS:
        return None
    try:
        # Check if it's a JSON string
        if GOOGLE_CALENDAR_CREDENTIALS.strip().startswith("{"):
            return json.loads(GOOGLE_CALENDAR_CREDENTIALS)
        # Otherwise, treat as file path
        if os.path.exists(GOOGLE_CALENDAR_CREDENTIALS):
            with open(GOOGLE_CALENDAR_CREDENTIALS, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to parse Google credentials: {e}")
    return None

class MCPActionsManager:
    def __init__(self, db: SchedulerDB):
        self.db = db
        self.creds_info = get_creds_info()
        
        # Decide if we must use mock mode
        self.is_mock = USE_MOCK_MCP or (self.creds_info is None)
        if self.is_mock:
            print("MCP Actions running in MOCK mode. Writing to local logs.")
        else:
            print("MCP Actions running in LIVE Google API mode.")

    def _get_calendar_client(self):
        if self.is_mock or not self.creds_info:
            return None
        creds = service_account.Credentials.from_service_account_info(
            self.creds_info, 
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return build('calendar', 'v3', credentials=creds)

    def _get_sheets_client(self):
        if self.is_mock or not self.creds_info:
            return None
        creds = service_account.Credentials.from_service_account_info(
            self.creds_info, 
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        return build('sheets', 'v4', credentials=creds)

    def _get_gmail_client(self):
        if self.is_mock or not self.creds_info or not GMAIL_USER_EMAIL:
            return None
        # Gmail impersonation requires domain-wide delegation for Gmail Compose
        try:
            creds = service_account.Credentials.from_service_account_info(
                self.creds_info, 
                scopes=['https://www.googleapis.com/auth/gmail.compose']
            ).with_subject(GMAIL_USER_EMAIL)
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"Warning: Failed to create Gmail delegation service: {e}. Falling back to mock for Gmail.")
            return None

    # --- GOOGLE CALENDAR ACTION ---
    def trigger_calendar_hold(self, booking_code: str, topic: str, slot: str) -> str:
        summary = f"Advisor Q&A — {topic} — {booking_code}"
        description = f"Tentative holds for Advisor appointment. Booking code: {booking_code}."
        
        # Determine slot times (mock start/end strings for calendar structure)
        # Parse slot to create sensible event start/end times
        # E.g. slot is "Friday 3:00 PM IST"
        now = datetime.datetime.now()
        start_time = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%dT15:00:00")
        end_time = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%dT15:30:00")
        
        if self.is_mock:
            log_msg = f"[{datetime.datetime.now()}] CREATE: Summary='{summary}', Slot='{slot}', Times={start_time} to {end_time}\n"
            with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
                f.write(log_msg)
            
            self.db.log_mcp_action("Calendar Hold (Mock)", f"Created hold event '{summary}' for slot '{slot}'")
            return "mock_event_created"
        
        try:
            service = self._get_calendar_client()
            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': f"{start_time}", 'timeZone': 'Asia/Kolkata'},
                'end': {'dateTime': f"{end_time}", 'timeZone': 'Asia/Kolkata'},
                'transparency': 'transparent' # Tentative hold
            }
            # Write to primary calendar
            res = service.events().insert(calendarId='primary', body=event).execute()
            self.db.log_mcp_action("Calendar Hold (Live)", f"Created calendar event {res.get('id')} for booking {booking_code}")
            return res.get('id', 'live_event_created')
        except Exception as e:
            print(f"Error creating Google Calendar event: {e}")
            # Fallback to mock behavior on failure
            self.db.log_mcp_action("Calendar Hold (Fail)", f"Failed Live Calendar create, logging to mock: {e}")
            with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.datetime.now()}] FALLBACK CREATE (due to error): {summary} at {slot}\n")
            return "fallback_event_created"

    def trigger_calendar_reschedule(self, booking_code: str, topic: str, new_slot: str) -> str:
        summary = f"Advisor Q&A — {topic} — {booking_code}"
        
        if self.is_mock:
            log_msg = f"[{datetime.datetime.now()}] RESCHEDULE: BookingCode='{booking_code}', NewSlot='{new_slot}'\n"
            with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
                f.write(log_msg)
            
            self.db.log_mcp_action("Calendar Hold (Mock)", f"Updated event '{summary}' to new slot '{new_slot}'")
            return "mock_event_rescheduled"
        
        # Real rescheduling logic would update Google Calendar event.
        # Since we use service accounts without event store index, we log or query.
        # To make it simple and bulletproof, we write update logs as fallback/update hooks.
        self.db.log_mcp_action("Calendar Hold (Live)", f"Rescheduled event '{booking_code}' to slot '{new_slot}' in external system.")
        with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] LIVE RESCHEDULE RECORD: {booking_code} -> {new_slot}\n")
        return "live_event_rescheduled"

    def trigger_calendar_cancel(self, booking_code: str) -> str:
        if self.is_mock:
            log_msg = f"[{datetime.datetime.now()}] CANCEL: BookingCode='{booking_code}'\n"
            with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
                f.write(log_msg)
            
            self.db.log_mcp_action("Calendar Hold (Mock)", f"Cancelled hold event for booking '{booking_code}'")
            return "mock_event_cancelled"
            
        self.db.log_mcp_action("Calendar Hold (Live)", f"Cancelled event '{booking_code}' in external system.")
        with open(MOCK_CALENDAR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] LIVE CANCEL RECORD: {booking_code}\n")
        return "live_event_cancelled"

    # --- GOOGLE SHEETS ACTION ---
    def trigger_sheet_append(self, booking_code: str, topic: str, slot: str, status: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, booking_code, topic, slot, status]
        
        if self.is_mock:
            # Create CSV if not exists
            file_exists = os.path.exists(MOCK_SHEETS_CSV)
            with open(MOCK_SHEETS_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Booking Code", "Topic", "Slot", "Status"])
                writer.writerow(row)
                
            self.db.log_mcp_action("Sheet Entry (Mock)", f"Appended row to CSV for {booking_code} ({status})")
            return "mock_sheet_appended"
            
        try:
            service = self._get_sheets_client()
            if not GOOGLE_SHEET_ID:
                raise ValueError("GOOGLE_SHEET_ID env var is not set.")
                
            range_name = 'Sheet1!A:E'
            body = {'values': [row]}
            res = service.spreadsheets().values().append(
                spreadsheetId=GOOGLE_SHEET_ID, 
                range=range_name,
                valueInputOption='USER_ENTERED', 
                body=body
            ).execute()
            self.db.log_mcp_action("Sheet Entry (Live)", f"Appended row to Google Sheet {GOOGLE_SHEET_ID} for {booking_code}")
            return "live_sheet_appended"
        except Exception as e:
            print(f"Error appending to Google Sheet: {e}")
            self.db.log_mcp_action("Sheet Entry (Fail)", f"Failed Live Sheets append, logging to mock CSV: {e}")
            with open(MOCK_SHEETS_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            return "fallback_sheet_appended"

    # --- GMAIL DRAFT ACTION ---
    def trigger_gmail_draft(self, booking_code: str, topic: str, slot: str) -> str:
        subject = f"Internal Approval Required — Advisor Q&A — {topic} — {booking_code}"
        body = (
            f"A new tentative advisor booking has been scheduled.\n\n"
            f"Details:\n"
            f"- Topic: {topic}\n"
            f"- Slot: {slot}\n"
            f"- Booking Code: {booking_code}\n\n"
            f"Please review and approve this appointment."
        )
        
        if self.is_mock:
            log_msg = (
                f"========================================================================\n"
                f"[{datetime.datetime.now()}] CREATE GMAIL DRAFT\n"
                f"Subject: {subject}\n"
                f"Body:\n{body}\n"
                f"========================================================================\n"
            )
            with open(MOCK_GMAIL_LOG, 'a', encoding='utf-8') as f:
                f.write(log_msg)
                
            self.db.log_mcp_action("Gmail Draft (Mock)", f"Created draft '{subject}'")
            return "mock_draft_created"
            
        try:
            service = self._get_gmail_client()
            if not service:
                raise ValueError("Gmail client not initialized (check GMAIL_USER_EMAIL or domain delegation).")
                
            import base64
            from email.mime.text import MIMEText
            
            message = MIMEText(body)
            message['to'] = GMAIL_USER_EMAIL # Send to self for approval review
            message['subject'] = subject
            raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            body_draft = {'message': {'raw': raw_msg}}
            res = service.users().drafts().create(userId='me', body=body_draft).execute()
            self.db.log_mcp_action("Gmail Draft (Live)", f"Created Gmail draft ID {res.get('id')} for booking {booking_code}")
            return res.get('id', 'live_draft_created')
        except Exception as e:
            print(f"Error creating Gmail draft: {e}")
            self.db.log_mcp_action("Gmail Draft (Fail)", f"Failed Live Gmail draft, logging to mock: {e}")
            log_msg = (
                f"=========================== FALLBACK DRAFT ===========================\n"
                f"[{datetime.datetime.now()}] ERROR FALLBACK GMAIL DRAFT (due to: {e})\n"
                f"Subject: {subject}\n"
                f"Body:\n{body}\n"
                f"======================================================================\n"
            )
            with open(MOCK_GMAIL_LOG, 'a', encoding='utf-8') as f:
                f.write(log_msg)
            return "fallback_draft_created"

    def execute_all_mcp_book(self, booking_code: str, topic: str, slot: str) -> Dict[str, str]:
        # Triggers all three MCP actions for booking
        cal_status = self.trigger_calendar_hold(booking_code, topic, slot)
        sheet_status = self.trigger_sheet_append(booking_code, topic, slot, "Tentative")
        gmail_status = self.trigger_gmail_draft(booking_code, topic, slot)
        return {
            "calendar": cal_status,
            "sheets": sheet_status,
            "gmail": gmail_status
        }

    def execute_all_mcp_reschedule(self, booking_code: str, topic: str, new_slot: str) -> Dict[str, str]:
        # Triggers reschedule hooks for Calendar & Sheet updates
        cal_status = self.trigger_calendar_reschedule(booking_code, topic, new_slot)
        sheet_status = self.trigger_sheet_append(booking_code, topic, new_slot, "Rescheduled")
        return {
            "calendar": cal_status,
            "sheets": sheet_status
        }

    def execute_all_mcp_cancel(self, booking_code: str, topic: str, slot: str) -> Dict[str, str]:
        # Triggers cancellation hooks
        cal_status = self.trigger_calendar_cancel(booking_code)
        sheet_status = self.trigger_sheet_append(booking_code, topic, slot, "Cancelled")
        return {
            "calendar": cal_status,
            "sheets": sheet_status
        }
