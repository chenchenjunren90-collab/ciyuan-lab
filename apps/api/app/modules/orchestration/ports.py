from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PlannedActivity:
    activity_id: str
    activity_type: str
    reason: str


class LearningOrchestrator(Protocol):
    """Selects the next activity without owning course content or model providers."""

    async def next_activity(self, student_id: str, course_id: str) -> PlannedActivity: ...
