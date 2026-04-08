# graph.py 
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from rag import get_rag_chain
from servicenow_client import create_servicenow_ticket

# ---- Shared state type ----

class SupportState(TypedDict, total=False):
    user_message: str
    intent: str
    rag_answer: str
    rag_sources: str
    summary: str
    should_create_ticket: bool
    ticket_payload: Dict[str, Any]
    ticket_response: Dict[str, Any]

    # NEW: Clarification agent fields
    clarification_needed: bool
    clarification_question: str
    clarification_message: str # merged user_message + clarification

    # NEW: Routing /escalation agent fields
    assignment_group: str
    category: str
    subcategory: str

# ---- Global components ----

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_rag_chain = get_rag_chain()

# ---- Agent 1: Customer Question / Intent Agent ----

def intake_agent(state: SupportState) -> SupportState:
    """"Classify the user's intent and decide if ticket creation is needed later."""
    user_message = state["user_message"]

    prompt = f"""
        You are an intent classifier for IT/Customer Support.
        user_message: {user_message}

        Classify into one of: ["simple_faq", "troubleshooting", "billing", "urgent_outage"]
        Also say whether we should eventually create a ServiceNow ticket: true/false

        Respond as valid JSON: 
        {{
            "intent": "...",
            "should_create_ticket": true/false
        }}
    """
    response = _llm.invoke(prompt)
    import json
    try:
        parsed = json.loads(response.content)
        state["intent"] = parsed.get("intent", "simple_faq")
        state["should_create_ticket"] = bool(parsed.get("should_create_ticket", False))
    except Exception:
        state["intent"] = "simple_faq"
        state["should_create_ticket"] = False

    return state
    
# ---- Agent: Clarification Agent ----

def clarification_agent(state: SupportState) -> SupportState:
    """
    Decide whether clarification is is needed and , if so, generate a targeted question.

    For simplicity, we dont loop with the user here;
    we just record the question and keep using the original message.
    In a real app, you'd send this back to UI and wait for answer.
    """ 
    user_message = state["user_message"]
    intent = state.get("intent", "simple_faq")

    prompt = f"""
You are a customer support triage assistant.

User message: {user_message}

Intent (classified earlier): {intent}

1. Decide if this message is too vague or ambiguous to answer well.
2. If ambiguous, propose ONE shot, specific clarification question.
3. If not, say clarification is needed.

Respond as JSON:
{{
    "clarification_needed": true/false,
    "clarification_question": "..." # empty string if not needed
}}
    """
    response = _llm.invoke(prompt)

    import json
    clarification_needed = False
    clarification_question = ""

    try:
        parsed = json.loads(response.content)
        clarification_needed = bool(parsed.get("clarification_needed", False))
        clarification_question = parsed.get("clarification_question", "").strip()
    except Exception:
        state["clarification_needed"] = False
        state["clarification_question"] = ""

    state["clarification_needed"] = clarification_needed
    state["clarification_question"] = clarification_question or ""
    # For now, we dont change the input; in a full UX flow you'd add user replies:
    state["clarification_message"] = user_message

    return state

# ---- Agent 2: RAG Answering Agent ----

def rag_agent(state: SupportState) -> SupportState:
    """Use RAG over KB to answer the question."""
    # Prefer clarified_message if set, otherwise fallback to original.
    user_message = state.get("clarification_message") or state["user_message"]

    result = _rag_chain(
        {
            "query": user_message
        }
    )
    answer = result["result"]
    sources = result.get("source_documents", [])

    src_strs = []
    for i, d in enumerate(sources):
        src_strs.append(f"[{i+1}] {d.metadata.get('source', 'unknown')}")

    state["rag_answer"] = answer
    state["rag_sources"] = "\n".join(src_strs)
    return state

# ---- Agent 3: Summary Agent ----

