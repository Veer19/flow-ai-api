from functools import lru_cache
from langchain_openai import AzureChatOpenAI
from .config import AgentConfig
from langchain_core.messages import SystemMessage, HumanMessage
from .retry_handler import retry_on_failure
@lru_cache(maxsize=4)
def get_llm(profile: str = "default", temperature: float | None = None) -> AzureChatOpenAI:
    cfg = AgentConfig()

    # Define routing logic based on profile
    profile_config = {
        "default": {
            "deployment_name": cfg.AZURE_OPENAI_DEPLOYMENT,
            "temperature": cfg.TEMPERATURE,
        },
        "analyze": {
            "deployment_name": cfg.AZURE_OPENAI_DEPLOYMENT,
            "temperature": 0.7,
        },
        "code": {
            "deployment_name": cfg.AZURE_OPENAI_DEPLOYMENT,  # or another like "gpt-code"
            "temperature": 0.0,
        },
        "creative": {
            "deployment_name": cfg.AZURE_OPENAI_DEPLOYMENT,
            "temperature": 0.7,
        }
    }

    if profile not in profile_config:
        raise ValueError(f"Unknown LLM profile: {profile}")

    # Allow caller to override temperature
    selected = profile_config[profile]
    if temperature is not None:
        selected["temperature"] = temperature

    return AzureChatOpenAI(
        deployment_name=selected["deployment_name"],
        openai_api_key=cfg.AZURE_OPENAI_API_KEY,
        azure_endpoint=cfg.AZURE_OPENAI_ENDPOINT,
        api_version=cfg.AZURE_OPENAI_API_VERSION,
        temperature=selected["temperature"]
    )

@retry_on_failure()
async def ainvoke_llm(user_prompt: str, system_prompt: str = "", profile: str = "default") -> str:
    llm = get_llm(profile=profile)
    result = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    return result.content
