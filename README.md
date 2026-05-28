# AI Voice Agent — Advisor Appointment Scheduler

This project is an AI Voice Agent built for the Bootcamp Challenge. It acts as a pre-booking assistant for a human financial advisor, allowing users to book tentative appointments without collecting any Personal Identifiable Information (PII) over the phone.

## Architecture

- **Voice UI**: Antigravity (Google AI Studio) / Retell AI
- **LLM**: GPT-4o-mini / Gemini 2.5 Flash
- **Backend API**: FastAPI (Python)
- **Deployment**: Render.com (Backend)
- **Integrations (MCP)**: Google Calendar (tentative holds), Google Sheets (logging), Gmail (drafting)

## Important Links

- **Live Voice Agent URL**: `[INSERT YOUR VOICE AGENT SHAREABLE LINK HERE]`
- **Backend API URL**: `[INSERT YOUR RENDER URL HERE]`

## Demo Scenarios

Please run the following 6 scenarios to test the agent's capabilities and compliance:

### Scenario 1 — Happy Path Booking
- **Action**: Ask to book a session for "SIP/Mandates" on Friday at 3 PM IST.
- **Expected**: Full conversational flow. The agent will offer backend slots, generate a booking code (e.g., `NL-XXXX`), and trigger the 3 MCP actions.

### Scenario 2 — Investment Advice Refusal (Compliance)
- **Action**: Ask: *"Which mutual fund should I invest in?"*
- **Expected**: The agent refuses to provide financial advice and directs you to SEBI/Investor resources.

### Scenario 3 — PII Interruption (Compliance)
- **Action**: Start reciting personal information: *"My account number is 123456..."*
- **Expected**: The agent interrupts immediately and stops you from sharing PII over the call.

### Scenario 4 — Waitlist
- **Action**: Ask for a slot on a day or time that has no availability (e.g. Wednesday).
- **Expected**: The agent offers to add you to the waitlist and confirms your waitlist status.

### Scenario 5 — Reschedule
- **Action**: Provide an existing booking code (e.g., the one from Scenario 1) and ask to reschedule to a new available slot.
- **Expected**: The agent updates the booking and MCP triggers update the backend systems.

### Scenario 6 — Cancel
- **Action**: Provide a booking code and ask to cancel the appointment.
- **Expected**: The agent confirms the cancellation and clears the hold.

---

*Note: The backend API runs on a free tier which spins down after inactivity. If the voice agent seems unresponsive initially, wait ~30-50 seconds for the backend to wake up from a cold start.*
