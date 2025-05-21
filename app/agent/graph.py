from langgraph.graph import StateGraph, END
from app.agent.config import AgentState
from app.agent.node_functions.classify import classify_query
from app.agent.node_functions.analyze import analyze_intent
from app.agent.node_functions.generate_code import generate_code
from app.agent.node_functions.format import format_response
from app.agent.node_functions.execute_code import execute_code_node
from app.agent.node_functions.handle_non_data_query import handle_non_data_query
from app.models.agent_response import Intent


def create_graph() -> StateGraph:
    """Create the agent workflow graph"""
    
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("classify_query", classify_query)
    workflow.add_node("analyze_intent", analyze_intent)
    workflow.add_node("generate_code", generate_code)
    workflow.add_node("execute_code", execute_code_node)
    workflow.add_node("format_response", format_response)
    workflow.add_node("handle_non_data_query", handle_non_data_query)

    # Edges
    workflow.set_entry_point("classify_query")
    workflow.add_conditional_edges(
        "classify_query",
        lambda state: "analyze_intent" if state.intent == Intent.DATA_QUESTION else "handle_non_data_query"
    )
    
    workflow.add_edge("analyze_intent", "generate_code")
    workflow.add_edge("generate_code", "execute_code")
    workflow.add_edge("execute_code", "format_response")
    workflow.add_edge("format_response", END)
    workflow.add_edge("handle_non_data_query", END)

    compiled_graph = workflow.compile()
    return compiled_graph
