# app.py (additions)

import os
import streamlit as st

from graph import build_graph, SupportState
from evaluation_metric import run_eval    # NEW

os.environ.setdefault("OPENAI_API_KEY", "your_api_key_here")

st.set_page_config(page_title="Customer Support Agent", page_icon="🤖")

tab_run, tab_eval = st.tabs(["Run Agent", "Evaluate Metrics"])

with tab_run:
    st.title("Customer Support Agent (Run)")

    st.markdown(
        """
        This demo uses a **multi-agent LanGraph workflow**:
        1. **Intake Agent**: classifies the request (simple FAQ, troubleshooting, billing, urgent outage)
        2. **Clarification Agent**: detects if the request is too vague and generates a targeted clarification question if needed
        3. **RAG Answering Agent**: retrieves relevant KB docs and generates a response using RAG
        4. **Summary Agent**: creates a concise, ticket-style summary of the issues and suggested solution
        5. **Routing Agent**: recommentds the best assignment group and category/subcategory for the ticket
        6. **ServiceNow Agent**: (mock) creates a ServiceNow style incident using the summary and routing info
        """
    )
    
    user_message = st.text_area(
        "Describe ur issue:",
        placeholder="Example: I'm unable to log in to the portal and see an 'invalid toke' error.",
        height=150,
        )
    

    create_ticket_flag = st.checkbox(
        "Ask the agent to create a ServiceNow ticket if needed",
        value=True,
    )

    if "graph" not in st.session_state:
        st.session_state["graph_app"] = build_graph()

    if st.button("Run Support Agent", key="run_agent"):
        if not user_message.strip():
            st.warning("Please enter your issue first.")
        else:
            with st.spinner("Running mutli-agent workflow..."):
                initial_state: SupportState = {
                    "user_message": user_message,
                    "create_ticket": create_ticket_flag,
                }
                app_graph = st.session_state["graph_app"]
                final_state = app_graph.invoke(initial_state)

            st.subheader("RAG Answer")
            st.write(final_state.get("rag_answer", "No answer generated."))

            st.subheader("Summary for Ticket / Suport Engineer")
            st.write(final_state.get("summary", "No summary generated."))

            st.subheader("Clarification (if any)")
            if final_state.get("clarification_needed"):
                st.warning(
                    f"Clarification question generated: "
                    f"{final_state.get('clarification_question', '')}"
                )
            else:
                st.info("No clarification needed for this query.")

            st.subheader("Routing Recommendation")
            st.write(
                f"Assignment Group: "
                f"**{final_state.get('assignment_group', 'N/A')}** "
            )
            st.write(
                f"Category/Subcategory: "
                f"**{final_state.get('category', 'N/A')} / "
                f"{final_state.get('subcategory', 'N/A')}**"
            )

            st.subheader("ServiceNow Ticket")
            ticket = final_state.get("ticket_response", {})
            if ticket and ticket.get("incident_id"):
                st.success(
                    f"Ticket created successfully!: **{ticket['incident_id']}** "
                    f"(Priority: {ticket.get('priority', '3')})"
                )
                st.code(ticket.get("description", ""), language="markdown")
            else:
                st.info("No ticket created for this issue.")

            st.subheader("RAG Sources")
            st.code(final_state.get("rag_sources", "No sources retrieved."), language="text")

            st.subheader("Debug State (optional)")
            st.json(final_state)

with tab_eval:
    st.title("Evaluation Metrics")

    st.markdown(
        """
This tab runs a small evaluation suite over sythetic test cases and reports:

- **Average Answer Quality (1-5)**: based on relevance, accuracy, and completeness vs expected hints/answers
- **Average Summary Quality (1-5)**: how well the generated summary captures the key issue and solution steps
- **Ticket Decision Accuracy**: fraction of cases where ticket/no-ticket is correct
- **Routing Accuracy**: fraction of cases where the recommended assignment group and category/subcategory are correct"""
    )

    if st.button("Run Evaluation Suite", key="run_eval_suite"):
        with st.spinner("Running evaluation over all test cases (this uses the LLM as a judge)..."):
            eval_results = run_eval()  # This function should return a dictionary of evaluation results

        agg = eval_results["aggregates"]
        per_case = eval_results["per_case"]

        st.subheader("Aggregate Metrics")
        st.metric("Average Answer Score (1-5)", f"{agg['avg_answer_score_1to5']:.2f}")
        st.metric("Average Summary Score (1-5)", f"{agg['avg_summary_score_1to5']:.2f}")
        st.metric("Ticket Decision Accuracy", f"{agg['ticket_accuracy']*100:.1f}%")
        st.metric("Routing Accuracy", f"{agg['routing_accuracy']*100:.1f}%")
        st.write(f"Number of cases: {agg['num_cases']}")

        st.subheader("Per-Case Details")
        for c in per_case:
            with st.expander(f"Case: {c['id']}"):
                st.write("**User Message:**")
                st.write(c["user_message"])
                st.write("**Expected Hints/Answers:**")
                st.write(c["expected_hints_answers"])
                st.write("**Notes:**")
                st.write(c["notes"])

                st.write("**Model answer:**")
                st.write(c["answer"])

                st.write("**Model summary:**")
                st.write(c["summary"])

                st.write(
                    f"**Answer Score (1-5):** {c['answer_score']:.1f} / 5 | "
                    f"**Summary Score (1-5):** {c['summary_score']:.1f} / 5 "
                )
                st.write(
                    f"**Ticket Decision Correct?** predicted: {c['pred_should_ticket']} "
                    f"| true: {c['true_should_ticket']} | "
                    f"correct: {c['ticket_decision_correct']}"
                    # f"**Routing Correct?** predicted: {c['predicted_routing']} | "
                    # f"true: {c['true_routing']} | "
                    # f"correct: {c['routing_correct']}"
                )
                st.write("**Routing Predictions:**")
                st.write(
                    f"Assignment Group: predicted: {c.get('pred_assignment_group', '')} | "
                    f"true: {c.get('true_assignment_group', '')} | "
                    f"correct: {c.get('routing_group_correct', '')}"
                )
                st.write(
                    f"Category: predicted: {c.get('pred_category', '')} | "
                    f"true: {c.get('true_category', '')} | "
                    f"correct: {c.get('routing_category_correct', '')}"
                )
                st.write(
                    f"Subcategory: predicted: {c.get('pred_subcategory', '')} | "
                    f"true: {c.get('true_subcategory', '')} | "
                    f"correct: {c.get('routing_subcategory_correct', '')}"
                )
