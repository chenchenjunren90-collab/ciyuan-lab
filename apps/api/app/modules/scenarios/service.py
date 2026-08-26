"""Resolve a safe business context while preserving the computer-science focus."""

from __future__ import annotations

from typing import Literal

from app.modules.course_content import CoursePackRepository, CourseRecordNotFoundError
from app.modules.course_content.models import ActivityDetail, CourseId
from app.modules.model_adapters import ModelError
from app.modules.model_adapters.tuoling import (
    TuolingScenarioAdapter,
    TuolingScenarioRequest,
)
from app.modules.scenarios.models import ScenarioContext


class ScenarioUnavailableError(Exception):
    """The requested activity is not an authorized scenario project."""


class ScenarioContextService:
    def __init__(
        self,
        *,
        courses: CoursePackRepository,
        tuoling: TuolingScenarioAdapter | None,
    ) -> None:
        self._courses = courses
        self._tuoling = tuoling

    async def get_context(self, course_id: CourseId, project_id: str) -> ScenarioContext:
        try:
            project = self._courses.get_activity(course_id, project_id)
        except CourseRecordNotFoundError:
            raise
        if project.type != "project":
            raise ScenarioUnavailableError("activity is not a project")
        if project.scenario_scope != "post_course_finance_practice":
            raise ScenarioUnavailableError(
                "project is not an authorized post-course finance practice"
            )
        if project.data_classification not in {
            "public",
            "synthetic",
            "authorized_desensitized",
        }:
            raise ScenarioUnavailableError("project data classification is not authorized")

        if project.scenario_provider == "tuoling" and self._tuoling is not None:
            try:
                response = await self._tuoling.fetch_context(
                    TuolingScenarioRequest(
                        project_id=project.id,
                        course_id=course_id,
                        scenario_scope=project.scenario_scope,
                        data_classification=project.data_classification,
                        computer_science_objectives=project.computer_science_objectives,
                        business_context_objectives=project.business_context_objectives,
                    )
                )
            except ModelError:
                return self._fixed_context(course_id, project, "fallback")
            allowed_source_refs = set([*project.source_refs, *project.fallback_source_refs])
            verified_source_refs = [
                source_ref
                for source_ref in response.source_refs
                if source_ref in allowed_source_refs
            ]
            return ScenarioContext(
                project_id=project.id,
                course_id=course_id,
                mode="tuoling",
                provider_status="live",
                context=response.context,
                constraints=list(response.constraints) or project.requirements,
                source_refs=verified_source_refs or project.source_refs,
                data_classification=project.data_classification,
                notice=(
                    "驼灵仅补充脱敏经管背景与约束；编程目标、代码验证和评分规则仍由本平台确定。"
                ),
            )

        if project.scenario_provider == "tuoling":
            return self._fixed_context(course_id, project, "disabled")
        return self._fixed_context(course_id, project, "fallback")

    def _fixed_context(
        self,
        course_id: CourseId,
        project: ActivityDetail,
        provider_status: Literal["disabled", "fallback"],
    ) -> ScenarioContext:
        fallback_refs = project.fallback_source_refs or project.source_refs
        reviewed = {
            source.id: source
            for source in self._courses.list_rag_source_records(course_id)
            if source.id in fallback_refs
        }
        ordered = [reviewed[source_id] for source_id in fallback_refs if source_id in reviewed]
        if not ordered:
            raise ScenarioUnavailableError("project has no reviewed synthetic fallback")
        return ScenarioContext(
            project_id=project.id,
            course_id=course_id,
            mode="fixed_synthetic",
            provider_status=provider_status,
            context="\n\n".join(source.text for source in ordered),
            constraints=project.requirements,
            source_refs=[source.id for source in ordered],
            data_classification="synthetic",
            notice=(
                "当前使用固定合成背景，不含真实主体或经营结论；课程评价仅考查"
                "Python 数据处理、异常处理和测试能力。"
            ),
        )
