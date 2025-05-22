from typing import Dict, Any
from app.services.visuals import generate_visual_sample_data
from app.agent.config import AgentState
from app.models.visuals import VisualData


async def generate_demo_visual_data(state: AgentState) -> Dict[str, Any]:
    result: VisualData = await generate_visual_sample_data(state.analysis, state.required_datasets, [])
    state.visual_data = {"result": result}
    state.execution_result = {"result": result}
    return state
