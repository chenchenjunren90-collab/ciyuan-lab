"""Student-safe models for generated Python practice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.learner_profile.models import LearnerProfile
from app.modules.practice.models import VerificationResult
from app.modules.practice.ports import CodeTestCase


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicExample(StrictModel):
    input: str
    expected_output: str


class GeneratedCodeProblem(StrictModel):
    problem_id: str
    course_id: Literal["python"] = "python"
    title: str
    prompt: str
    concept_ids: list[str] = Field(min_length=1)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    constraints: list[str] = Field(min_length=1)
    public_examples: list[PublicExample] = Field(min_length=1)
    starter_code: str
    hints: list[str] = Field(min_length=3, max_length=3)
    generation_notice: str


@dataclass(frozen=True, slots=True)
class GeneratedProblemBundle:
    public: GeneratedCodeProblem
    tests: tuple[CodeTestCase, ...]
    template_id: str


@dataclass(frozen=True, slots=True)
class AdaptiveProblemSubmission:
    problem: GeneratedCodeProblem
    verification: VerificationResult
    feedback: str
    profile: LearnerProfile
    next_problem: GeneratedCodeProblem
