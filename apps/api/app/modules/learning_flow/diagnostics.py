"""Server-graded diagnostic quizzes for initial assessment and reassessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learning_flow.models import AssessmentOutcome
from app.modules.learning_flow.service import LearningFlowService

DiagnosticPhase = Literal["initial", "reassessment"]

_PYTHON_INITIAL = (
    "PY-BASE-01-Q1",
    "PY-BASE-04-Q1",
    "PY-BASE-06-Q1",
    "PY-FUNC-03-Q1",
    "PY-LIST-01-Q1",
    "PY-DICT-01-Q1",
    "PY-FILE-01-Q1",
    "PY-EXC-02-Q1",
)
_PYTHON_REASSESSMENT = (
    "PY-BASE-02-Q1",
    "PY-BASE-03-Q1",
    "PY-BASE-08-Q1",
    "PY-FUNC-04-Q1",
    "PY-LIST-02-Q1",
    "PY-FILE-04-Q1",
    "PY-MOD-02-Q1",
    "PY-DATA-02-Q1",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosticOption(StrictModel):
    id: str
    text: str


class DiagnosticItem(StrictModel):
    exercise_id: str
    title: str
    prompt: str
    concept_ids: list[str]
    options: list[DiagnosticOption] = Field(min_length=2)


class DiagnosticQuiz(StrictModel):
    course_id: CourseId
    phase: DiagnosticPhase
    title: str
    instructions: str
    items: list[DiagnosticItem] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class DiagnosticGrade:
    exercise_id: str
    knowledge_point_id: str
    correct: bool


@dataclass(frozen=True, slots=True)
class DiagnosticSubmissionOutcome:
    phase: DiagnosticPhase
    grades: tuple[DiagnosticGrade, ...]
    assessment: AssessmentOutcome


class DiagnosticService:
    """Select public questions and grade them only against server-side answer keys."""

    def __init__(
        self,
        *,
        courses: CoursePackRepository,
        learning_flow: LearningFlowService,
        item_count: int = 8,
    ) -> None:
        if not 4 <= item_count <= 12:
            raise ValueError("diagnostic item_count must be between 4 and 12")
        self._courses = courses
        self._learning_flow = learning_flow
        self._item_count = item_count

    def build_quiz(
        self, *, course_id: CourseId, phase: DiagnosticPhase
    ) -> DiagnosticQuiz:
        activity_ids = self._select_activity_ids(course_id, phase)
        items: list[DiagnosticItem] = []
        for activity_id in activity_ids:
            activity = self._courses.get_activity(course_id, activity_id)
            options = activity.evaluation.get("options")
            if activity.type != "objective" or not isinstance(options, list):
                raise ValueError(f"diagnostic activity is not an objective item: {activity_id}")
            items.append(
                DiagnosticItem(
                    exercise_id=activity.id,
                    title=activity.title,
                    prompt=activity.prompt or activity.title,
                    concept_ids=activity.concept_ids,
                    options=[DiagnosticOption.model_validate(option) for option in options],
                )
            )
        return DiagnosticQuiz(
            course_id=course_id,
            phase=phase,
            title="初始能力诊断" if phase == "initial" else "阶段能力重测",
            instructions=(
                "请独立完成全部题目。结果将作为学习路径的初始证据。"
                if phase == "initial"
                else "请在不查看原学习材料的情况下完成，以检验能否迁移所学知识。"
            ),
            items=items,
        )

    async def submit(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        phase: DiagnosticPhase,
        answers: list[tuple[str, str]],
    ) -> DiagnosticSubmissionOutcome:
        quiz = self.build_quiz(course_id=course_id, phase=phase)
        expected_ids = [item.exercise_id for item in quiz.items]
        answer_ids = [exercise_id for exercise_id, _ in answers]
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("diagnostic exercise_id values must be unique")
        if set(answer_ids) != set(expected_ids):
            raise ValueError("diagnostic answers must match the current quiz")
        answer_map = {exercise_id: response.strip() for exercise_id, response in answers}
        grades: list[DiagnosticGrade] = []
        evidence: list[tuple[str, bool]] = []
        for item in quiz.items:
            record = self._courses.get_practice_activity(course_id, item.exercise_id)
            accepted = record.evaluation.get("accepted_answers")
            if not isinstance(accepted, list) or not accepted:
                raise ValueError(f"diagnostic answer key is incomplete: {item.exercise_id}")
            correct = answer_map[item.exercise_id] in accepted
            knowledge_point_id = record.concept_ids[0]
            grades.append(
                DiagnosticGrade(
                    exercise_id=item.exercise_id,
                    knowledge_point_id=knowledge_point_id,
                    correct=correct,
                )
            )
            evidence.append((knowledge_point_id, correct))
        assessment = await self._learning_flow.submit_assessment(
            student_id=student_id,
            course_id=course_id,
            answers=evidence,
            evidence_source=f"diagnostic_{phase}",
        )
        return DiagnosticSubmissionOutcome(
            phase=phase,
            grades=tuple(grades),
            assessment=assessment,
        )

    def _select_activity_ids(
        self, course_id: CourseId, phase: DiagnosticPhase
    ) -> tuple[str, ...]:
        if course_id == "python":
            return _PYTHON_INITIAL if phase == "initial" else _PYTHON_REASSESSMENT
        objective_ids = tuple(
            activity.id
            for activity in self._courses.list_activities(course_id)
            if activity.type == "objective"
        )
        if len(objective_ids) < self._item_count:
            raise ValueError(f"course {course_id} has too few objective diagnostic items")
        if phase == "initial":
            return self._spread(objective_ids, self._item_count)
        initial_ids = set(self._spread(objective_ids, self._item_count))
        remaining = tuple(item for item in objective_ids if item not in initial_ids)
        return self._spread(remaining or objective_ids, self._item_count)

    @staticmethod
    def _spread(values: tuple[str, ...], count: int) -> tuple[str, ...]:
        if count >= len(values):
            return values
        indexes = [round(index * (len(values) - 1) / (count - 1)) for index in range(count)]
        return tuple(values[index] for index in indexes)
