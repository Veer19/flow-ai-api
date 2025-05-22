from pydantic import BaseModel
from typing import List
from enum import Enum
from datetime import datetime
from typing import Any, Dict
from pydantic import Field
from typing import Annotated


class VisualType(str, Enum):
    line = "line"
    area = "area"
    bar = "bar"
    pie = "pie"
    donut = "donut"
    radialBar = "radialBar"
    scatter = "scatter"
    bubble = "bubble"
    heatmap = "heatmap"
    candlestick = "candlestick"
    boxPlot = "boxPlot"
    radar = "radar"
    polarArea = "polarArea"
    rangeBar = "rangeBar"
    rangeArea = "rangeArea"
    treemap = "treemap"


class VisualData(BaseModel):
    series: Annotated[List[Any], "The data series for the chart"]
    options: Annotated[Dict[str, Any], "Options for rendering the chart"]


class Visual(BaseModel):
    id: str
    project_id: str
    user_id: str
    title: str
    description: str
    type: VisualType
    python_code: str
    required_dataset_ids: List[str]
    status: str
    data: VisualData
    created_at: datetime


class VisualConcept(BaseModel):
    title: str
    description: str
    type: VisualType
    required_dataset_ids: List[str]

    def to_llm_dict(self) -> Dict[str, Any]:
        """Convert the VisualConcept to a plain dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "required_dataset_ids": self.required_dataset_ids
        }


class VisualConceptsLLMResponse(BaseModel):
    visual_concepts: List[VisualConcept]


class VisualSampleDataLLMResponse(BaseModel):
    visual_sample_data: VisualData


class VisualSampleData(BaseModel):
    visual_concept: VisualConcept
    visual_data: VisualData


class VisualPythonCodeLLMResponse(BaseModel):
    visual_python_code: str
