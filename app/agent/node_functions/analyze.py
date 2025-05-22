from typing import Dict, Any, List
from app.utils.prompt_engine import render_prompt
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.models.agent_response import AnalyzeQuestionLLMResponse
from app.models.data_sources import DataSource


async def analyze_intent_llm(query: str, datasets: List[DataSource], past_messages: List[Dict[str, Any]]) -> AnalyzeQuestionLLMResponse:
    user_prompt = render_prompt("analyze_intent/user.jinja", {
        "query": query,
        "datasets": [d.to_llm_dict() for d in datasets],
        "past_messages": past_messages
    })
    system_prompt = render_prompt("analyze_intent/system.jinja")
    result: AnalyzeQuestionLLMResponse = await ainvoke_llm(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        profile="analyze",
        response_model=AnalyzeQuestionLLMResponse
    )
    return result


async def analyze_intent(state: AgentState) -> Dict[str, Any]:
    try:
        result: AnalyzeQuestionLLMResponse = await analyze_intent_llm(state.current_query, state.datasets, state.past_messages)
        state.analysis = result
        state.required_datasets = [d for d in state.datasets if str(
            d.id) in result.required_dataset_ids]
        return state
    except Exception as e:
        raise e
