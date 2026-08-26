from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content.models import CourseId


class ScenarioContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    course_id: CourseId
    mode: Literal["tuoling", "fixed_synthetic"]
    provider_status: Literal["live", "disabled", "fallback"]
    context: str = Field(min_length=1)
    constraints: list[str]
    source_refs: list[str]
    data_classification: str
    notice: str
