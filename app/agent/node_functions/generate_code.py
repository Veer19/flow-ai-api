from typing import Dict, Any
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.utils.prompt_engine import render_prompt
from app.models.data_sources import DataSource


async def generate_code_llm(query: str, operations: list, datasets: list[DataSource]) -> str:
    user_prompt = render_prompt("generate_code/user.jinja", {
        "query": query,
        "operations": operations,
        "datasets": [d.to_llm_dict() for d in datasets]
    })
    system_prompt = render_prompt("generate_code/system.jinja")
    result = await ainvoke_llm(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        profile="code"
    )
    return result.content


async def generate_code(state: AgentState) -> Dict[str, Any]:
    code = await generate_code_llm(
        state.analysis.analysis_description if state.analysis else state.current_query,
        state.analysis.suggested_operations if state.analysis else [],
        state.required_datasets if state.required_datasets else state.datasets
    )
    state.generated_code = code
    return state
