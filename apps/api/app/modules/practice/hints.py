"""Progressive, answer-safe hints derived from versioned course content."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learning_flow.service import LearningStore


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HintRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    level: Literal[1, 2, 3]


class HintResponse(StrictModel):
    activity_id: str
    level: Literal[1, 2, 3]
    hint: str
    focus_concept_ids: list[str]
    source_refs: list[str]
    answer_revealed: bool = False


class ProgressiveHintService:
    def __init__(self, *, courses: CoursePackRepository, repository: LearningStore) -> None:
        self._courses = courses
        self._repository = repository

    def create_hint(
        self,
        *,
        student_id: str,
        course_id: CourseId,
        activity_id: str,
        level: Literal[1, 2, 3],
    ) -> HintResponse:
        activity = self._courses.get_activity(course_id, activity_id)
        concepts = [
            self._courses.get_knowledge_point(course_id, concept_id)
            for concept_id in activity.concept_ids
        ]
        profile = self._repository.get_profile(student_id=student_id, course_id=course_id)
        mastery = {
            item.knowledge_point_id: item.score for item in (profile.mastery if profile else [])
        }
        if not activity.concept_ids:
            hint = self._hint_text(activity, {}, level)
            return HintResponse(
                activity_id=activity_id,
                level=level,
                hint=hint,
                focus_concept_ids=[],
                source_refs=list(dict.fromkeys(activity.source_refs)),
                answer_revealed=False,
            )
        weakest = min(activity.concept_ids, key=lambda item: mastery.get(item, 0.5))
        focus = next((item for item in concepts if item.id == weakest), concepts[0])
        hint = self._hint_text(activity, focus.lesson, level)
        return HintResponse(
            activity_id=activity_id,
            level=level,
            hint=hint,
            focus_concept_ids=[focus.id],
            source_refs=list(dict.fromkeys([*activity.source_refs, *focus.source_refs])),
            answer_revealed=False,
        )

    @staticmethod
    def _hint_text(activity: object, lesson: dict[str, object], level: int) -> str:
        learning_objectives = getattr(activity, "computer_science_objectives", [])
        requirements = getattr(activity, "requirements", [])
        deliverables = getattr(activity, "deliverables", [])
        if getattr(activity, "type", None) == "project":
            if level == 1:
                focus = learning_objectives[0] if learning_objectives else "先明确输入、输出和约束"
                return f"先不要急着编码。把项目拆成可验证的小目标，第一项关注：{focus}。"
            if level == 2:
                requirement = requirements[0] if requirements else "列出正常、边界和错误输入"
                return (
                    "建立最小闭环：读取一条输入、完成一次处理、输出可检查结果。"
                    f"约束提示：{requirement}。"
                )
            deliverable = deliverables[0] if deliverables else "代码、测试证据和结果说明"
            return (
                "按‘输入校验→核心逻辑→异常处理→测试证据’逐段自查；"
                f"先确保交付物完整：{deliverable}。"
            )

        key_points = ProgressiveHintService._strings(lesson.get("key_points"))
        mistakes = ProgressiveHintService._strings(lesson.get("common_mistakes"))
        if level == 1:
            focus = key_points[0] if key_points else "回到题目输入、输出和边界"
            return f"先判断这道题主要考查什么。聚焦条件与适用范围：{focus}。"
        if level == 2:
            risk = mistakes[0] if mistakes else "空输入、边界值和类型不匹配"
            return f"构造一个最小样例并手工走一遍状态变化。特别排查：{risk}。"
        return (
            "把失败现象固定下来，再依次检查：输入是否满足前提、每一步状态是否"
            "符合预期、输出格式是否精确；只修改一个假设后重新验证。"
        )

    @staticmethod
    def _strings(value: object) -> list[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
