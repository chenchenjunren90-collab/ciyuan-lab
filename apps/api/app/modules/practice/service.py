"""Exercise submission, objective evidence and next-activity loop."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import uuid4

from app.modules.course_content import (
    CourseId,
    CoursePackRepository,
    PracticeActivityRecord,
)
from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.policy import EvidenceMasteryPolicy
from app.modules.learner_profile.records import LearningEvent
from app.modules.learning_flow.service import LearningStore
from app.modules.practice.models import VerificationResult
from app.modules.practice.ports import (
    CodeTestCase,
    CodeVerifier,
)
from app.modules.practice.ports import (
    VerificationResult as DomainVerificationResult,
)


class NextActivityProvider(Protocol):
    async def next_activity(self, *, student_id: str, course_id: CourseId) -> Any: ...


class SubmissionOutcome:
    def __init__(
        self,
        *,
        verification: VerificationResult | None,
        feedback: str,
        profile: LearnerProfile,
        next_activity: Any,
    ) -> None:
        self.verification = verification
        self.feedback = feedback
        self.profile = profile
        self.next_activity = next_activity


class PracticeSubmissionService:
    def __init__(
        self,
        *,
        repository: LearningStore,
        courses: CoursePackRepository,
        verifier: CodeVerifier,
        learning_flow: NextActivityProvider,
    ) -> None:
        self._repository = repository
        self._courses = courses
        self._verifier = verifier
        self._learning_flow = learning_flow
        self._policy = EvidenceMasteryPolicy()

    async def submit(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        exercise_id: str,
        response: str | None,
        language: str | None,
        source_code: str | None,
    ) -> SubmissionOutcome:
        profile = self._repository.get_profile(student_id=student_id, course_id=course_id)
        if profile is None:
            raise LookupError("learner profile not found; complete assessment first")
        activity = self._courses.get_practice_activity(course_id, exercise_id)
        accepted, verification = await self._evaluate(
            activity=activity,
            response=response,
            language=language,
            source_code=source_code,
        )
        event = self._event(
            activity=activity,
            student_id=student_id,
            accepted=accepted,
            verification=verification,
        )
        if self._repository.append_event(event):
            self._repository.project_event(event_id=event.event_id, policy=self._policy)

        updated = self._repository.get_profile(student_id=student_id, course_id=course_id)
        if updated is None:  # pragma: no cover - repository invariant
            raise LookupError("learner profile disappeared after submission")
        next_activity = await self._learning_flow.next_activity(
            student_id=student_id, course_id=course_id
        )
        return SubmissionOutcome(
            verification=self._verification_model(verification),
            feedback=self._feedback(activity, accepted, verification),
            profile=updated,
            next_activity=next_activity,
        )

    async def _evaluate(
        self,
        *,
        activity: PracticeActivityRecord,
        response: str | None,
        language: str | None,
        source_code: str | None,
    ) -> tuple[bool, DomainVerificationResult | None]:
        evaluation = activity.evaluation
        if activity.type == "objective":
            if not response or not response.strip():
                raise ValueError("objective exercise requires response")
            accepted_answers = evaluation.get("accepted_answers")
            if not isinstance(accepted_answers, list):
                raise ValueError("objective exercise has no answer key")
            return response.strip() in accepted_answers, None
        if activity.type == "short_answer":
            raise ValueError("short-answer automatic scoring is not enabled in the MVP")
        if activity.type not in {"code", "debug"}:
            raise ValueError(f"unsupported exercise type: {activity.type}")
        if not source_code or not source_code.strip() or language not in {"c", "python"}:
            raise ValueError("code exercise requires language and source_code")
        runtime = evaluation.get("runtime")
        tests = evaluation.get("tests")
        if not isinstance(runtime, dict) or not isinstance(tests, list):
            raise ValueError("code exercise evaluation is incomplete")
        expected_language = runtime.get("language")
        if language != expected_language:
            raise ValueError(f"exercise requires language {expected_language}")
        cases = tuple(self._test_case(item) for item in tests)
        limits = {
            key: cast(int, runtime[key])
            for key in ("time_limit_ms", "memory_limit_mb", "output_limit_kb")
        }
        result = await self._verifier.verify(cast(Any, language), source_code, cases, limits)
        return result.accepted, result

    def _event(
        self,
        *,
        activity: PracticeActivityRecord,
        student_id: str,
        accepted: bool,
        verification: DomainVerificationResult | None,
    ) -> LearningEvent:
        metadata = self._courses.get_version_metadata(activity.course)
        payload: dict[str, object] = {"accepted": accepted, "exercise_id": activity.id}
        event_type = "practice.submitted"
        if verification is not None:
            event_type = "code.verified"
            payload.update(
                {
                    "passed_tests": verification.passed_tests,
                    "total_tests": verification.total_tests,
                }
            )
        return LearningEvent(
            event_id=uuid4(),
            schema_version="0.1.0",
            event_type=cast(Any, event_type),
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id=activity.course,
            course_version=metadata.version,
            knowledge_point_id=activity.concept_ids[0],
            trace_id=activity.id,
            payload=payload,
            evidence_summary="确定性练习判定结果",
        )

    @staticmethod
    def _test_case(value: object) -> CodeTestCase:
        if not isinstance(value, dict):
            raise ValueError("test case must be a mapping")
        return CodeTestCase(
            id=str(value["id"]),
            visibility=cast(Any, value["visibility"]),
            input=str(value["input"]),
            expected_output=str(value["expected_output"]),
        )

    @staticmethod
    def _verification_model(
        value: DomainVerificationResult | None,
    ) -> VerificationResult | None:
        if value is None:
            return None
        return VerificationResult(
            accepted=value.accepted,
            passed_tests=value.passed_tests,
            total_tests=value.total_tests,
            diagnostics=list(value.diagnostics),
        )

    @staticmethod
    def _feedback(
        activity: PracticeActivityRecord,
        accepted: bool,
        verification: DomainVerificationResult | None,
    ) -> str:
        if accepted:
            return f"{activity.id} 已通过确定性判定。请回顾关键边界，并继续下一项活动。"
        if verification and verification.diagnostics:
            return "尚未通过。先根据验证事实逐项定位：" + "；".join(verification.diagnostics[:3])
        return "答案尚未通过。请重新核对题意、适用条件和边界，再提交一次。"
