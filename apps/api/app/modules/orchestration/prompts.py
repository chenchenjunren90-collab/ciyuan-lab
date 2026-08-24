"""Model prompt construction and structured output parsing for AGENT-01.

The planner never sends names, student ids or other personal information to the
model: only the course id, candidate facts and the legal activity whitelist.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.modules.learner_profile.records import RecommendationCandidate
from app.modules.model_adapters.ports import ChatMessage
from app.modules.orchestration.catalog import ACTIVITY_TYPES, CourseActivity
from app.modules.orchestration.ports import PlannedActivity

_MAX_REASON_LENGTH = 500


class ModelChoice:
    """A parsed and structurally valid model selection."""

    __slots__ = ("activity_id", "activity_type")

    def __init__(self, activity_id: str, activity_type: str) -> None:
        self.activity_id = activity_id
        self.activity_type = activity_type


def build_planning_messages(
    *,
    course_id: str,
    candidates: Sequence[RecommendationCandidate],
    whitelist: Sequence[CourseActivity],
) -> tuple[ChatMessage, ...]:
    system = (
        "你是学情规划智能体，负责从合法候选白名单中选择学生的下一项学习活动。"
        "规则：只输出一个 JSON 对象，包含 activity_id 和 activity_type 两个字段；"
        "activity_id 必须取自候选白名单中真实存在的活动；"
        "activity_type 必须与白名单中该活动的类型完全一致；"
        "不得编造任何不存在的 ID、分数、测试结果或个人历史；"
        "不要输出任何 JSON 之外的内容。"
    )
    candidate_lines = [
        {
            "knowledge_point_id": candidate.knowledge_point_id,
            "score": candidate.score,
            "evidence_count": candidate.evidence_count,
            "confidence": candidate.confidence,
            "priority": candidate.priority,
            "reason_code": candidate.reason_code,
        }
        for candidate in candidates
    ]
    whitelist_lines = [
        {"activity_id": activity.activity_id, "activity_type": activity.activity_type}
        for activity in whitelist
    ]
    user = json.dumps(
        {
            "course_id": course_id,
            "candidates": candidate_lines,
            "legal_activities": whitelist_lines,
        },
        ensure_ascii=False,
    )
    return (
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    )


def parse_model_choice(content: str) -> ModelChoice | None:
    """Parse the model reply into a structurally valid selection.

    Returns None when the reply is not JSON or misses required fields, so the
    planner can fall back to deterministic rules.
    """
    payload = _extract_json(content)
    if payload is None:
        return None
    activity_id = payload.get("activity_id")
    activity_type = payload.get("activity_type")
    if not isinstance(activity_id, str) or not activity_id.strip():
        return None
    if not isinstance(activity_type, str) or activity_type not in ACTIVITY_TYPES:
        return None
    return ModelChoice(activity_id=activity_id.strip(), activity_type=activity_type)


def normalize_reason(reason: str | None) -> str | None:
    """Accept only a non-empty, bounded reason."""
    if reason is None:
        return None
    normalized = reason.strip()
    if not normalized or len(normalized) > _MAX_REASON_LENGTH:
        return None
    return normalized


def _extract_json(content: str) -> dict[str, object] | None:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def planned_activity_from_choice(activity: CourseActivity, reason: str) -> PlannedActivity:
    return PlannedActivity(
        activity_id=activity.activity_id,
        activity_type=activity.activity_type,
        reason=reason,
    )
