# servicenow_client.py

import os
import uuid
from typing import Dict, Any

# Real ServiceNow would use requests and ENV vars for URL & auth.
# Here we just simulate a ticket and return an ID.

def create_servicenow_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a SericeNow incident creation.
    Replace this with real REST call:
    - url = os.getenv("SNOW_URL")
    - user, pwd or token from env
    - requests.post(...)
    """
    incident_id = f"INC{uuid.uuid4().hex[:8].upper()}"
    return {
        "incident_id": incident_id,
        "short_description": payload.get("short_description"),
        "description": payload.get("description"),
        "priority": payload.get("priority", "3"),
        "state": "New",
    }