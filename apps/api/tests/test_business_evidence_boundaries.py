"""Service failures and self reports cannot manufacture learner evidence."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from app.modules.adaptive_practice import AdaptiveProblemService
from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.policy import EvidenceMasteryPolicy
from app.modules.learner_profile.records import LearningEvent, MasteryRejection, MasterySnapshot
from app.modules.learning_flow.service import LearningFlowService
from app.modules.model_adapters import MockAdapter
from app.modules.model_adapters.errors import ModelTimeoutError
from app.modules.orchestration.classroom import (
    FIRST_LESSON_ID,
    SECOND_LESSON_ID,
    ClassroomCheckpointRequest,
    ClassroomDialogueRequest,
    ClassroomDialogueService,
    ClassroomDialogueTurn,
    ClassroomLessonService,
    ClassroomSelfProfileRequest,
    _fit_role_answer,
    _role_output_issue,
)
from app.modules.orchestration.ports import PlannedActivity
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor, TutorDraft
from app.modules.practice import DeterministicCodeVerifier, DisabledSandboxRunner
from app.modules.practice.docker_runner import DockerSandboxRunner
from app.modules.practice.ports import CodeTestCase
from app.modules.practice.sandbox import SandboxOutcome, SandboxUnavailableError
from app.modules.practice.service import PracticeSubmissionService
from app.modules.rag.ports import KnowledgeRetrievalError, SearchHit


class EvidenceStore:
    def __init__(self) -> None:
        self.profile = LearnerProfile(
            student_id="evidence-student",
            course_id="python",
            mastery=[MasteryState(knowledge_point_id="PY-DICT-01", score=0.4, evidence_count=2)],
        )
        self.events: list[LearningEvent] = []

    def register_course_version(self, course: object) -> None:
        pass

    def create_profile(self, **kwargs: object) -> None:
        pass

    def get_profile(self, *, student_id: str, course_id: str) -> LearnerProfile | None:
        if (student_id, course_id) == (self.profile.student_id, self.profile.course_id):
            return self.profile
        return None

    def append_event(self, event: LearningEvent) -> bool:
        self.events.append(event)
        return True

    def project_event(self, **kwargs: object) -> None:
        raise AssertionError("Unverified outcomes must never update mastery")


class NextActivity:
    async def next_activity(self, **kwargs: object) -> PlannedActivity:
        return PlannedActivity("PY-DICT-01", "concept", "继续学习字典")


def test_unavailable_practice_runner_preserves_profile_and_creates_no_evidence() -> None:
    store = EvidenceStore()
    before = store.profile.model_dump()
    service = PracticeSubmissionService(
        repository=cast(Any, store),
        courses=CoursePackRepository(),
        verifier=DeterministicCodeVerifier(DisabledSandboxRunner()),
        learning_flow=NextActivity(),
    )
    result = asyncio.run(
        service.submit(
            student_id="evidence-student",
            course_id="python",
            exercise_id="PY-DATA-01-C1",
            response=None,
            language="python",
            source_code="print(1)",
        )
    )
    assert result.profile.model_dump() == before
    assert store.events == []
    assert "未判定代码正确性" in result.feedback
    assert "未更新掌握度" in result.feedback


def test_unavailable_adaptive_runner_keeps_current_problem_and_profile() -> None:
    store = EvidenceStore()
    before = store.profile.model_dump()
    service = AdaptiveProblemService(
        repository=cast(Any, store), verifier=DeterministicCodeVerifier(DisabledSandboxRunner())
    )
    problem = service.generate(student_id="evidence-student", course_id="python", attempt_index=1)
    result = asyncio.run(
        service.submit(
            student_id="evidence-student", problem_id=problem.problem_id, source_code="print(1)"
        )
    )
    assert result.next_problem.problem_id == problem.problem_id
    assert result.profile.model_dump() == before
    assert store.events == []
    assert "未更新掌握度" in result.feedback


def test_partial_runner_failure_is_not_a_scored_test_ratio() -> None:
    class Runner:
        calls = 0

        async def run(self, request: object) -> SandboxOutcome:
            self.calls += 1
            if self.calls == 2:
                raise SandboxUnavailableError("infrastructure failed")
            return SandboxOutcome(return_code=0, stdout="1")

    cases = tuple(CodeTestCase(str(i), "public", "", "1") for i in range(2))
    result = asyncio.run(
        DeterministicCodeVerifier(Runner()).verify("python", "print(1)", cases, {})
    )
    assert result.passed_tests == 1
    assert result.evidence_available is False


@pytest.mark.parametrize("claimed_correct", [True, False])
def test_repeated_client_self_report_cannot_change_existing_mastery(claimed_correct: bool) -> None:
    store = EvidenceStore()
    before = store.profile.model_dump()
    service = LearningFlowService(
        repository=cast(Any, store), courses=CoursePackRepository(), model_adapter=MockAdapter()
    )
    for _ in range(3):
        outcome = asyncio.run(
            service.submit_assessment(
                student_id="evidence-student",
                course_id="python",
                answers=[("PY-DICT-01", claimed_correct)],
            )
        )
        assert "未计入客观学习证据" in outcome.next_activity.reason
    assert store.profile.model_dump() == before
    assert len(store.events) == 3
    assert all("is_correct" not in event.payload for event in store.events)
    assert all(event.payload["self_reported_correct"] is claimed_correct for event in store.events)


def test_policy_rejects_legacy_claim_even_if_it_contains_is_correct() -> None:
    event = LearningEvent(
        event_id=uuid4(),
        schema_version="0.1.0",
        event_type="assessment.completed",
        occurred_at=datetime.now(UTC),
        student_id="s",
        course_id="python",
        course_version="0.1.0",
        knowledge_point_id="PY-DICT-01",
        payload={"is_correct": True, "source": "legacy_client_assessment"},
    )
    result = EvidenceMasteryPolicy().evaluate(event, MasterySnapshot(0.4, 2, 2))
    assert isinstance(result, MasteryRejection)
    assert result.reason_code == "insufficient_evidence"


class FailingRetriever:
    def __init__(self, empty_first: bool = False) -> None:
        self.empty_first = empty_first
        self.calls = 0

    async def search(self, *args: object) -> tuple[()]:
        self.calls += 1
        if self.empty_first and self.calls == 1:
            return ()
        raise KnowledgeRetrievalError("private backend detail must not be shown")


class EmptyRetriever:
    async def search(self, *args: object) -> tuple[()]:
        return ()


class NeverTutor:
    async def draft(self, **kwargs: object) -> None:
        raise AssertionError("retrieval outage must not trigger tutor generation")


@pytest.mark.parametrize("stage", ["direct", "context", "online"])
def test_classroom_retrieval_outage_is_a_visible_degradation(stage: str) -> None:
    service = ClassroomDialogueService(
        courses=CoursePackRepository(),
        # Context-dependent questions now go straight to a history-enriched
        # query instead of making a redundant direct lookup first.
        retriever=cast(Any, EmptyRetriever() if stage == "online" else FailingRetriever()),
        online_retriever=cast(Any, FailingRetriever()) if stage == "online" else None,
        tutor=cast(Any, NeverTutor()),
        supervisor=QualitySupervisor(),
    )
    request = ClassroomDialogueRequest(
        student_id="evidence-student",
        lesson_id=FIRST_LESSON_ID,
        phase="concept",
        role="teacher",
        message="那它到底做什么？" if stage == "context" else "Python print 是什么意思？",
        recent_turns=[ClassroomDialogueTurn(role="student", content="print 是什么意思？")]
        if stage == "context"
        else [],
    )
    result = asyncio.run(service.answer(request))
    assert result.status == "insufficient_evidence"
    assert result.trace[0].status == "degraded"
    assert "暂时不可用" in result.answer
    assert "private" not in result.model_dump_json()
    assert result.citations == []


def test_self_profile_marks_retrieval_outage_without_claiming_evidence() -> None:
    service = ClassroomDialogueService(
        courses=CoursePackRepository(),
        retriever=cast(Any, FailingRetriever()),
        tutor=cast(Any, NeverTutor()),
        supervisor=QualitySupervisor(),
    )
    result = asyncio.run(
        service.assess_self_profile(
            ClassroomSelfProfileRequest(
                student_id="evidence-student",
                lesson_id=FIRST_LESSON_ID,
                description="我之前没有学过任何编程语言。",
            )
        )
    )
    assert result.trace[0].status == "degraded"
    assert result.citations == []
    assert "暂时不可用" in result.advisor_message


def test_hidden_compilation_diagnostic_does_not_expose_test_stdin() -> None:
    class Runner:
        async def run(self, request: object) -> SandboxOutcome:
            return SandboxOutcome(return_code=120, compilation_failed=True, stderr="secret-input")

    result = asyncio.run(
        DeterministicCodeVerifier(Runner()).verify(
            "c", "source", (CodeTestCase("h", "hidden", "secret-input", "secret-output"),), {}
        )
    )
    assert "secret" not in " ".join(result.diagnostics)


def test_output_capture_limits_combined_stdout_and_stderr_and_kills_flood() -> None:
    async def run() -> None:
        class Process:
            def __init__(self) -> None:
                self.stdout = asyncio.StreamReader()
                self.stderr = asyncio.StreamReader()
                self.stdin = None
                self.returncode: int | None = None
                self.killed = False
                self.stdout.feed_data(b"x" * 4096)
                self.stderr.feed_data(b"y" * 4096)
                self.done = asyncio.Event()

            def kill(self) -> None:
                self.killed = True
                self.returncode = -9
                self.stdout.feed_eof()
                self.stderr.feed_eof()
                self.done.set()

            async def wait(self) -> int:
                await self.done.wait()
                return cast(int, self.returncode)

        process = Process()
        stdout, stderr, exceeded = await asyncio.wait_for(
            DockerSandboxRunner._capture_bounded(cast(Any, process), b"", 1024), timeout=1
        )
        assert exceeded is True
        assert process.killed is True
        assert len(stdout) + len(stderr) <= 1024

    asyncio.run(run())


def test_natural_teacher_answer_does_not_require_a_scripted_question() -> None:
    answer = "print 把内容显示到输出。请运行 print(2)，对照输出确认。"
    assert (
        _role_output_issue(
            role="teacher", question="print 做什么？", answer=answer, has_history=False
        )
        == ""
    )
    clipped = _fit_role_answer("teacher", "print 用于输出。" * 100)
    assert len(clipped) <= 220
    assert "可以继续吗" not in clipped


class TimedOutReviewer:
    async def complete(self, messages: object) -> None:
        raise ModelTimeoutError("private provider detail")


@pytest.mark.parametrize("reviewer", [MockAdapter(), TimedOutReviewer()])
def test_configured_unavailable_supervisor_never_releases_generated_prose(reviewer: object) -> None:
    hit = SearchHit("SRC-PY-test", "chunk-test", "print 用于输出。", 0.8, {})
    draft = TutorDraft("print 的自编断言不应直接放行。", (hit.chunk_id,), False)
    result = asyncio.run(
        QualitySupervisor(cast(Any, reviewer)).review(draft=draft, evidence=(hit,))
    )
    assert result.accepted is False
    assert result.model_degraded is True
    assert result.model_reviewed is False
    assert result.reason_code == "semantic_review_unavailable"
    assert result.answer == ""
    assert result.citations == ()


def test_application_evidence_fallback_does_not_require_generative_review() -> None:
    class Reviewer:
        async def complete(self, messages: object) -> None:
            raise AssertionError("Evidence extraction uses the explicit local rule gate")

    hits = (SearchHit("SRC-PY-test", "chunk-test", "print 用于输出。", 0.8, {}),)
    draft = asyncio.run(CourseTutor(MockAdapter()).draft(question="print 是什么？", evidence=hits))
    assert draft.degraded is True
    result = asyncio.run(
        QualitySupervisor(cast(Any, Reviewer())).review(draft=draft, evidence=hits)
    )
    assert result.accepted is True
    assert result.model_reviewed is False
    assert result.citations == hits


def test_classroom_replaces_unreviewed_prose_with_cited_conservative_answer() -> None:
    hit = SearchHit("SRC-PY-test", "chunk-test", "print 把内容显示到标准输出。", 0.8, {})

    class Retriever:
        async def search(self, *args: object) -> tuple[SearchHit, ...]:
            return (hit,)

    class Tutor:
        async def draft(self, **kwargs: object) -> TutorDraft:
            return TutorDraft("print 的自编断言不应直接放行。", (hit.chunk_id,), False)

    service = ClassroomDialogueService(
        courses=CoursePackRepository(),
        retriever=Retriever(),
        tutor=cast(Any, Tutor()),
        supervisor=QualitySupervisor(cast(Any, TimedOutReviewer())),
    )
    result = asyncio.run(
        service.answer(
            ClassroomDialogueRequest(
                student_id="evidence-student",
                lesson_id=FIRST_LESSON_ID,
                phase="concept",
                role="teacher",
                message="print 是什么意思？",
            )
        )
    )
    assert result.status == "answered"
    assert "自编断言" not in result.answer
    assert "print" in result.answer
    assert result.citations[0].chunk_id == hit.chunk_id
    assert result.trace[-1].status == "degraded"
    assert "模型语义审核与确定性" not in result.trace[-1].detail


@pytest.mark.parametrize("status", ["completed", "degraded"])
def test_classroom_records_maas_rerank_outcome(status: str) -> None:
    class Retriever:
        async def search(self, *args: object) -> tuple[SearchHit, ...]:
            return (
                SearchHit(
                    "SRC-PY-test",
                    "chunk-test",
                    "print 把内容显示到标准输出。",
                    0.8,
                    {"rerank_status": status, "rerank_provider": "xfyun-maas"},
                ),
            )

    class Tutor:
        async def draft(self, **kwargs: object) -> TutorDraft:
            return TutorDraft(
                "print 把内容显示到标准输出。请运行 print(1) 检查。", ("chunk-test",), False
            )

    service = ClassroomDialogueService(
        courses=CoursePackRepository(),
        retriever=Retriever(),
        tutor=cast(Any, Tutor()),
        supervisor=QualitySupervisor(),
    )
    result = asyncio.run(
        service.answer(
            ClassroomDialogueRequest(
                student_id="evidence-student",
                lesson_id=FIRST_LESSON_ID,
                phase="concept",
                role="teacher",
                message="print 是什么意思？",
            )
        )
    )
    assert result.trace[0].status == status
    assert "MaaS" in result.trace[0].detail
    assert ("保留课程检索排序" in result.trace[0].detail) is (status == "degraded")
    assert "模型语义审核与确定性" not in result.trace[-1].detail


@pytest.mark.parametrize(
    ("lesson_id", "beat_id"),
    [(FIRST_LESSON_ID, "dict-beat-model"), (SECOND_LESSON_ID, "beat-traversal")],
)
def test_checkpoint_from_another_lesson_cannot_be_accepted(lesson_id: str, beat_id: str) -> None:
    service = ClassroomLessonService(CoursePackRepository())
    with pytest.raises(LookupError, match="checkpoint not found"):
        service.evaluate_checkpoint(
            ClassroomCheckpointRequest(lesson_id=lesson_id, beat_id=beat_id, response="A")
        )
