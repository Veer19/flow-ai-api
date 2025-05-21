from app.utils.code_executer import execute_pandas_code
from app.utils.blob_storage import get_dataframes_dict
from app.utils.json_encoders import ensure_json_serializable
from app.agent.config import AgentState

async def execute_code_node(state: AgentState) -> AgentState:
    """Execute the generated code and update state"""
    dataframes = await get_dataframes_dict(state.required_datasets)
    result = execute_pandas_code(state.generated_code, dataframes, 'analyze_data')
    state.execution_result = ensure_json_serializable(result)
    return state