from langgraph.graph import END, StateGraph

from app.agents.nodes.example_node import (
    answer_with_sources_node,
    classify_intent_node,
    finalize_response_node,
    general_answer_node,
    handle_no_source_node,
    handle_ticket_intent_node,
    hr_metrics_node,
    input_safeguard_node,
    is_blocked,
    output_safeguard_node,
    retrieve_policy_node,
    route_intent,
    route_retrieval,
    should_continue_active_ticket_flow,
    topic_scope_node,
)
from app.agents.state import AgentState


def route_after_input_safeguard(state: AgentState) -> str:
    decision = state.get("input_safeguard") or {}
    if decision.get("blocked") is True or is_blocked(state):
        return "output_safeguard"
    if should_continue_active_ticket_flow(state):
        return "handle_ticket_intent"
    if decision.get("requires_handoff") is True and decision.get("reason_code") == "workplace_misconduct":
        return "handle_ticket_intent"
    return "topic_scope"


def route_after_topic_scope(state: AgentState) -> str:
    if is_blocked(state):
        return "output_safeguard"
    return "classify_intent"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("input_safeguard", input_safeguard_node)
    graph.add_node("topic_scope", topic_scope_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("hr_metrics", hr_metrics_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("answer_with_sources", answer_with_sources_node)
    graph.add_node("handle_no_source", handle_no_source_node)
    graph.add_node("handle_ticket_intent", handle_ticket_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("output_safeguard", output_safeguard_node)
    graph.add_node("finalize_response", finalize_response_node)

    graph.set_entry_point("input_safeguard")
    graph.add_conditional_edges(
        "input_safeguard",
        route_after_input_safeguard,
        {
            "topic_scope": "topic_scope",
            "handle_ticket_intent": "handle_ticket_intent",
            "output_safeguard": "output_safeguard",
        },
    )
    graph.add_conditional_edges(
        "topic_scope",
        route_after_topic_scope,
        {
            "classify_intent": "classify_intent",
            "output_safeguard": "output_safeguard",
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
        graph.add_edge(node, "output_safeguard")
    graph.add_edge("output_safeguard", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


agent = build_graph()
