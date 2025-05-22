from typing import Dict, Any, List
from app.utils.prompt_engine import render_prompt
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.models.data_sources import DataSource
from app.models.visuals import VisualType, VisualConceptsLLMResponse, VisualConcept


async def create_visual_concept_llm(query: str, datasets: List[DataSource], past_messages: List[Dict[str, Any]]) -> VisualConcept:
    system_prompt = render_prompt("generate_visual_concept/system.jinja")
    user_prompt = render_prompt("generate_visual_concept/user.jinja", {
        "query": query,
        "past_messages": past_messages,
        "datasets": [d.to_llm_dict() for d in datasets],
        "visual_types": [visual_type.value for visual_type in VisualType]
    })
    response: VisualConceptsLLMResponse = await ainvoke_llm(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        profile="analyze",
        response_model=VisualConceptsLLMResponse
    )
    return response.visual_concepts[0]


async def create_visual_concept(state: AgentState) -> Dict[str, Any]:
    result: VisualConcept = await create_visual_concept_llm(state.current_query, state.datasets, state.past_messages)
    state.analysis = result
    state.required_datasets = [d for d in state.datasets if str(
        d.id) in result.required_dataset_ids]
    return state
