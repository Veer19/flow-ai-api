from functools import lru_cache
from pydantic import BaseModel, ConfigDict, Field
from app.config import get_settings, Settings
from typing import ClassVar
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import asyncio
import random
import functools
from openai import RateLimitError, APIConnectionError
from httpx import HTTPStatusError


class LLMConfig(BaseModel):
    """Configuration for the data analysis agent"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    settings: ClassVar[Settings] = get_settings()
    
    AZURE_OPENAI_DEPLOYMENT: str = settings.AZURE_OPENAI_DEPLOYMENT
    AZURE_OPENAI_API_KEY: str = settings.AZURE_OPENAI_KEY
    AZURE_OPENAI_ENDPOINT: str = settings.AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    MAX_ITERATIONS: int = 5
    TEMPERATURE: float = 0.5

@lru_cache(maxsize=4)
def get_llm(profile: str = "default", temperature: float | None = None) -> AzureChatOpenAI:
    cfg = LLMConfig()

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



TRANSIENT_ERRORS = (RateLimitError, APIConnectionError, HTTPStatusError, TimeoutError)

def retry_on_failure(max_attempts=3, base_delay=0.5, max_delay=4):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except TRANSIENT_ERRORS as e:
                    if attempt == max_attempts - 1:
                        raise  # Let it fail after final attempt
                    delay = min(max_delay, base_delay * 2 ** attempt + random.uniform(0, 0.3))
                    print(f"[retry] {fn.__name__} failed ({e}), retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

@retry_on_failure()
async def ainvoke_llm(
        user_prompt: str, 
        system_prompt: str = "", 
        profile: str = "default",
        response_model: BaseModel | None = None
    ) -> str:
    llm = get_llm(profile=profile)
    if response_model:
        llm = llm.with_structured_output(response_model, method="function_calling")
    result = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    return result
