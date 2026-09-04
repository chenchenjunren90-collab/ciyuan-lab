"""Public course-content responses with answer and hidden-test protection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CourseId = Literal["c", "python", "data_structures"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
ActivityType = Literal["objective", "short_answer", "code", "debug", "project"]
LearningStage = Literal["diagnostic", "in_class", "after_class", "challenge"]


@dataclass(frozen=True, slots=True)
class RagSourceRecord:
    """Internal reviewed source body; never returned by course-content APIs."""

    id: str
    title: str
    course: CourseId
    citation: dict[str, Any]
    text: str


@dataclass(frozen=True, slots=True)
class PracticeActivityRecord:
    """Internal exercise facts including answer keys and hidden tests."""

    id: str
    course: CourseId
    type: ActivityType
    concept_ids: tuple[str, ...]
    prompt: str
    source_refs: tuple[str, ...]
    evaluation: dict[str, Any]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseSummary(StrictModel):
    id: CourseId
    title: str
    status: str
    target_core_concepts: int = Field(ge=0)
    implemented_core_concepts: int = Field(ge=0)
    features: dict[str, str]


class CourseVersionMetadata(StrictModel):
    course_id: CourseId
    version: str
    title: str
    status: str
    manifest_hash: str


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
    concepts: list[str]
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
    learning_stage: LearningStage | None = None


class ActivityExample(StrictModel):
    input: str
    expected_output: str
    explanation: str


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
    fallback_source_refs: list[str] = Field(default_factory=list)
    audience: str | None = None
    scaffolding: list[str] = Field(default_factory=list)
    input_format: str | None = None
    output_format: str | None = None
    constraints: list[str] = Field(default_factory=list)
    public_examples: list[ActivityExample] = Field(default_factory=list)
    reflection_prompt: str | None = None
    source_adaptation: dict[str, str] = Field(default_factory=dict)
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
