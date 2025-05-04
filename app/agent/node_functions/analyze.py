from typing import Dict, Any, List
from app.agent.prompt_engine import render_prompt
from app.agent.utils import prepare_datasets_for_prompt, extract_json_from_llm_response
from app.agent.config import AgentState
from app.agent.llm_provider import ainvoke_llm

async def analyze_intent_llm(query: str, datasets: List[Dict[str, Any]], past_messages: List[Dict[str, Any]]  ) -> Dict[str, Any]:
    user_prompt = render_prompt("analyze_intent/user.jinja", {
        "query": query,
        "datasets": prepare_datasets_for_prompt(datasets),
        "past_messages": past_messages
    })
    system_prompt = render_prompt("analyze_intent/system.jinja")
    print("ANALYZE INTENT USER PROMPT")
    print(user_prompt)
    print("ANALYZE INTENT SYSTEM PROMPT")
    print(system_prompt)
    result = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="analyze"
    )
    print("ANALYZE INTENT RESULT")
    print(result)
    return extract_json_from_llm_response(result)

async def analyze_intent(state: AgentState) -> Dict[str, Any]:
    try:
        result = await analyze_intent_llm(state.current_query, state.datasets, state.past_messages)
        print("ANALYZE INTENT RESULT")
        print(result)
        state.analysis = result
        state.required_datasets = [d for d in state.datasets if d['_id'] in result['required_datasets']]
        return state
    except Exception as e:
        print(f"[analyze_intent] Error: {str(e)}")
        raise e
