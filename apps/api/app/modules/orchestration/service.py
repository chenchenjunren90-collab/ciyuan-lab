"""AGENT-01: learning-planning agent with safe degradation.

``LearningPlanner`` implements the frozen ``LearningOrchestrator`` protocol: it
loads the real course catalog, builds recommendation candidates through the
learner-profile service, lets the model choose from a legal whitelist, and
falls back to deterministic rules whenever the model is unconfigured, times
out, is rate limited, or returns an invalid selection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.records import RecommendationCandidate
from app.modules.learner_profile.service import LearnerProfileService
from app.modules.model_adapters.errors import ModelError
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.orchestration.catalog import (
    CourseActivity,
    CourseCatalog,
    CourseNotFoundError,
    load_course_catalog,
)
from app.modules.orchestration.ports import PlannedActivity
from app.modules.orchestration.prompts import (
    ModelChoice,
    build_planning_messages,
    parse_model_choice,
)
from app.modules.orchestration.rules import (
    build_reason,
    build_whitelist,
    select_by_rules,
    validate_model_choice,
)


class ProfileProvider(Protocol):
    """Loads a learner profile for one student and course."""

    def get_profile(self, *, student_id: str, course_id: str) -> LearnerProfile | None: ...


ProfileLoader = Callable[[str, str], LearnerProfile | None]


def _as_profile_loader(provider: ProfileProvider | ProfileLoader) -> ProfileLoader:
    """Normalize either protocol to a simple callable."""
    if isinstance(provider, Callable):  # type: ignore[arg-type]
        return provider  # type: ignore[return-value]
    return lambda student_id, course_id: provider.get_profile(  # type: ignore[union-attr]
        student_id=student_id, course_id=course_id
    )


class LearningPlanner:
    """Concrete planner satisfying the frozen ``LearningOrchestrator`` protocol."""

    def __init__(
        self,
        *,
        catalog: CourseCatalog,
        profile_provider: ProfileProvider | ProfileLoader,
        model_adapter: ModelAdapter,
        top_k: int = 5,
    ) -> None:
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        self._catalog = catalog
        self._profile_loader = _as_profile_loader(profile_provider)
        self._model_adapter = model_adapter
        self._top_k = top_k

    async def next_activity(self, student_id: str, course_id: str) -> PlannedActivity:
        """Select and verify the next activity for the student in one course."""
        if not student_id.strip():
            raise ValueError("student_id must not be empty")
        self._validate_course_id(course_id)
        profile = self._load_profile(student_id, course_id)
        candidates = self._build_candidates(profile)
        whitelist = build_whitelist(candidates=candidates, catalog=self._catalog, profile=profile)
        model_choice = await self._try_model_choice(course_id, candidates, whitelist)
        if model_choice is not None:
            activity = validate_model_choice(
                activity_id=model_choice.activity_id,
                activity_type=model_choice.activity_type,
                whitelist=whitelist,
                catalog=self._catalog,
            )
            if activity is not None:
                candidate = self._candidate_for(activity, candidates)
                return PlannedActivity(
                    activity_id=activity.activity_id,
                    activity_type=activity.activity_type,
                    reason=build_reason(activity, candidate),
                )
        return select_by_rules(candidates=candidates, catalog=self._catalog, profile=profile)

    def _validate_course_id(self, course_id: str) -> None:
        if self._catalog.course_id != course_id:
            raise CourseNotFoundError(f"course not supported by this planner: {course_id}")

    def _load_profile(self, student_id: str, course_id: str) -> LearnerProfile:
        profile = self._profile_loader(student_id, course_id)
        if profile is None:
            return LearnerProfile(student_id=student_id, course_id=course_id)
        if profile.student_id != student_id:
            raise ValueError("profile student_id does not match the request")
        if profile.course_id != course_id:
            raise ValueError("profile course_id does not match the request")
        return profile

    def _build_candidates(self, profile: LearnerProfile) -> Sequence[RecommendationCandidate]:
        course_knowledge_point_ids = [
            item.activity_id for item in self._catalog.activities if item.activity_type == "concept"
        ]
        return LearnerProfileService.build_recommendation_data(
            profile=profile,
            course_knowledge_point_ids=course_knowledge_point_ids,
            top_k=self._top_k,
        )

    async def _try_model_choice(
        self,
        course_id: str,
        candidates: Sequence[RecommendationCandidate],
        whitelist: Sequence[CourseActivity],
    ) -> ModelChoice | None:
        """Ask the model and degrade only expected provider failures to None."""
        try:
            messages = build_planning_messages(
                course_id=course_id,
                candidates=candidates,
                whitelist=whitelist,
            )
            response = await self._model_adapter.complete(messages)
        except ModelError:
            return None
        return parse_model_choice(response.content)

    def _candidate_for(
        self,
        activity: CourseActivity,
        candidates: Sequence[RecommendationCandidate],
    ) -> RecommendationCandidate | None:
        for candidate in candidates:
            if candidate.knowledge_point_id in activity.concept_ids:
                return candidate
        return None


def build_learning_planner(
    *,
    course_id: str,
    profile_provider: ProfileProvider | ProfileLoader,
    model_adapter: ModelAdapter,
    packs_root: str | None = None,
    top_k: int = 5,
) -> LearningPlanner:
    """Convenience factory loading the real course catalog from disk."""
    catalog = load_course_catalog(course_id, packs_root=packs_root)
    return LearningPlanner(
        catalog=catalog,
        profile_provider=profile_provider,
        model_adapter=model_adapter,
        top_k=top_k,
    )
