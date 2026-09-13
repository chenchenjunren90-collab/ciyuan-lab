"""Progressive, answer-safe hints derived from versioned course content."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.course_content import CourseId, CoursePackRepository
from app.modules.learning_flow.service import LearningStore


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


DiagnosticText = Annotated[str, Field(min_length=1, max_length=500)]


class HintRequest(StrictModel):
    student_id: str = Field(min_length=1, max_length=128)
    level: Literal[1, 2, 3]
    source_code: str = Field(default="", max_length=8000)
    diagnostics: list[DiagnosticText] = Field(default_factory=list, max_length=8)
    passed_tests: int | None = Field(default=None, ge=0, le=1000)
    total_tests: int | None = Field(default=None, ge=0, le=1000)


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
        source_code: str = "",
        diagnostics: list[str] | None = None,
        passed_tests: int | None = None,
        total_tests: int | None = None,
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
        verification_diagnostics = [item[:500] for item in (diagnostics or []) if item.strip()]
        if not activity.concept_ids:
            hint = self._hint_text(
                activity,
                {},
                level,
                source_code=source_code,
                diagnostics=verification_diagnostics,
                passed_tests=passed_tests,
                total_tests=total_tests,
            )
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
        hint = self._hint_text(
            activity,
            focus.lesson,
            level,
            source_code=source_code,
            diagnostics=verification_diagnostics,
            passed_tests=passed_tests,
            total_tests=total_tests,
        )
        return HintResponse(
            activity_id=activity_id,
            level=level,
            hint=hint,
            focus_concept_ids=[focus.id],
            source_refs=list(dict.fromkeys([*activity.source_refs, *focus.source_refs])),
            answer_revealed=False,
        )

    @staticmethod
    def _hint_text(
        activity: object,
        lesson: dict[str, object],
        level: int,
        *,
        source_code: str = "",
        diagnostics: list[str] | None = None,
        passed_tests: int | None = None,
        total_tests: int | None = None,
    ) -> str:
        debug_hint = ProgressiveHintService._debug_hint(
            activity=activity,
            source_code=source_code,
            diagnostics=diagnostics or [],
            passed_tests=passed_tests,
            total_tests=total_tests,
            level=level,
        )
        if debug_hint:
            return debug_hint

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
    def _debug_hint(
        *,
        activity: object,
        source_code: str,
        diagnostics: list[str],
        passed_tests: int | None,
        total_tests: int | None,
        level: int,
    ) -> str | None:
        """Hand deterministic verifier facts to the TA without exposing hidden cases."""

        if not diagnostics or any("验证服务暂不可用" in item for item in diagnostics):
            return None
        report = "；".join(diagnostics)
        prompt = str(getattr(activity, "prompt", "") or "")
        score = (
            f"当前 {passed_tests}/{total_tests} 项测试通过。"
            if passed_tests is not None and total_tests
            else ""
        )

        if "公开测试" in report and "期望" in report and "实际" in report:
            if "你好， " in report and "你好，" in report:
                return (
                    f"{score}先逐字比较公开测试的期望与实际：中文逗号后多了一个空格。"
                    "只检查负责拼接问候语的那一行，先让公开样例完全一致，再处理隐藏边界。"
                )
            return (
                f"{score}先只看第一条公开测试反馈：{diagnostics[0]}。"
                "从第一个不同的字符开始检查输出格式，不要同时改动输入处理和核心逻辑。"
            )

        hidden_failed = any("隐藏测试未通过" in item for item in diagnostics)
        strip_required = "首尾空格" in prompt or "两侧可能有空格" in prompt
        if hidden_failed and strip_required and ".strip(" not in source_code.replace(" ", ""):
            return (
                f"{score}公开样例已经通过，差异只出现在隐藏边界。题面说明姓名两侧可能有空格；"
                "检查 input() 读到的字符串是否在参与格式化前去掉了首尾空格。"
                + (
                    "先只改读取后的清洗步骤再提交。"
                    if level == 1
                    else "再用带前后空格的名字自行验证。"
                )
            )

        if any("运行错误" in item or "SyntaxError" in item for item in diagnostics):
            return (
                f"{score}先处理运行错误，不要猜隐藏测试。第一条可见诊断是：{diagnostics[0]}。"
                "定位诊断指向的语句，修复后先确认程序能够启动，再核对输出。"
            )

        return (
            f"{score}助教已接到代码验证结果：{diagnostics[0]}。"
            "先围绕这条已知失败定位一个最小改动；隐藏测试的输入和答案不会被推测或泄露。"
        )

    @staticmethod
    def _strings(value: object) -> list[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
