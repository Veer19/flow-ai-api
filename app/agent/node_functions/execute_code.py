from app.agent.utils import execute_pandas_code
from app.agent.config import AgentState
from app.utils.json_encoders import ensure_json_serializable

async def execute_code_node(state: AgentState) -> AgentState:
    """Execute the generated code and update state"""
    result = await execute_pandas_code(state.required_datasets, state.generated_code)
    state.execution_result = ensure_json_serializable(result)
    return state