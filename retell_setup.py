"""
retell_setup.py
---------------
Creates a Retell AI Agent with:
  - System Prompt (pre-booking compliance rules)
  - 5 Function Tool schemas linked to your local backend (via ngrok)

Usage:
    python retell_setup.py <YOUR_NGROK_URL>

Example:
    python retell_setup.py https://a1b2-34-56.ngrok-free.app
"""

import sys
import json
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
RETELL_API_KEY = "key_f35e83f971767ab3e7834a8d86b7"
RETELL_BASE    = "https://api.retellai.com"

# ── Helpers ───────────────────────────────────────────────────────────────────
def retell_post(path: str, payload: dict) -> dict:
    body  = json.dumps(payload).encode()
    req   = urllib.request.Request(
        f"{RETELL_BASE}{path}",
        data    = body,
        headers = {
            "Authorization": f"Bearer {RETELL_API_KEY}",
            "Content-Type":  "application/json",
        },
        method = "POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"\nERROR: HTTP {e.code} error calling {path}")
        print(e.read().decode())
        sys.exit(1)


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
# Role and Objective
You are a compliant, helpful pre-booking voice assistant for a human financial advisor. Your sole objective is to help the caller secure a tentative consultation slot or join the waitlist.

# Strict Compliance & Verification Rules
1. DO NOT collect any Personal Identifiable Information (PII) on the call. This includes names, emails, phone numbers, addresses, account numbers, PAN, or Aadhaar.
2. If the user begins to state PII, politely interrupt: "Please do not share any personal details on this call. For security and compliance, you will receive a secure link at the end of the call to complete your registration details safely."
3. Clearly state the pre-booking disclaimer at the beginning of the call: "Hello! I am your pre-booking voice assistant. I can help you secure a tentative slot with a human advisor today. Please note that this call is for scheduling only, and we do not collect any personal details. A secure link will be sent to complete your registration later."
4. If a user asks financial or investment questions, reply: "I am only authorized to schedule your appointment. I cannot provide financial advice. Our human advisor will address all your questions during the consultation."

# Workflow Logic
1. Greet the caller and state the pre-booking disclaimer.
2. Ask for the topic of consultation. Validate against ONLY these approved topics:
   - KYC / Onboarding
   - SIP / Mandates
   - Statements / Tax Docs
   - Withdrawals & Timelines
   - Account Changes / Nominee
   If the topic is not in this list, say: "I'm sorry, that topic is outside our scope. I can schedule appointments for KYC / Onboarding, SIP / Mandates, Statements / Tax Docs, Withdrawals & Timelines, or Account Changes / Nominee. Which of these fits your query?"
3. Ask the caller for their preferred day. We offer slots on Monday, Tuesday, and Friday.
4. Call get_slots with the day and topic to check availability.
5. If slots are available, present them and ask which one they prefer.
   - Call book_appointment with the topic and chosen slot.
   - Read out the unique Booking Code and say: "Your slot has been tentatively held. Please note your booking code [CODE]. You will receive a secure link to enter your contact details. Thank you!"
6. If no slots are available, offer to join the waitlist. If they agree, call join_waitlist.
7. For rescheduling: ask for their booking code (NL-XXXX) and new preferred slot, then call reschedule_appointment.
8. For cancellation: ask for their booking code, then call cancel_appointment.
""".strip()


# ── Tool Definitions ──────────────────────────────────────────────────────────
def build_tools(base_url: str) -> list:
    base = base_url.rstrip("/")
    return [
        {
            "type": "custom",
            "name": "get_slots",
            "description": "Retrieves available appointment slots for a given day and approved topic.",
            "url": f"{base}/retell/get_slots",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Let me check what slots are available for you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "Day of the week e.g. Monday, Tuesday, Friday"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Approved consultation topic from the allowed list"
                    }
                },
                "required": ["day", "topic"]
            }
        },
        {
            "type": "custom",
            "name": "book_appointment",
            "description": "Books a tentative slot. Returns a unique booking code and secure link.",
            "url": f"{base}/retell/book_appointment",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Let me secure that slot for you now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Validated approved consultation topic"
                    },
                    "slot": {
                        "type": "string",
                        "description": "Slot string exactly as returned by get_slots e.g. Friday 3:00 PM IST"
                    }
                },
                "required": ["topic", "slot"]
            }
        },
        {
            "type": "custom",
            "name": "reschedule_appointment",
            "description": "Reschedules an existing booking code to a new slot.",
            "url": f"{base}/retell/reschedule_appointment",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Let me reschedule that for you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {
                        "type": "string",
                        "description": "The customer booking code e.g. NL-ABCD"
                    },
                    "new_slot": {
                        "type": "string",
                        "description": "New slot string in IST format"
                    }
                },
                "required": ["booking_code", "new_slot"]
            }
        },
        {
            "type": "custom",
            "name": "cancel_appointment",
            "description": "Cancels an active booking hold.",
            "url": f"{base}/retell/cancel_appointment",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Let me cancel that booking for you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {
                        "type": "string",
                        "description": "The customer booking code e.g. NL-ABCD"
                    }
                },
                "required": ["booking_code"]
            }
        },
        {
            "type": "custom",
            "name": "join_waitlist",
            "description": "Joins the waitlist for a topic when no slots are available.",
            "url": f"{base}/retell/join_waitlist",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Let me add you to the waitlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Approved consultation topic"
                    },
                    "preferred_day": {
                        "type": "string",
                        "description": "Preferred day of the week"
                    }
                },
                "required": ["topic", "preferred_day"]
            }
        }
    ]


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python retell_setup.py <YOUR_NGROK_URL>")
        print("Example: python retell_setup.py https://a1b2-34-56.ngrok-free.app")
        sys.exit(1)

    ngrok_url = sys.argv[1].rstrip("/")
    print(f"\n[*] Setting up Retell AI Agent...")
    print(f"   Backend URL : {ngrok_url}")

    # Step 1: Create Retell LLM
    print("\n[1/2] Creating Retell LLM with system prompt and tools...")
    llm_payload = {
        "model": "gpt-4o-mini",
        "general_prompt": SYSTEM_PROMPT,
        "tools": build_tools(ngrok_url),
        "begin_message": "Hello! I am your pre-booking voice assistant. I can help you secure a tentative slot with a human advisor today. This call is for scheduling only — no personal details will be collected. A secure link will be sent afterwards. How may I help you today?"
    }
    llm = retell_post("/create-retell-llm", llm_payload)
    llm_id = llm.get("llm_id")
    print(f"   [OK] LLM created  -> ID: {llm_id}")

    # Step 2: Create Agent
    print("\n[2/2] Creating Voice Agent...")
    agent_payload = {
        "response_engine": {
            "type": "retell-llm",
            "llm_id": llm_id
        },
        "agent_name": "Advisor Pre-Booking Assistant",
        "voice_id": "openai-Nova",
        "language": "en-US",
        "ambient_sound": "coffee-shop",
        "responsiveness": 1,
        "enable_backchannel": True,
        "backchannel_frequency": 0.5,
        "end_call_after_silence_ms": 15000,
        "max_call_duration_ms": 600000,
    }
    agent = retell_post("/create-agent", agent_payload)
    agent_id = agent.get("agent_id")
    print(f"   [OK] Agent created -> ID: {agent_id}")

    # Save IDs to .env for future reference
    with open(".env", "a", encoding="utf-8") as f:
        f.write(f"\n# Retell AI Configuration\n")
        f.write(f"RETELL_API_KEY={RETELL_API_KEY}\n")
        f.write(f"RETELL_LLM_ID={llm_id}\n")
        f.write(f"RETELL_AGENT_ID={agent_id}\n")

    print("\n" + "="*60)
    print("  [DONE] VOICE AGENT READY!")
    print("="*60)
    print(f"  Agent ID    : {agent_id}")
    print(f"  LLM ID      : {llm_id}")
    print(f"  Backend URL : {ngrok_url}")
    print()
    print("  To test via web call, run:")
    print(f"      python retell_webcall.py")
    print("="*60)


if __name__ == "__main__":
    main()
