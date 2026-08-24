"""Domain outputs for the minimum learning flow."""

from dataclasses import dataclass

from app.modules.learner_profile.models import LearnerProfile
from app.modules.orchestration.ports import PlannedActivity


@dataclass(frozen=True, slots=True)
class PlanStageRecord:
    stage: str
    objective: str
    knowledge_point_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class AssessmentOutcome:
    profile: LearnerProfile
    stages: tuple[PlanStageRecord, ...]
    next_activity: PlannedActivity
