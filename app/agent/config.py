from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional, Union, ClassVar
from app.models.visuals import VisualConcept, VisualData
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import get_settings, Settings
from app.models.agent_response import Intent, AnalyzeQuestionLLMResponse, FormatResponseLLMResponse
from app.models.data_sources import DataSource


class AgentConfig(BaseModel):
    """Configuration for the data analysis agent"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: ClassVar[Settings] = get_settings()

    AZURE_OPENAI_DEPLOYMENT: str = settings.AZURE_OPENAI_DEPLOYMENT
    AZURE_OPENAI_API_KEY: str = settings.AZURE_OPENAI_KEY
    AZURE_OPENAI_ENDPOINT: str = settings.AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    MAX_ITERATIONS: int = 5
    TEMPERATURE: float = 0.5


class AgentState(BaseModel):
    """State maintained between agent steps"""
    project_id: str
    intent: Intent = Intent.UNKNOWN
    datasets: Optional[List[DataSource]] = []
    required_datasets: Optional[List[DataSource]] = []
    current_query: Optional[str] = None
    past_messages: Optional[List[Dict[str, Any]]] = []
    generated_code: Optional[str] = None
    execution_result: Optional[Any] = None
    formatted_response: Optional[FormatResponseLLMResponse] = None
    messages: List[Union[SystemMessage, HumanMessage,
                         AIMessage]] = Field(default_factory=list)
    error: Optional[str] = None
    analysis: Optional[AnalyzeQuestionLLMResponse | VisualConcept] = None
    visual_data: Optional[dict[str, VisualData]] = None


class DatasetInfo(BaseModel):
    """Information about a dataset"""
    filename: str
    columns: List[str]
    sample_data: List[Dict[str, Any]]
    row_count: int
