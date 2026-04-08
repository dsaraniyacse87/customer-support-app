# eval_dataset.py

from typing import List, Dict, Any

# Minimal schema:
# - user_message: str
# - expected_answer_hint: str (short decription of what a good answer should contain)
# - should_create_ticket: bool (ground truth for ticket decision)
# - notes: optional

def get_eval_cases() -> List[Dict[str, Any]]:
    # In a real implementation, this could load from a JSON file, database, or other source
    return [
        {
            "id": "login_1",
            "user_message": "I can't login into the customer portal, it says 'invalid token' every time.",
            "expected_hints_answers": "Explain how to clear browser cache and cookies, and provide a link to the portal. Try to reset login, and mention token inquiry.",
            "should_create_ticket": False,
            "notes": "Simple FAQ/troubleshooting, should not create ticket by default."
        },
        {
            "id": "payment_1",
            "user_message": "My credit card payment failed twice today, and I see no confirmation email. Can you check?",
            "expected_hints_answers": "Explain common payment failure reasons and checking transaction history. Might need ticket.",
            "should_create_ticket": True,
            "notes": "This is a billing issue that requires further investigation."
        },
        {
            "id": "outage_1",
            "user_message": "Our entire team cannot access the VPN and all services are down. This is urgent!",
            "expected_hints_answers": "Acknowledge the outage, suggest basic checks, escalate and immediately create a ticket for urgent handling.",
            "should_create_ticket": True,
            "notes": "Urgent outage scenario, should always create ticket with high priority."
        },
        # Add more cases as needed for evaluation
    ]