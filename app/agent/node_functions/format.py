from typing import Dict, Any
from app.agent.config import AgentState
from app.agent.llm_provider import ainvoke_llm
from app.agent.prompt_engine import render_prompt
from app.agent.utils import extract_json_from_llm_response
import math


def is_tabular(data: Any) -> bool:
    return isinstance(data, list) and all(isinstance(row, dict) for row in data)


def clean_value(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def clean_table_data(table: list[dict]) -> list[dict]:
    return [
        {k: clean_value(v) for k, v in row.items()}
        for row in table
    ]


def attach_table_data(response: Dict[str, Any], result: Any) -> Dict[str, Any]:
    """
    Adds a clean, structured `table_data` field and sets show_data = True
    if the result is actually tabular.
    """
    print("ATTACHING TABLE DATA")
    print(result)
    print("IS TABULAR")
    print(is_tabular(result))
    if is_tabular(result):
        response["table_data"] = clean_table_data(result)
        response["show_data"] = True
    else:
        response["show_data"] = False
    return response


async def format_response_llm(query: str, result: Any) -> Dict[str, Any]:
    """
    Runs the response formatting prompt through the LLM.
    If parsing fails, falls back to simple JSON response with table check.
    """
    user_prompt = render_prompt("format_response/user.jinja", {
        "query": query,
        "result": result
    })
    system_prompt = render_prompt("format_response/system.jinja")
    response_content = await ainvoke_llm(
        user_prompt=user_prompt, 
        system_prompt=system_prompt, 
        profile="creative"
    )

    try:
        parsed = extract_json_from_llm_response(response_content)
        print("PARSED")
        print(parsed)
        return attach_table_data(parsed, result)
    except Exception:
        fallback = {
            "type": "analysis",
            "message": response_content,
            "data": result
        }
        return attach_table_data(fallback, result)


async def format_response(state: AgentState) -> AgentState:
    """
    Final step of the agent: generates a natural-language response
    and optionally attaches a table view of the result.
    """
    if state.execution_result is None:
        state.formatted_response = {
            "type": "error",
            "message": (
                "I couldn't find an answer. "
                "Could you please provide more specific information about what you're looking for?"
            ),
            "show_data": False
        }
        return state

    formatted = await format_response_llm(state.current_query, state.execution_result)
    state.formatted_response = formatted
    return state
