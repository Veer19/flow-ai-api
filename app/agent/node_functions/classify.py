from typing import Dict, Any, List
from app.utils.prompt_engine import render_prompt
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.models.agent_response import ClassifyQueryLLMResponse


async def classify_query_llm(query: str, past_messages: List[Dict[str, Any]]  ) -> ClassifyQueryLLMResponse:
    user_prompt = render_prompt("classify_query/user.jinja", {
        "query": query,
        "past_messages": past_messages
    })
    system_prompt = render_prompt("classify_query/system.jinja")
    response:ClassifyQueryLLMResponse = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="analyze",
        response_model=ClassifyQueryLLMResponse
    )
    print("CLASSIFY QUERY RESPONSE")
    print(response)
    return response

async def classify_query(state: AgentState) -> Dict[str, Any]:
    try:
        result:ClassifyQueryLLMResponse = await classify_query_llm(state.current_query, state.past_messages)
        state.intent = result.intent
        return state
    except Exception as e:
        print(f"[classify_query] Error: {str(e)}")
        raise e
