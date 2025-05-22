from typing import Dict, Any
from app.agent.config import AgentState
from app.utils.llm_provider import ainvoke_llm
from app.utils.prompt_engine import render_prompt
from app.models.agent_response import AttachmentType, FormatResponseLLMResponse
from app.utils.json_encoders import ensure_json_serializable
from app.models.agent_response import Intent
from app.models.agent_response import AnalyzeQuestionLLMResponse
from app.models.visuals import VisualConcept


async def format_response_llm(intent: Intent, query: str, analysis: AnalyzeQuestionLLMResponse | VisualConcept, result: Any) -> Dict[str, Any]:
    """
    Runs the response formatting prompt through the LLM.
    If parsing fails, falls back to simple JSON response with table check.
    """
    user_prompt = render_prompt("format_response/user.jinja", {
        "query": query,
        "result": analysis.to_llm_dict() if intent == Intent.CREATE_VISUAL else result
    })
    system_prompt = render_prompt("format_response/system.jinja")
    response: FormatResponseLLMResponse = await ainvoke_llm(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        profile="creative",
        response_model=FormatResponseLLMResponse
    )
    if (intent == Intent.CREATE_VISUAL):
        response.attach = AttachmentType.VISUAL
        response.data = ensure_json_serializable(result)
    return response


async def format_response(state: AgentState) -> AgentState:
    """
    Final step of the agent: generates a natural-language response
    and optionally attaches a table view of the result.
    """
    if state.execution_result is None:
        state.formatted_response = FormatResponseLLMResponse(
            type="error",
            message="I couldn't find an answer. Could you please provide more specific information about what you're looking for?",
        )
        return state
    formatted: FormatResponseLLMResponse = await format_response_llm(state.intent, state.current_query, state.analysis, state.execution_result)
    state.formatted_response = formatted
    return state
