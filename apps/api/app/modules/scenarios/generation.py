"""Constrained generation of post-course synthetic finance projects."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.modules.course_content import CoursePackRepository
from app.modules.course_content.models import ActivityDetail, CourseId, Difficulty
from app.modules.model_adapters import ChatMessage, ModelAdapter, ModelError
from app.modules.scenarios.fixtures import SyntheticScenarioDataset, build_synthetic_dataset


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioProjectNeed(StrictModel):
    """Non-identifying learner requirements allowed to leave the platform."""

    course_id: CourseId
    template_project_id: str = Field(min_length=1, max_length=128)
    learner_goal: str = Field(min_length=5, max_length=500)
    target_concept_ids: list[str] = Field(min_length=1, max_length=8)
    difficulty: Difficulty
    estimated_minutes: int = Field(ge=30, le=480)

    @field_validator("learner_goal")
    @classmethod
    def reject_sensitive_values(cls, value: str) -> str:
        patterns = (
            r"(?<!\d)1[3-9]\d{9}(?!\d)",
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            r"(?<!\d)\d{17}[\dXx](?!\w)",
            r"(?:我叫|我的名字是|姓名是)\s*[\u4e00-\u9fff]{2,4}",
            r"学号(?:是|[:：])?\s*[A-Za-z0-9]{5,}",
            r"(?:api[_ -]?key|password|密钥)\s*[:：=]\s*\S+",
        )
        if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns):
            raise ValueError("learner_goal must not contain identity or credential values")
        return value.strip()


class GeneratedScenarioProject(StrictModel):
    title: str = Field(min_length=2, max_length=80)
    scenario_context: str = Field(min_length=30, max_length=2_000)
    tasks: list[str] = Field(min_length=2, max_length=8)
    constraints: list[str] = Field(min_length=2, max_length=10)
    deliverables: list[str] = Field(min_length=1, max_length=8)
    source_refs: list[str] = Field(min_length=1, max_length=10)
    computer_science_objectives: list[str] = Field(min_length=1, max_length=8)
    data_classification: Literal["synthetic"] = "synthetic"
    ai_generated_notice: str
    provider: str
    model: str
    degraded: bool
    dataset: SyntheticScenarioDataset


class _ModelScenarioDraft(StrictModel):
    title: str = Field(min_length=2, max_length=80)
    scenario_context: str = Field(min_length=30, max_length=2_000)
    tasks: list[str] = Field(min_length=2, max_length=8)
    constraints: list[str] = Field(min_length=2, max_length=10)
    deliverables: list[str] = Field(min_length=1, max_length=8)
    source_refs: list[str] = Field(min_length=1, max_length=10)


_FORBIDDEN_GENERATED_MARKERS = (
    "真实姓名",
    "身份证号",
    "手机号码",
    "家庭住址",
    "银行卡号",
    "参考答案",
    "```",
)


class ScenarioProjectGenerator:
    """Let a model vary wording and task depth inside a reviewed template."""

    def __init__(self, *, courses: CoursePackRepository, model: ModelAdapter) -> None:
        self._courses = courses
        self._model = model

    async def generate(self, need: ScenarioProjectNeed) -> GeneratedScenarioProject:
        project = self._courses.get_activity(need.course_id, need.template_project_id)
        self._validate_template(need, project)
        messages = self._messages(need, project)
        try:
            response = await self._model.complete(messages)
            if response.provider == "mock":
                return self._fallback(need, project, provider="mock", model=response.model)
            draft = _ModelScenarioDraft.model_validate_json(response.content)
            self._validate_draft(draft, set(project.source_refs))
        except (ModelError, ValidationError, ValueError, json.JSONDecodeError):
            return self._fallback(need, project, provider="fallback", model="fixed")

        return GeneratedScenarioProject(
            **draft.model_dump(),
            computer_science_objectives=project.computer_science_objectives,
            data_classification="synthetic",
            ai_generated_notice=(
                "AI生成的合成教学场景，仅用于计算机课程练习；主体与数值均为虚构，"
                "不得用于真实金融、信用、营销或合规判断。"
            ),
            provider=response.provider,
            model=response.model,
            degraded=False,
            dataset=build_synthetic_dataset(project.id),
        )

    @staticmethod
    def _validate_template(need: ScenarioProjectNeed, project: ActivityDetail) -> None:
        if project.type != "project":
            raise ValueError("template activity must be a project")
        if project.scenario_scope != "post_course_finance_practice":
            raise ValueError("template is not a post-course finance project")
        if project.scenario_provider != "fixed_synthetic":
            raise ValueError("template must use the fixed synthetic provider")
        if project.data_classification != "synthetic":
            raise ValueError("template must be classified as synthetic")
        unknown = sorted(set(need.target_concept_ids) - set(project.concept_ids))
        if unknown:
            raise ValueError(f"target concepts are outside the template: {', '.join(unknown)}")

    @staticmethod
    def _messages(need: ScenarioProjectNeed, project: ActivityDetail) -> tuple[ChatMessage, ...]:
        system = (
            "你是计算机课程综合项目编排器。只能改写给定的固定合成场景，不得引入真实主体、"
            "个人信息、投资建议、信用结论或未登记来源；不得给出参考答案或完整代码。"
            "计算机知识目标不可更改。只返回JSON，字段必须且只能是title、scenario_context、"
            "tasks、constraints、deliverables、source_refs。source_refs只能从模板列表中选择。"
        )
        payload = {
            "learner_need": need.model_dump(),
            "template": {
                "title": project.title,
                "summary": project.summary,
                "requirements": project.requirements,
                "deliverables": project.deliverables,
                "source_refs": project.source_refs,
                "computer_science_objectives": project.computer_science_objectives,
                "business_context_objectives": project.business_context_objectives,
            },
            "required_boundaries": [
                "所有主体、编号、时间和数值均为虚构",
                "项目评价以程序、算法、测试和可追溯性为核心",
                "不输出答案代码，不作真实金融或经营判断",
            ],
        }
        return (
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
        )

    @staticmethod
    def _validate_draft(draft: _ModelScenarioDraft, allowed_source_refs: set[str]) -> None:
        if not set(draft.source_refs).issubset(allowed_source_refs):
            raise ValueError("model returned an unregistered source reference")
        combined = "\n".join(
            [draft.title, draft.scenario_context, *draft.tasks, *draft.constraints]
        )
        if any(marker in combined for marker in _FORBIDDEN_GENERATED_MARKERS):
            raise ValueError("model returned forbidden content")

    @staticmethod
    def _fallback(
        need: ScenarioProjectNeed,
        project: ActivityDetail,
        *,
        provider: str,
        model: str,
    ) -> GeneratedScenarioProject:
        difficulty_constraint = {
            "beginner": "按基础难度完成，优先保证输入校验、核心流程与正常用例。",
            "intermediate": "按进阶难度完成，覆盖正常、边界、重复与非法输入。",
            "advanced": "按拓展难度完成，增加复杂度分析、模块边界和系统化异常测试。",
        }[need.difficulty]
        return GeneratedScenarioProject(
            title=project.title,
            scenario_context=(
                f"{project.summary} 所有主体、编号、时间和数值均由固定规则生成，"
                f"不对应任何真实个人或机构。本次学习目标：{need.learner_goal}"
            ),
            tasks=[
                f"优先练习知识点：{', '.join(need.target_concept_ids)}。",
                *project.requirements,
            ],
            constraints=[
                difficulty_constraint,
                f"建议在 {need.estimated_minutes} 分钟内完成并记录测试证据。",
                "不得加入姓名、联系方式、地址、证件号或真实账号。",
                "不得把练习结果解释为真实金融、信用、营销或合规结论。",
                "必须使用确定性测试验证程序结果。",
            ],
            deliverables=project.deliverables,
            source_refs=project.source_refs,
            computer_science_objectives=project.computer_science_objectives,
            data_classification="synthetic",
            ai_generated_notice=(
                "当前使用固定合成教学场景；未调用外部模型，不含真实主体或经营结论。"
            ),
            provider=provider,
            model=model,
            degraded=True,
            dataset=build_synthetic_dataset(project.id),
        )
