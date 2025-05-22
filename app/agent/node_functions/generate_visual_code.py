from typing import Dict, Any
from app.services.visuals import generate_visual_python_code
from app.agent.config import AgentState
from app.models.visuals import VisualData


async def generate_visual_code(state: AgentState) -> Dict[str, Any]:
    print("Generating visual code")
    print(state)
    result: VisualData = await generate_visual_python_code(
        data_sources=state.required_datasets,
        relationships=[],
        visual_concept=state.analysis,
        visual_sample_data=state.visual_data
    )
    state.generated_code = result
    return state
