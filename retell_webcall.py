"""
retell_webcall.py
-----------------
Creates a Retell AI web call link so you can test
the voice agent directly in your browser.

Usage:
    python retell_webcall.py
"""

import json
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv

load_dotenv()

RETELL_API_KEY = os.getenv("RETELL_API_KEY", "key_f35e83f971767ab3e7834a8d86b7")
RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID", "")

def create_web_call(agent_id: str) -> dict:
    payload = json.dumps({"agent_id": agent_id}).encode()
    req = urllib.request.Request(
        "https://api.retellai.com/v2/create-web-call",
        data=payload,
        headers={
            "Authorization": f"Bearer {RETELL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} error:")
        print(e.read().decode())
        return {}

def main():
    if not RETELL_AGENT_ID:
        print("ERROR: RETELL_AGENT_ID not found in .env")
        print("   Please run: python retell_setup.py <YOUR_NGROK_URL> first.")
        return

    print(f"Creating web call for Agent: {RETELL_AGENT_ID}")
    result = create_web_call(RETELL_AGENT_ID)

    if result:
        call_id = result.get("call_id", "N/A")
        access_token = result.get("access_token", "")
        print("\n" + "="*60)
        print("  [DONE] WEB CALL READY!")
        print("="*60)
        print(f"  Call ID      : {call_id}")
        print(f"  Access Token : {access_token[:40]}...")
        print()
        print("  Open this URL in your browser to speak with your agent:")
        print(f"  https://retell-widget.pages.dev/?access_token={access_token}")
        print("="*60)
    else:
        print("ERROR: Failed to create web call.")

if __name__ == "__main__":
    main()
