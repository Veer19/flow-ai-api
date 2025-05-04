from typing import Dict, Any
from app.agent.config import AgentState
from app.agent.llm_provider import ainvoke_llm
from app.agent.prompt_engine import render_prompt
from app.agent.utils import prepare_datasets_for_prompt, extract_code_block

async def generate_code_llm(query: str, operations: list, datasets: list) -> str:
    user_prompt = render_prompt("generate_code/user.jinja", {
        "query": query,
        "operations": operations,
        "datasets": prepare_datasets_for_prompt(datasets)
    })
    system_prompt = render_prompt("generate_code/system.jinja")
    result = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="code"
    )
    print("GENERATE CODE RESULT")
    print(result)
    return result

async def generate_code(state: AgentState) -> Dict[str, Any]:
    try:
        code = await generate_code_llm(
            state.analysis['analysis_description'] if state.analysis else state.current_query, 
            state.analysis['suggested_operations'] if state.analysis else [], 
            state.required_datasets if state.required_datasets else state.datasets
        )
        state.generated_code = code
        return state
    except Exception as e:
        print(f"[generate_code] Error: {str(e)}")
        raise e
