from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import scenarios as scenarios_api
from app.main import app
from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters import ChatMessage, MockAdapter, ModelResponse
from app.modules.scenarios import ScenarioProjectGenerator, ScenarioProjectNeed


def _need() -> ScenarioProjectNeed:
    return ScenarioProjectNeed(
        course_id="python",
        template_project_id="PY-PROJ-BANK-MARKETING-01",
        learner_goal="练习字典分组、文件解析和异常记录",
        target_concept_ids=["PY-DICT-02", "PY-FILE-03"],
        difficulty="intermediate",
        estimated_minutes=120,
    )


class ValidModel:
    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        joined = "\n".join(message.content for message in messages)
        assert "student_id" not in joined
        assert "所有主体、编号、时间和数值均为虚构" in joined
        return ModelResponse(
            content=(
                '{"title":"虚构活动记录分组统计","scenario_context":"某虚构教学机构提供固定生成的活动记录，'
                '学生需要完成解析、去重、统计和限制说明，全部编号与数值均不对应真实主体。",'
                '"tasks":["校验记录字段并保留错误原因","按渠道和分群计算响应统计"],'
                '"constraints":["不得加入真实个人信息","不得生成个体营销建议"],'
                '"deliverables":["Python程序","自动化测试"],'
                '"source_refs":["SRC-PY-SYNTHETIC-FINANCE-CATALOG"]}'
            ),
            provider="xfyun-maas",
            model="xopdeepseekv4flash0731",
            usage={},
        )


class InvalidCitationModel:
    async def complete(self, _messages: Sequence[ChatMessage]) -> ModelResponse:
        return ModelResponse(
            content=(
                '{"title":"无效来源项目","scenario_context":"这是一个长度足够但包含未登记来源的固定合成教学场景。",'
                '"tasks":["任务一","任务二"],"constraints":["限制一","限制二"],'
                '"deliverables":["程序"],"source_refs":["FAKE-SOURCE"]}'
            ),
            provider="xfyun-maas",
            model="xopdeepseekv4flash0731",
            usage={},
        )


def test_generator_accepts_constrained_model_output() -> None:
    generator = ScenarioProjectGenerator(courses=CoursePackRepository(), model=ValidModel())
    result = asyncio.run(generator.generate(_need()))

    assert result.degraded is False
    assert result.provider == "xfyun-maas"
    assert result.data_classification == "synthetic"
    assert result.source_refs == ["SRC-PY-SYNTHETIC-FINANCE-CATALOG"]
    assert result.computer_science_objectives
    assert "AI生成" in result.ai_generated_notice
    assert result.dataset.filename.endswith("-synthetic.json")
    assert result.dataset.sha256
    assert all("SYN-" in str(row) for row in result.dataset.rows)


def test_generator_falls_back_when_model_invents_a_source() -> None:
    generator = ScenarioProjectGenerator(
        courses=CoursePackRepository(), model=InvalidCitationModel()
    )
    result = asyncio.run(generator.generate(_need()))

    assert result.degraded is True
    assert result.provider == "fallback"
    assert "FAKE-SOURCE" not in result.source_refs


def test_generator_falls_back_without_model_credentials() -> None:
    generator = ScenarioProjectGenerator(courses=CoursePackRepository(), model=MockAdapter())
    result = asyncio.run(generator.generate(_need()))

    assert result.degraded is True
    assert result.provider == "mock"
    assert "固定合成" in result.ai_generated_notice
    assert _need().learner_goal in result.scenario_context
    assert "PY-DICT-02" in result.tasks[0]
    assert "120 分钟" in result.constraints[1]


@pytest.mark.parametrize(
    "goal",
    [
        "用手机号13800138000练习数据校验",
        "把结果发到student@example.com",
        "姓名是张三，练习字典分组",
        "学号是2026123456，练习文件处理",
        "API_KEY=should-not-leave-the-service",
    ],
)
def test_need_rejects_identity_and_credential_values(goal: str) -> None:
    with pytest.raises(ValidationError, match="identity or credential"):
        ScenarioProjectNeed(
            course_id="python",
            template_project_id="PY-PROJ-BANK-MARKETING-01",
            learner_goal=goal,
            target_concept_ids=["PY-DICT-02"],
            difficulty="intermediate",
            estimated_minutes=120,
        )


def test_generation_endpoint_returns_fixed_dataset_without_credentials(
    monkeypatch: object,
) -> None:
    generator = ScenarioProjectGenerator(courses=CoursePackRepository(), model=MockAdapter())
    monkeypatch.setattr(  # type: ignore[attr-defined]
        scenarios_api, "get_scenario_project_generator", lambda: generator
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/courses/python/scenario-projects/generate",
            json=_need().model_dump(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert payload["data_classification"] == "synthetic"
    assert payload["dataset"]["rows"]
    assert payload["dataset"]["sha256"]
