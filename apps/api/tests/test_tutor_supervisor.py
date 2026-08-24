"""Tutor generation is always constrained by the deterministic supervisor."""

import asyncio
from collections.abc import Sequence

import pytest

from app.modules.model_adapters import MockAdapter
from app.modules.model_adapters.ports import ChatMessage, ModelResponse
from app.modules.orchestration import CourseTutor, QualitySupervisor, TutorDraft
from app.modules.rag.ports import SearchHit


class FixedAdapter:
    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        assert messages[0].role == "system"
        return ModelResponse(
            content=self.content,
            provider="fixed",
            model="test",
            usage={},
        )


@pytest.fixture
def evidence() -> tuple[SearchHit, ...]:
    return (
        SearchHit(
            source_id="SRC-PY-GUIDE-DATA",
            chunk_id="SRC-PY-GUIDE-DATA-001-deadbeef00",
            content="数据处理先确认字段和缺失约定，再执行解析与校验。",
            score=0.5,
            metadata={},
        ),
    )


def test_mock_model_degrades_to_cited_evidence(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(MockAdapter())

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))
    decision = QualitySupervisor().inspect(draft=draft, evidence=evidence)

    assert draft.degraded is True
    assert decision.accepted is True
    assert decision.citations[0].source_id == "SRC-PY-GUIDE-DATA"


def test_tutor_accepts_only_structured_model_output(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(
        FixedAdapter(
            '{"answer":"先确认字段约定，再标记缺失。",'
            '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}'
        )
    )

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert draft.degraded is False
    assert QualitySupervisor().inspect(draft=draft, evidence=evidence).accepted is True


def test_supervisor_rejects_fabricated_citation(
    evidence: tuple[SearchHit, ...],
) -> None:
    draft = TutorDraft(
        answer="这是一个看似合理的回答。",
        citation_chunk_ids=("SRC-PY-FAKE-001",),
        degraded=False,
    )

    decision = QualitySupervisor().inspect(draft=draft, evidence=evidence)

    assert decision.accepted is False
    assert decision.reason_code == "fabricated_citation"


def test_supervisor_rejects_secret_shaped_content(
    evidence: tuple[SearchHit, ...],
) -> None:
    draft = TutorDraft(
        answer="API_KEY=should-not-appear",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = QualitySupervisor().inspect(draft=draft, evidence=evidence)

    assert decision.accepted is False
    assert decision.reason_code == "unsafe_content"
