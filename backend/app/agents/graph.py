from langgraph.graph import END, StateGraph

from app.agents.nodes.example_node import (
    answer_with_sources_node,
    classify_intent_node,
    finalize_response_node,
    general_answer_node,
    guardrail_node,
    handle_no_source_node,
    handle_ticket_intent_node,
    hr_metrics_node,
    is_blocked,
    retrieve_policy_node,
    route_intent,
    route_retrieval,
)
from app.agents.state import AgentState


def route_after_guardrail(state: AgentState) -> str:
    if is_blocked(state):
        return "finalize_response"
    return "classify_intent"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("hr_metrics", hr_metrics_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("answer_with_sources", answer_with_sources_node)
    graph.add_node("handle_no_source", handle_no_source_node)
    graph.add_node("handle_ticket_intent", handle_ticket_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("finalize_response", finalize_response_node)

    graph.set_entry_point("guardrail")
    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "classify_intent": "classify_intent",
            "finalize_response": "finalize_response",
        },
    )
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "hr_metric": "hr_metrics",
            "ticket_create": "handle_ticket_intent",
            "policy_question": "retrieve_policy",
            "general": "general_answer",
            "blocked": "finalize_response",
        },
    )
    graph.add_conditional_edges(
        "retrieve_policy",
        route_retrieval,
        {
            "answer_with_sources": "answer_with_sources",
            "handle_no_source": "handle_no_source",
            "general_answer": "general_answer",
        },
    )

    for node in (
        "hr_metrics",
        "answer_with_sources",
        "handle_no_source",
        "handle_ticket_intent",
        "general_answer",
    ):
        graph.add_edge(node, "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


agent = build_graph()
