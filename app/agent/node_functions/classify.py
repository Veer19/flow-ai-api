from typing import Dict, Any, List
from app.agent.prompt_engine import render_prompt
from app.agent.utils import extract_json_from_llm_response
from app.agent.config import AgentState
from app.agent.llm_provider import ainvoke_llm

async def classify_query_llm(query: str, past_messages: List[Dict[str, Any]]  ) -> Dict[str, Any]:
    user_prompt = render_prompt("classify_query/user.jinja", {
        "query": query,
        "past_messages": past_messages
    })
    system_prompt = render_prompt("classify_query/system.jinja")
    response_content = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="analyze"
    )
    print("CLASSIFY QUERY RESPONSE")
    print(response_content)
    return extract_json_from_llm_response(response_content)

async def classify_query(state: AgentState) -> Dict[str, Any]:
    try:
        result = await classify_query_llm(state.current_query, state.past_messages)
        state.is_data_query = result.get("intent", "unknown") == "data_question"
        return state
    except Exception as e:
        print(f"[classify_query] Error: {str(e)}")
        raise e
