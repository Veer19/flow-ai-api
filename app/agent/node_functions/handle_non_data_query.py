from typing import Dict, Any, List
from app.agent.prompt_engine import render_prompt
from app.agent.utils import prepare_datasets_for_prompt, extract_json_from_llm_response
from app.agent.config import AgentState
from app.agent.llm_provider import ainvoke_llm

async def handle_non_data_query_llm(query: str, past_messages: List[Dict[str, Any]]  ) -> Dict[str, Any]:
    user_prompt = render_prompt("handle_non_data_query/user.jinja", {
        "query": query,
        "past_messages": past_messages
    })
    system_prompt = render_prompt("handle_non_data_query/system.jinja")
    response_content = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="analyze"
    )
    print("HANDLE NON DATA QUERY RESPONSE")
    print(response_content)
    return response_content

async def handle_non_data_query(state: AgentState) -> Dict[str, Any]:
    try:
        result = await handle_non_data_query_llm(state.current_query, state.past_messages)
        state.formatted_response = {
            "type": "response",
            "message": result,
            "data": [],
            "show_data": False
        }
        return state
    except Exception as e:
        print(f"[handle_non_data_query] Error: {str(e)}")
        raise e
