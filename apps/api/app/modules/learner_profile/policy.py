"""Pure, versioned policy for turning objective evidence into mastery changes.

The MVP intentionally uses a transparent weighted update. A fitted BKT model can
replace this policy later, after the project has enough representative sequences
to estimate skill-specific prior, learn, guess and slip parameters.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Protocol

from app.modules.learner_profile.records import (
    LearningEvent,
    MasteryDecision,
    MasteryRejection,
    MasterySnapshot,
)

_FOUR_PLACES = Decimal("0.0001")


class MasteryPolicy(Protocol):
    version: str
    initial_score: float

    def evaluate(
        self,
        event: LearningEvent,
        current: MasterySnapshot,
    ) -> MasteryDecision | MasteryRejection: ...


class EvidenceMasteryPolicy:
    """Deterministic EWMA policy whose inputs and weights are fully auditable."""

    version = "evidence-ewma-v1"
    initial_score = 0.5
    _weights = {
        "assessment.completed": 0.45,
        "practice.submitted": 0.25,
        "code.verified": 0.35,
    }

    def evaluate(
        self,
        event: LearningEvent,
        current: MasterySnapshot,
    ) -> MasteryDecision | MasteryRejection:
        if event.event_type not in self._weights:
            return MasteryRejection(reason_code="unsupported_event")
        if not event.knowledge_point_id:
            return MasteryRejection(reason_code="insufficient_evidence")

        evidence = self._extract_evidence(event)
        if evidence is None:
            return MasteryRejection(reason_code="insufficient_evidence")
        value, reason_code = evidence
        weight = self._weights[event.event_type]
        score = self._round(current.score + weight * (value - current.score))

        return MasteryDecision(
            knowledge_point_id=event.knowledge_point_id,
            score=score,
            evidence_count=current.evidence_count + 1,
            revision=current.revision + 1,
            evidence_value=value,
            evidence_weight=weight,
            policy_version=self.version,
            reason_code=reason_code,
        )

    @staticmethod
    def _extract_evidence(
        event: LearningEvent,
    ) -> (
        tuple[
            float,
            Literal["assessment_result", "practice_result", "code_test_ratio"],
        ]
        | None
    ):
        payload = event.payload
        if event.event_type == "assessment.completed":
            value = payload.get("is_correct", payload.get("correct"))
            if type(value) is not bool:
                return None
            return (1.0 if value else 0.0), "assessment_result"

        if event.event_type == "practice.submitted":
            accepted = payload.get("accepted")
            if type(accepted) is not bool:
                return None
            return (1.0 if accepted else 0.0), "practice_result"

        passed = payload.get("passed_tests")
        total = payload.get("total_tests")
        accepted = payload.get("accepted")
        if type(passed) is not int or type(total) is not int:
            return None
        if total <= 0 or passed < 0 or passed > total:
            return None
        if accepted is not None and (
            type(accepted) is not bool or accepted is not (passed == total)
        ):
            return None
        return passed / total, "code_test_ratio"

    @staticmethod
    def _round(value: float) -> float:
        bounded = min(1.0, max(0.0, value))
        return float(Decimal(str(bounded)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP))
