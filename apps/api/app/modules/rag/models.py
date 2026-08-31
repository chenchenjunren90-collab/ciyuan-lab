"""Public RAG question-answering models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QaRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    course_id: CourseId
    question: str = Field(min_length=2, max_length=1000)


class Citation(StrictModel):
    source_id: str
    chunk_id: str
    score: float = Field(ge=0, le=1)
    source_type: Literal["course", "online"] = "course"
    source_title: str | None = None
    source_url: str | None = None


class AgentTraceStep(StrictModel):
    """Student-safe execution audit, never hidden chain-of-thought."""

    component: Literal["retrieval", "course_tutor", "quality_supervisor"]
    status: Literal["completed", "degraded", "blocked"]
    detail: str


class QaResponse(StrictModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str
    citations: list[Citation]
    trace: list[AgentTraceStep] = Field(default_factory=list)
