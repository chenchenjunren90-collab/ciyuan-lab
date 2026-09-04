"""Server-graded diagnostic quizzes for initial assessment and reassessment."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learning_flow.models import AssessmentOutcome
from app.modules.learning_flow.service import LearningFlowService

DiagnosticPhase = Literal["initial", "reassessment"]
UNKNOWN_DIAGNOSTIC_RESPONSE = "UNKNOWN"

# Correct options are deliberately spread across visible positions.  The
# source course pack keeps its stable answer ids, while a diagnostic quiz gets
# a deterministic display order and fresh A/B/C/D labels.  This avoids the
# accidental "mostly B" pattern without exposing or changing source answers.
_BALANCED_CORRECT_POSITIONS = (1, 3, 0, 2, 2, 0, 3, 1, 0, 2, 1, 3)

_PYTHON_INITIAL = (
    "PY-BASE-01-Q1",
    "PY-BASE-02-Q1",
    "PY-BASE-03-Q1",
    "PY-BASE-04-Q1",
    "PY-BASE-06-Q1",
    "PY-BASE-08-Q1",
    "PY-LIST-01-Q1",
    "PY-DICT-01-Q1",
    "PY-FUNC-03-Q1",
    "PY-DATA-02-Q1",
    "PY-EXC-02-Q1",
    "PY-ALGO-01-Q1",
)
_PYTHON_REASSESSMENT = (
    "PY-BASE-02-Q1",
    "PY-BASE-03-Q1",
    "PY-BASE-09-Q1",
    "PY-BASE-10-Q1",
    "PY-FUNC-04-Q1",
    "PY-LIST-02-Q1",
    "PY-STR-02-Q1",
    "PY-SET-01-Q1",
    "PY-FILE-04-Q1",
    "PY-MOD-02-Q1",
    "PY-OOP-01-Q1",
    "PY-ALGO-02-Q1",
    "PY-DATA-02-Q1",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosticOption(StrictModel):
    id: str
    text: str


class DiagnosticSkillAtom(StrictModel):
    id: str
    knowledge_point_id: str
    label: str


class DiagnosticItem(StrictModel):
    exercise_id: str
    title: str
    prompt: str
    concept_ids: list[str]
    skill_atoms: list[DiagnosticSkillAtom]
    options: list[DiagnosticOption] = Field(min_length=2)


class DiagnosticQuiz(StrictModel):
    course_id: CourseId
    phase: DiagnosticPhase
    title: str
    instructions: str
    items: list[DiagnosticItem] = Field(min_length=1)


class DiagnosticPrerequisiteGap(StrictModel):
    downstream_id: str
    downstream_title: str
    missing_prerequisite_id: str
    missing_prerequisite_title: str
    reason: str


class DiagnosticLearningBlock(StrictModel):
    block_id: str
    knowledge_point_id: str
    title: str
    reason: str
    estimated_minutes: int = Field(gt=0)
    skill_atoms: list[DiagnosticSkillAtom]
    summary: str
    key_points: list[str]
    example_problem: str = ""
    example_steps: list[str] = Field(default_factory=list)
    example_code: str = ""


class DiagnosticAnalysis(StrictModel):
    course_core_nodes: int = Field(gt=0)
    course_skill_atoms: int = Field(gt=0)
    assessed_core_nodes: int = Field(ge=0)
    assessed_skill_atoms: int = Field(ge=0)
    evidence_scope: Literal["knowledge_point_proxy"]
    non_linear_profile: bool
    prerequisite_gaps: list[DiagnosticPrerequisiteGap]
    demonstrated_knowledge_point_ids: list[str]
    focus_knowledge_point_ids: list[str]
    learning_blocks: list[DiagnosticLearningBlock]


@dataclass(frozen=True, slots=True)
class DiagnosticGrade:
    exercise_id: str
    knowledge_point_id: str
    correct: bool
    unknown: bool
    skill_atoms: tuple[DiagnosticSkillAtom, ...]


@dataclass(frozen=True, slots=True)
class DiagnosticSubmissionOutcome:
    phase: DiagnosticPhase
    grades: tuple[DiagnosticGrade, ...]
    analysis: DiagnosticAnalysis
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
        for item_index, activity_id in enumerate(activity_ids):
            activity = self._courses.get_activity(course_id, activity_id)
            knowledge_point_id = activity.concept_ids[0]
            knowledge_point = self._courses.get_knowledge_point(
                course_id, knowledge_point_id
            )
            options = activity.evaluation.get("options")
            if activity.type != "objective" or not isinstance(options, list):
                raise ValueError(f"diagnostic activity is not an objective item: {activity_id}")
            graded_activity = self._courses.get_practice_activity(course_id, activity_id)
            public_options, _ = self._balanced_options(
                graded_activity.evaluation,
                item_index,
            )
            public_options.append(
                DiagnosticOption(
                    id=UNKNOWN_DIAGNOSTIC_RESPONSE,
                    text="我不知道 / 还没有学过",
                )
            )
            items.append(
                DiagnosticItem(
                    exercise_id=activity.id,
                    title=activity.title,
                    prompt=activity.prompt or activity.title,
                    concept_ids=activity.concept_ids,
                    skill_atoms=list(self._skill_atoms(knowledge_point)),
                    options=public_options,
                )
            )
        return DiagnosticQuiz(
            course_id=course_id,
            phase=phase,
            title="初始能力诊断" if phase == "initial" else "阶段能力重测",
            instructions=(
                "请独立完成全部题目；不确定时请直接选择“我不知道”，比猜答案更有助于安排合适起点。"
                if phase == "initial"
                else (
                    "请在不查看原学习材料的情况下完成；"
                    "不确定时请选择“我不知道”，系统会据此安排回补。"
                )
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
        for item_index, item in enumerate(quiz.items):
            record = self._courses.get_practice_activity(course_id, item.exercise_id)
            _, accepted = self._balanced_options(record.evaluation, item_index)
            response = answer_map[item.exercise_id]
            allowed_responses = {option.id for option in item.options}
            if response not in allowed_responses:
                raise ValueError(
                    f"diagnostic response is not a public option: {item.exercise_id}"
                )
            unknown = response == UNKNOWN_DIAGNOSTIC_RESPONSE
            correct = not unknown and response in accepted
            knowledge_point_id = record.concept_ids[0]
            grades.append(
                DiagnosticGrade(
                    exercise_id=item.exercise_id,
                    knowledge_point_id=knowledge_point_id,
                    correct=correct,
                    unknown=unknown,
                    skill_atoms=tuple(item.skill_atoms),
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
            analysis=self._analyse(course_id=course_id, grades=tuple(grades)),
            assessment=assessment,
        )

    def _analyse(
        self,
        *,
        course_id: CourseId,
        grades: tuple[DiagnosticGrade, ...],
    ) -> DiagnosticAnalysis:
        knowledge_points = self._courses.list_knowledge_points(course_id)
        by_id = {item.id: item for item in knowledge_points}
        correct_by_id = {item.knowledge_point_id: item.correct for item in grades}

        def assessed_missing_prerequisites(knowledge_point_id: str) -> list[str]:
            missing: list[str] = []
            visited: set[str] = set()

            def visit(current_id: str) -> None:
                if current_id in visited:
                    return
                visited.add(current_id)
                current = by_id.get(current_id)
                if current is None:
                    return
                for prerequisite_id in current.prerequisites:
                    if correct_by_id.get(prerequisite_id) is False:
                        missing.append(prerequisite_id)
                    visit(prerequisite_id)

            visit(knowledge_point_id)
            return list(dict.fromkeys(missing))

        gaps: list[DiagnosticPrerequisiteGap] = []
        for downstream_id, correct in correct_by_id.items():
            if not correct:
                continue
            downstream = by_id[downstream_id]
            for prerequisite_id in assessed_missing_prerequisites(downstream_id):
                prerequisite = by_id[prerequisite_id]
                gaps.append(
                    DiagnosticPrerequisiteGap(
                        downstream_id=downstream_id,
                        downstream_title=downstream.title,
                        missing_prerequisite_id=prerequisite_id,
                        missing_prerequisite_title=prerequisite.title,
                        reason=(
                            f"已证明会“{downstream.title}”，但前置“{prerequisite.title}”"
                            "本轮未通过，需要精准回补而不是从头重学。"
                        ),
                    )
                )

        gap_ids = [item.missing_prerequisite_id for item in gaps]
        incorrect_ids = [
            item.knowledge_point_id for item in grades if not item.correct
        ]
        focus_ids = list(dict.fromkeys([*gap_ids, *incorrect_ids]))[:6]
        learning_blocks = [
            self._learning_block(
                course_id=course_id,
                knowledge_point_id=knowledge_point_id,
                is_prerequisite_gap=knowledge_point_id in gap_ids,
            )
            for knowledge_point_id in focus_ids
        ]
        all_atoms = {
            atom.id
            for item in knowledge_points
            for atom in self._skill_atoms(
                self._courses.get_knowledge_point(course_id, item.id)
            )
        }
        assessed_atoms = {
            atom.id for grade in grades for atom in grade.skill_atoms
        }
        return DiagnosticAnalysis(
            course_core_nodes=len(knowledge_points),
            course_skill_atoms=len(all_atoms),
            assessed_core_nodes=len(correct_by_id),
            assessed_skill_atoms=len(assessed_atoms),
            evidence_scope="knowledge_point_proxy",
            non_linear_profile=bool(gaps),
            prerequisite_gaps=gaps,
            demonstrated_knowledge_point_ids=[
                item.knowledge_point_id for item in grades if item.correct
            ],
            focus_knowledge_point_ids=focus_ids,
            learning_blocks=learning_blocks,
        )

    def _learning_block(
        self,
        *,
        course_id: CourseId,
        knowledge_point_id: str,
        is_prerequisite_gap: bool,
    ) -> DiagnosticLearningBlock:
        detail = self._courses.get_knowledge_point(course_id, knowledge_point_id)
        lesson = detail.lesson
        worked_example = lesson.get("worked_example")
        example = worked_example if isinstance(worked_example, dict) else {}
        common_mistakes = self._string_list(lesson.get("common_mistakes"))
        return DiagnosticLearningBlock(
            block_id=f"diagnostic-block-{knowledge_point_id.lower()}",
            knowledge_point_id=knowledge_point_id,
            title=detail.title,
            reason=(
                "前置断层回补：保留你已经会的后续内容，只补这一块。"
                if is_prerequisite_gap
                else "客观测评未通过：安排短讲解、例题和一次验证。"
            ),
            estimated_minutes=max(6, min(18, detail.estimated_minutes // 3)),
            skill_atoms=list(self._skill_atoms(detail)),
            summary=str(lesson.get("summary") or detail.title),
            key_points=[
                *self._string_list(lesson.get("key_points")),
                *[f"易错提醒：{item}" for item in common_mistakes[:2]],
            ],
            example_problem=str(example.get("problem") or ""),
            example_steps=self._string_list(example.get("steps")),
            example_code=str(example.get("code") or ""),
        )

    @staticmethod
    def _skill_atoms(knowledge_point: Any) -> tuple[DiagnosticSkillAtom, ...]:
        atoms: list[DiagnosticSkillAtom] = []
        for label in knowledge_point.concepts:
            digest = hashlib.blake2s(
                f"{knowledge_point.id}:{label}".encode(), digest_size=4
            ).hexdigest()
            atoms.append(
                DiagnosticSkillAtom(
                    id=f"{knowledge_point.id}::{digest}",
                    knowledge_point_id=knowledge_point.id,
                    label=label,
                )
            )
        return tuple(atoms)

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _balanced_options(
        evaluation: dict[str, Any], item_index: int
    ) -> tuple[list[DiagnosticOption], set[str]]:
        raw_options = evaluation.get("options")
        accepted_answers = evaluation.get("accepted_answers")
        if not isinstance(raw_options, list) or not raw_options:
            raise ValueError("diagnostic options are incomplete")
        if not isinstance(accepted_answers, list) or not accepted_answers:
            raise ValueError("diagnostic answer key is incomplete")
        accepted_source_ids = {str(item) for item in accepted_answers}
        normalized = [DiagnosticOption.model_validate(option) for option in raw_options]
        correct = [option for option in normalized if option.id in accepted_source_ids]
        distractors = [option for option in normalized if option.id not in accepted_source_ids]
        if not correct:
            raise ValueError("diagnostic answer key does not reference a public option")

        target = min(
            _BALANCED_CORRECT_POSITIONS[item_index % len(_BALANCED_CORRECT_POSITIONS)],
            len(normalized) - 1,
        )
        ordered = list(distractors)
        ordered.insert(target, correct[0])
        ordered.extend(correct[1:])
        visible: list[DiagnosticOption] = []
        accepted_visible_ids: set[str] = set()
        for position, option in enumerate(ordered):
            visible_id = chr(ord("A") + position)
            visible.append(DiagnosticOption(id=visible_id, text=option.text))
            if option.id in accepted_source_ids:
                accepted_visible_ids.add(visible_id)
        return visible, accepted_visible_ids

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
