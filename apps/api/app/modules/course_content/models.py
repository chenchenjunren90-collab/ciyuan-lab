"""Public course-content responses with answer and hidden-test protection."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CourseId = Literal["c", "python", "data_structures"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
ActivityType = Literal["objective", "short_answer", "code", "debug", "project"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseSummary(StrictModel):
    id: CourseId
    title: str
    status: str
    target_core_concepts: int = Field(ge=0)
    implemented_core_concepts: int = Field(ge=0)
    features: dict[str, str]


class KnowledgePointDetail(StrictModel):
    id: str
    title: str
    course: CourseId
    difficulty: Difficulty
    estimated_minutes: int = Field(gt=0)
    prerequisites: list[str]
    learning_objectives: list[str]
    concepts: list[str]
    lesson: dict[str, Any]
    assessment_ids: list[str]
    source_refs: list[str]
    status: str


class KnowledgePointSummary(StrictModel):
    id: str
    title: str
    difficulty: Difficulty
    prerequisites: list[str]
    source_refs: list[str]


class KnowledgePointList(StrictModel):
    course_id: CourseId
    items: list[KnowledgePointSummary]


class ActivitySummary(StrictModel):
    id: str
    title: str
    course: CourseId
    type: ActivityType
    difficulty: Difficulty
    estimated_minutes: int = Field(gt=0)
    concept_ids: list[str]
    source_refs: list[str]


class ActivityDetail(ActivitySummary):
    prompt: str | None = None
    summary: str | None = None
    requirements: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    evaluation: dict[str, Any]
    scenario_scope: str | None = None
    scenario_provider: str | None = None
    data_classification: str | None = None
    computer_science_objectives: list[str] = Field(default_factory=list)
    business_context_objectives: list[str] = Field(default_factory=list)
    status: str


class SourceDetail(StrictModel):
    id: str
    title: str
    course: CourseId
    source_type: str
    citation: dict[str, Any]
    rights: dict[str, Any]
    data_classification: str
    rag_eligible: bool
    status: str
