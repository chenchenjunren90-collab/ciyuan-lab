"""Application service for evidence projection and explainable recommendations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.policy import EvidenceMasteryPolicy, MasteryPolicy
from app.modules.learner_profile.records import (
    MasteryUpdateResult,
    RecommendationCandidate,
    RecommendationReasonCode,
)
from app.modules.learner_profile.repository import LearningRepository


class LearnerProfileService:
    def __init__(
        self,
        repository: LearningRepository,
        policy: MasteryPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or EvidenceMasteryPolicy()

    def process_event(self, event_id: UUID) -> MasteryUpdateResult:
        """Project one already-stored event exactly once."""

        return self._repository.project_event(event_id=event_id, policy=self._policy)

    @staticmethod
    def build_recommendation_data(
        *,
        profile: LearnerProfile,
        course_knowledge_point_ids: Sequence[str],
        top_k: int = 5,
    ) -> tuple[RecommendationCandidate, ...]:
        """Rank evidence for AGENT-01 without inventing an activity or content ID."""

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        normalized_ids = [item.strip() for item in course_knowledge_point_ids]
        if not normalized_ids or any(not item for item in normalized_ids):
            raise ValueError("course_knowledge_point_ids must contain non-empty IDs")
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ValueError("course_knowledge_point_ids must be unique")

        known = set(normalized_ids)
        states = {item.knowledge_point_id: item for item in profile.mastery}
        unknown = set(states) - known
        if unknown:
            raise ValueError(f"profile contains unknown knowledge points: {sorted(unknown)}")

        candidates = []
        for knowledge_point_id in normalized_ids:
            state = states.get(knowledge_point_id)
            score = state.score if state is not None else 0.5
            evidence_count = state.evidence_count if state is not None else 0
            reason_code, reason_rank = _recommendation_reason(score, evidence_count)
            confidence = min(1.0, evidence_count / 5)
            priority = round((1 - score) * (0.5 + 0.5 * confidence), 4)
            candidates.append(
                (
                    reason_rank,
                    score,
                    knowledge_point_id,
                    RecommendationCandidate(
                        knowledge_point_id=knowledge_point_id,
                        score=score,
                        evidence_count=evidence_count,
                        confidence=confidence,
                        priority=priority,
                        reason_code=reason_code,
                    ),
                )
            )

        candidates.sort(key=lambda item: item[:3])
        return tuple(item[3] for item in candidates[:top_k])


def _recommendation_reason(
    score: float,
    evidence_count: int,
) -> tuple[RecommendationReasonCode, int]:
    if evidence_count == 0:
        return "insufficient_evidence", 1
    if score < 0.6:
        return "needs_reinforcement", 0
    if score < 0.8:
        return "continue_practice", 2
    return "ready_to_progress", 3
