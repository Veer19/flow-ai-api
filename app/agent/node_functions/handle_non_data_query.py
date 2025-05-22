from typing import Dict, Any, List
from app.utils.prompt_engine import render_prompt
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.models.agent_response import FormatResponseLLMResponse


async def handle_non_data_query_llm(query: str, past_messages: List[Dict[str, Any]]) -> str:
    user_prompt = render_prompt("handle_non_data_query/user.jinja", {
        "query": query,
        "past_messages": past_messages
    })
    system_prompt = render_prompt("handle_non_data_query/system.jinja")
    response: FormatResponseLLMResponse = await ainvoke_llm(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        profile="analyze",
        response_model=FormatResponseLLMResponse
    )
    return response


async def handle_non_data_query(state: AgentState) -> AgentState:
    result: FormatResponseLLMResponse = await handle_non_data_query_llm(state.current_query, state.past_messages)
    state.formatted_response = result
    return state
