"""Deterministic planning rules for AGENT-01.

The model may choose an activity from the whitelist, but every fallback path
must stay deterministic so fixed inputs with a Mock adapter reproduce the same
``PlannedActivity``. Reasons are generated from candidate facts only and never
invent test results, mastery changes or sources.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.records import RecommendationCandidate
from app.modules.orchestration.catalog import CONCEPT, CourseActivity, CourseCatalog
from app.modules.orchestration.ports import PlannedActivity

MASTERY_THRESHOLD = 0.6
MIN_EVIDENCE_FOR_MASTERY = 1

_ACTIVITY_LABELS: dict[str, str] = {
    "concept": "概念学习",
    "objective": "客观题练习",
    "short_answer": "简答题练习",
    "code": "编程练习",
    "debug": "调试练习",
    "project": "综合项目",
}


class NoAvailableActivityError(Exception):
    """Raised when no legal activity exists for the current course state."""


def mastered_knowledge_point_ids(profile: LearnerProfile) -> frozenset[str]:
    """Knowledge points with enough evidence and score to act as prerequisites."""
    return frozenset(
        state.knowledge_point_id
        for state in profile.mastery
        if state.score >= MASTERY_THRESHOLD and state.evidence_count >= MIN_EVIDENCE_FOR_MASTERY
    )


def prerequisites_satisfied(
    activity: CourseActivity, mastered: frozenset[str]
) -> bool:
    return all(prerequisite in mastered for prerequisite in activity.prerequisites)


def build_whitelist(
    *,
    candidates: Sequence[RecommendationCandidate],
    catalog: CourseCatalog,
    profile: LearnerProfile,
) -> tuple[CourseActivity, ...]:
    """Legal activities reachable from the candidate knowledge points.

    A concept is legal when its prerequisites are satisfied. An exercise is
    legal when it belongs to a candidate knowledge point. A project is legal
    when every covered concept is already mastered.
    """
    mastered = mastered_knowledge_point_ids(profile)
    whitelist: list[CourseActivity] = []
    for candidate in candidates:
        for activity in catalog.activities_for_kp(candidate.knowledge_point_id):
            if activity.activity_type == CONCEPT:
                if prerequisites_satisfied(activity, mastered):
                    whitelist.append(activity)
            else:
                whitelist.append(activity)

    for activity in catalog.activities:
        if activity.activity_type != "project":
            continue
        if activity.concept_ids and all(
            concept_id in mastered for concept_id in activity.concept_ids
        ):
            whitelist.append(activity)

    return tuple(whitelist)


def select_by_rules(
    *,
    candidates: Sequence[RecommendationCandidate],
    catalog: CourseCatalog,
    profile: LearnerProfile,
) -> PlannedActivity:
    """Choose the next activity without a model.

    Order of preference follows the candidate ranking produced by
    ``LearnerProfileService.build_recommendation_data``: reinforcement first,
    then new learning, continued practice, and finally progression.
    """
    mastered = mastered_knowledge_point_ids(profile)

    for candidate in candidates:
        knowledge_point_id = candidate.knowledge_point_id
        if candidate.reason_code == "needs_reinforcement":
            exercise = _first_exercise(catalog, knowledge_point_id)
            if exercise is not None:
                return _plan(exercise, candidate)
            concept = catalog.concept(knowledge_point_id)
            if concept is not None and prerequisites_satisfied(concept, mastered):
                return _plan(concept, candidate)
        elif candidate.reason_code == "insufficient_evidence":
            concept = catalog.concept(knowledge_point_id)
            if concept is not None and prerequisites_satisfied(concept, mastered):
                return _plan(concept, candidate)
        elif candidate.reason_code == "continue_practice":
            exercise = _first_exercise(catalog, knowledge_point_id)
            if exercise is not None:
                return _plan(exercise, candidate)
        elif candidate.reason_code == "ready_to_progress":
            concept = _next_concept(catalog, knowledge_point_id, mastered)
            if concept is not None:
                return _plan(concept, candidate)

    fallback = _first_legal_concept(catalog, mastered)
    if fallback is not None:
        return PlannedActivity(
            activity_id=fallback.activity_id,
            activity_type=fallback.activity_type,
            reason=(
                f"当前课程尚无可用规划路径，从基础活动开始："
                f"{fallback.title}（知识点 {fallback.activity_id}）"
            ),
        )
    raise NoAvailableActivityError(f"course {catalog.course_id} has no legal activity")


def validate_model_choice(
    *,
    activity_id: str,
    activity_type: str,
    whitelist: Sequence[CourseActivity],
    catalog: CourseCatalog,
) -> CourseActivity | None:
    """Return the whitelisted activity only when id and type both match reality."""
    activity = catalog.activity(activity_id)
    if activity is None:
        return None
    if activity.activity_type != activity_type:
        return None
    if not any(item.activity_id == activity_id for item in whitelist):
        return None
    return activity


def build_reason(
    activity: CourseActivity, candidate: RecommendationCandidate | None
) -> str:
    """Explainable reason built only from verifiable facts."""
    label = _ACTIVITY_LABELS.get(activity.activity_type, activity.activity_type)
    knowledge_point_id = activity.knowledge_point_id or activity.concept_ids[0]
    if candidate is None:
        return (
            f"基于当前画像选择{label}：{activity.title}（知识点 {knowledge_point_id}）"
        )
    if candidate.reason_code == "needs_reinforcement":
        return (
            f"知识点 {knowledge_point_id} 掌握度 {candidate.score:.2f} 低于巩固阈值，"
            f"安排{label}以巩固掌握"
        )
    if candidate.reason_code == "insufficient_evidence":
        return (
            f"知识点 {knowledge_point_id} 尚无学习证据，"
            f"从{label}开始建立学习记录"
        )
    if candidate.reason_code == "continue_practice":
        return (
            f"知识点 {knowledge_point_id} 已有部分掌握（证据 {candidate.evidence_count} 条），"
            f"继续{label}以加深理解"
        )
    return (
        f"知识点 {knowledge_point_id} 掌握度 {candidate.score:.2f} 且证据充分，"
        f"进入{label}推进学习"
    )


def _plan(
    activity: CourseActivity, candidate: RecommendationCandidate
) -> PlannedActivity:
    return PlannedActivity(
        activity_id=activity.activity_id,
        activity_type=activity.activity_type,
        reason=build_reason(activity, candidate),
    )


def _first_exercise(
    catalog: CourseCatalog, knowledge_point_id: str
) -> CourseActivity | None:
    exercises = catalog.exercises_for_kp(knowledge_point_id)
    return exercises[0] if exercises else None


def _next_concept(
    catalog: CourseCatalog,
    knowledge_point_id: str,
    mastered: frozenset[str],
) -> CourseActivity | None:
    """The next concept whose prerequisites include the mastered knowledge point."""
    for activity in catalog.activities:
        if activity.activity_type != CONCEPT:
            continue
        if knowledge_point_id not in activity.prerequisites:
            continue
        if prerequisites_satisfied(activity, mastered):
            return activity
    return None


def _first_legal_concept(
    catalog: CourseCatalog, mastered: frozenset[str]
) -> CourseActivity | None:
    for activity in catalog.activities:
        if activity.activity_type != CONCEPT:
            continue
        if prerequisites_satisfied(activity, mastered):
            return activity
    return None