def summary_agent(state: SupportState) -> SupportState:
    """Summarize the conversation + RAG answer into a short ticket-style  summary"""
    user_message = state["user_message"]
    rag_answer = state["rag_answer"]

    prompt = f"""
You are a support engineer. Write a concise summary suitable for a ServiceNow incident.

Include:
- Problem description in 1-2 sentences
- Key context from the RAG answer (if any)
- Any workaround or solution already suggested 

User message: {user_message}

RAG Answer: {rag_answer}

Respond with 3-5 sentences, plain text.
"""
    response = _llm.invoke(prompt)
    state["summary"] = response.content.strip()
    return state

# ---- Agent: Routing Agent ----

def routing_agent(state: SupportState) -> SupportState:
    """
    Recommend which team/queue should own the ticket:
    - assignment_group (e.g. Network, App Support, Billing)
    - category/subcategory (for ServiceNow-like systems)
    """

    user_message = state["user_message"]
    intent = state.get("intent", "simple_faq")
    summary = state.get("summary", "")

    prompt = f"""
You are a service desk routing assistant for an IT/Customer support organization.

Decide the best routing for this case based on:
- User message
- Intent
- Summary

Routing schema:
- assignment_group: one of ["Network Operation", "Application Support", "Billing Support", "Identity & Access", "General Support"]
- category: a short lable like "network", "application", "billing", "access", "general"
- subcategory: more specific, like "vpn", "portal login", "payment failure", "outage", "password reset", etc.

User message: {user_message}

Intent: {intent}

Summary: {summary}

Respond as JSON:
{{
    "assignment_group": "...",
    "category": "...",
    "subcategory": "..."
}}
    """
    response = _llm.invoke(prompt)

    import json
    assignment_group = "General Support"
    category = "other"
    subcategory = "Unspecified"

    try:
        parsed = json.loads(response.content)
        assignment_group = parsed.get("assignment_group") or assignment_group
        category = parsed.get("category") or category
        subcategory = parsed.get("subcategory") or subcategory
    except Exception:
        pass

        state["assignment_group"] = assignment_group
        state["category"] = category
        state["subcategory"] = subcategory

    return state

# ---- Agent 4: ServiceNow Ticket Generation Agent ----

def ticket_agent(state: SupportState) -> SupportState:
    """Create a ticket if requested by user/intent. """
    if not state.get("should_create_ticket", False):
        state["ticket_payload"] = {}
        state["ticket_response"] = {}
        return state  
    
    user_message = state["user_message"]
    summary = state.get("summary", "")

    # Simple priority logic
    priority = "2" if state.get("intent") == "urgent_outage" else "3"

    assignment_group = state.get("assignment_group", "General Support")
    category = state.get("category", "other")
    subcategory = state.get("subcategory", "Unspecified")

    payload = {
        "short_description:": f"suport request: {state.get('intent', 'general')}",
        "description": f"user message: {user_message}\n\nSummary: {summary}",
        "priority": priority,
        "assignment_group": assignment_group,
        "category": category,
        "subcategory": subcategory,
    }
    state["ticket_payload"] = payload

    ticket = create_servicenow_ticket(payload)
    state["ticket_response"] = ticket
    return state

# ---- Build LangGraph ----

def build_graph():
    workflow = StateGraph(SupportState)

    workflow.add_node("intake_agent", intake_agent)
    workflow.add_node("clarification_agent", clarification_agent) # NEW
    workflow.add_node("rag_agent", rag_agent)
    workflow.add_node("summary_agent", summary_agent)
    workflow.add_node("routing_agent", routing_agent) # NEW
    workflow.add_node("ticket_agent", ticket_agent)

    workflow.set_entry_point("intake_agent")
    workflow.add_edge("intake_agent", "clarification_agent") # NEW
    workflow.add_edge("clarification_agent", "rag_agent")   # NEW
    workflow.add_edge("rag_agent", "summary_agent")        
    workflow.add_edge("summary_agent", "routing_agent")     # NEW
    workflow.add_edge("routing_agent", "ticket_agent")      # NEW
    workflow.add_edge("ticket_agent", END)                 

    app = workflow.compile()
    return app

    