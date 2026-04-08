# evaluation_metric.py

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from eval_dataset import get_eval_cases

from graph import build_graph, SupportState

_llm_judge = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def score_answer_quality(answer: str, expected_hint: str) -> float:
    """
    Return a score 1-5: relevance & completeness vs expected hint.
    """
    prompt = f"""
You are grading a support answer.

Expected good answer (hint, not exact text): {expected_hint}

Model answer: {answer}

Score from 1 to 5, where:
1 = completely irrelevant or incorrect, does not address the user's issue at all.
2 = somewhat relevant but mostly misses the point, or is very incomplete.
3 = partially relevant and somewhat addresses the issue, but is missing key information or has some inaccuracies.
4 = mostly relevant and addresses the issue well, but may be missing minor details or have small inaccuracies.
5 = highly relevant, accurate, and complete answer that fully addresses the user's issue and includes all key information.

Respond with ONLY the number score (1-5) and no other text.
"""
    response = _llm_judge.invoke(prompt)
    try:
        return float(response.content.strip())
    except Exception:
        return 0.0


def score_summary_quality(summary: str, user_message: str, answer: str) -> float:
    """
    Return a score 1-5: Does the summary capture the problem and solution context?
    """
    prompt = f"""
You are grading a support ticket summary.

User message: {user_message}

Support answer: {answer}

Summary to grade: {summary}

Score from 1 to 5, where:
1 = useless or misleading summary that does not capture the user's problem or the solution provided.
2 = poor summary that captures only a vague sense of the problem or solution, but is mostly unhelpful.
3 = partially captures the problem and solution but misses key details or is somewhat unclear.
4 = mostly captures the problem and solution, but may miss minor details or be slightly unclear.
5 = concise, accurate, and captures both problem and main solution/workaround clearly and completely.

Respond with ONLY the number score (1-5) and no other text.
"""
    response = _llm_judge.invoke(prompt)
    try:
        return float(response.content.strip())
    except Exception:
        return 0.0


def eval_ticket_decision(should_create_ticket: bool, model_decision: bool) -> int:
    """
    1 = correct decision, 0 = incorrect decision.
    """
    return int(should_create_ticket == model_decision)


def eval_routing(pred_group: str, true_group: str | None) -> int:
    if not true_group:
        return 1
    return int(pred_group.strip().lower() == true_group.strip().lower())


def eval_category(pred: str, true: str | None) -> int:
    if not true:
        return 1
    return int(pred.strip().lower() == true.strip().lower())


def eval_subcategory(pred: str, true: str | None) -> int:
    if not true:
        return 1
    return int(pred.strip().lower() == true.strip().lower())


class QualityPipeline:
    def __init__(self) -> None:
        self.graph_app = build_graph()
        self.eval_cases = get_eval_cases()

    def evaluate_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: SupportState = {
            "user_message": case["user_message"],
        }
        final_state = self.graph_app.invoke(initial_state)

        answer = final_state.get("rag_answer", "")
        summary = final_state.get("summary", "")
        pred_ticket_flag = final_state.get("should_create_ticket", False)
        pred_group = final_state.get("assignment_group", "")
        pred_category = final_state.get("category", "")
        pred_subcategory = final_state.get("subcategory", "")

        answer_score = score_answer_quality(answer, case["expected_hints_answers"])
        summary_score = score_summary_quality(summary, case["user_message"], answer)
        ticket_acc = eval_ticket_decision(case["should_create_ticket"], pred_ticket_flag)
        routing_group_acc = eval_routing(pred_group, case.get("expected_assignment_group"))
        routing_category_acc = eval_category(pred_category, case.get("expected_category"))
        routing_subcategory_acc = eval_subcategory(pred_subcategory, case.get("expected_subcategory"))

        return {
            "id": case["id"],
            "user_message": case["user_message"],
            "expected_hints_answers": case["expected_hints_answers"],
            "true_should_ticket": case["should_create_ticket"],
            "pred_should_ticket": pred_ticket_flag,
            "answer": answer,
            "summary": summary,
            "answer_score": answer_score,
            "summary_score": summary_score,
            "ticket_decision_correct": ticket_acc,
            "pred_assignment_group": pred_group,
            "true_assignment_group": case.get("expected_assignment_group"),
            "pred_category": pred_category,
            "true_category": case.get("expected_category"),
            "pred_subcategory": pred_subcategory,
            "true_subcategory": case.get("expected_subcategory"),
            "routing_group_correct": routing_group_acc,
            "routing_category_correct": routing_category_acc,
            "routing_subcategory_correct": routing_subcategory_acc,
            "notes": case.get("notes", ""),
        }

    def run(self) -> Dict[str, Any]:
        per_case: List[Dict[str, Any]] = []
        for case in self.eval_cases:
            per_case.append(self.evaluate_case(case))

        if per_case:
            avg_answer_score = sum(c["answer_score"] for c in per_case) / len(per_case)
            avg_summary_score = sum(c["summary_score"] for c in per_case) / len(per_case)
            ticket_accuracy = sum(c["ticket_decision_correct"] for c in per_case) / len(per_case)
            routing_accuracy = sum((c["routing_group_correct"] and c["routing_category_correct"] and c["routing_subcategory_correct"]) for c in per_case) / len(per_case)
            routing_group_accuracy = sum(c["routing_group_correct"] for c in per_case) / len(per_case)
            routing_category_accuracy = sum(c["routing_category_correct"] for c in per_case) / len(per_case)
            routing_subcategory_accuracy = sum(c["routing_subcategory_correct"] for c in per_case) / len(per_case)
        else:
            avg_answer_score = avg_summary_score = ticket_accuracy = 0.0
            routing_accuracy = routing_group_accuracy = routing_category_accuracy = routing_subcategory_accuracy = 0.0

        return {
            "per_case": per_case,
            "aggregates": {
                "avg_answer_score_1to5": avg_answer_score,
                "avg_summary_score_1to5": avg_summary_score,
                "ticket_accuracy": ticket_accuracy,
                "routing_accuracy": routing_accuracy,
                "routing_group_accuracy": routing_group_accuracy,
                "routing_category_accuracy": routing_category_accuracy,
                "routing_subcategory_accuracy": routing_subcategory_accuracy,
                "num_cases": len(per_case),
            },
        }


def run_eval() -> Dict[str, Any]:
    pipeline = QualityPipeline()
    return pipeline.run()
