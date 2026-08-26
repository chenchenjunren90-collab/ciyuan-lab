"""Submission request and result models shared by the API and service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.schemas import NextActivity
from app.modules.learner_profile.models import MasteryState
from app.modules.rag.models import Citation


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubmissionRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    response: str | None = Field(default=None, max_length=20_000)
    language: Literal["c", "python"] | None = None
    source_code: str | None = Field(default=None, max_length=262_144)

    @model_validator(mode="after")
    def require_some_submission(self) -> SubmissionRequest:
        if not (self.response and self.response.strip()) and not (
            self.source_code and self.source_code.strip()
        ):
            raise ValueError("response or source_code is required")
        return self


class VerificationResult(StrictModel):
    accepted: bool
    passed_tests: int = Field(ge=0)
    total_tests: int = Field(ge=0)
    diagnostics: list[str]


class SubmissionResult(StrictModel):
    verification: VerificationResult | None = None
    feedback: str
    citations: list[Citation]
    mastery_updated: list[MasteryState]
    next_activity: NextActivity
