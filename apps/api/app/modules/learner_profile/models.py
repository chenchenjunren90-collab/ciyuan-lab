from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class MasteryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_point_id: str
    score: float = Field(ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LearnerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    course_id: str
    mastery: list[MasteryState] = Field(default_factory=list)
