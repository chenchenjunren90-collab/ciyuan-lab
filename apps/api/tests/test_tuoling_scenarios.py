from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters.errors import ModelUpstreamError
from app.modules.model_adapters.tuoling import (
    TuolingScenarioAdapter,
    TuolingScenarioRequest,
)
from app.modules.scenarios import ScenarioContextService


def _request() -> TuolingScenarioRequest:
    return TuolingScenarioRequest(
        project_id="PY-PROJ-FINANCE-DATA-01",
        course_id="python",
        scenario_scope="post_course_finance_practice",
        data_classification="authorized_desensitized",
        computer_science_objectives=("实现可测试的数据管道",),
        business_context_objectives=("理解字段约束",),
    )


def test_tuoling_adapter_sends_only_project_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.read().decode())
        assert payload["scenario_scope"] == "post_course_finance_practice"
        assert "student_id" not in payload
        assert "source_code" not in payload
        return httpx.Response(
            200,
            json={
                "data": {
                    "context": "使用已授权脱敏经营记录完成数据质量分析。",
                    "constraints": ["不得推断真实经营主体"],
                    "source_refs": ["TUOLING-CASE-001"],
                }
            },
        )

    async def scenario() -> tuple[str, tuple[str, ...]]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0) as client:
            adapter = TuolingScenarioAdapter(
                base_url="https://tuoling.example.edu",
                api_key="test-key",
                client=client,
            )
            result = await adapter.fetch_context(_request())
            return result.context, result.source_refs

    context, source_refs = asyncio.run(scenario())
    assert "脱敏经营记录" in context
    assert source_refs == ("TUOLING-CASE-001",)


def test_scenario_endpoint_uses_reviewed_fixed_fallback_when_disabled() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/courses/python/projects/PY-PROJ-FINANCE-DATA-01/scenario")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fixed_synthetic"
    assert payload["provider_status"] == "disabled"
    assert payload["data_classification"] == "synthetic"
    assert payload["source_refs"] == ["SRC-PY-GUIDE-CASE-FALLBACK"]
    assert "所有主体与数值均为虚构" in payload["context"]


def test_scenario_endpoint_rejects_non_finance_project() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/courses/c/projects/C-PROJ-RECORD-01/scenario")

    assert response.status_code == 422
    assert "not an authorized" in response.json()["detail"]


def test_tuoling_adapter_rejects_oversized_context() -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"context": "x" * 8_001})
            )
        ) as client:
            adapter = TuolingScenarioAdapter(
                base_url="https://tuoling.example.edu",
                api_key="test-key",
                client=client,
            )
            await adapter.fetch_context(_request())

    with pytest.raises(ModelUpstreamError, match="size limit"):
        asyncio.run(scenario())


def test_scenario_service_filters_unregistered_provider_source_ids() -> None:
    class FakeTuoling:
        async def fetch_context(self, _request: object) -> object:
            from app.modules.model_adapters.tuoling import TuolingScenarioResponse

            return TuolingScenarioResponse(
                context="已授权脱敏场景",
                constraints=("仅用于编程练习",),
                source_refs=("UNREGISTERED-SOURCE", "SRC-PY-GUIDE-DATA"),
            )

    result = asyncio.run(
        ScenarioContextService(
            courses=CoursePackRepository(),
            tuoling=FakeTuoling(),  # type: ignore[arg-type]
        ).get_context("python", "PY-PROJ-FINANCE-DATA-01")
    )

    assert result.source_refs == ["SRC-PY-GUIDE-DATA"]
