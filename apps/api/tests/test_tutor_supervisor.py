"""Tutor generation is always constrained by the deterministic supervisor."""

import asyncio
import json
from collections.abc import Sequence

import pytest

from app.modules.model_adapters import MockAdapter
from app.modules.model_adapters.ports import ChatMessage, ModelResponse
from app.modules.orchestration import CourseTutor, QualitySupervisor, TutorDraft
from app.modules.rag.ports import SearchHit


class FixedAdapter:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0
        self.last_messages: Sequence[ChatMessage] = ()

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        self.calls += 1
        self.last_messages = messages
        assert messages[0].role == "system"
        return ModelResponse(
            content=self.content,
            provider="fixed",
            model="test",
            usage={},
        )


class SequenceAdapter:
    def __init__(self, contents: Sequence[str]) -> None:
        self.contents = tuple(contents)
        self.calls = 0
        self.last_messages: Sequence[ChatMessage] = ()

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        self.last_messages = messages
        content = self.contents[min(self.calls, len(self.contents) - 1)]
        self.calls += 1
        return ModelResponse(content=content, provider="fixed", model="test", usage={})


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


def test_tutor_routes_only_python_course_to_the_optional_lora_adapter(
    evidence: tuple[SearchHit, ...],
) -> None:
    general = FixedAdapter(
        '{"answer":"通用模型回答。",'
        '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}'
    )
    python_tutor = FixedAdapter(
        '{"answer":"Python 垂类模型回答。",'
        '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}'
    )
    tutor = CourseTutor(general, python_model_adapter=python_tutor)

    python_draft = asyncio.run(
        tutor.draft(question="如何处理缺失值？", evidence=evidence, course_id="python")
    )
    other_draft = asyncio.run(
        tutor.draft(question="如何处理缺失值？", evidence=evidence, course_id="c")
    )

    assert python_draft.answer == "Python 垂类模型回答。"
    assert other_draft.answer == "通用模型回答。"
    assert python_tutor.calls == 1
    assert general.calls == 1


def test_tutor_accepts_one_complete_json_markdown_fence(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(
        FixedAdapter(
            '```json\n{"answer":"先确认字段约定，再标记缺失。",'
            '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}\n```'
        )
    )

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert draft.degraded is False
    assert draft.citation_chunk_ids == (evidence[0].chunk_id,)


def test_tutor_accepts_json_after_an_empty_qwen_thinking_marker(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(
        FixedAdapter(
            '<think>\n\n</think>\n\n{"answer":"先确认字段约定，再标记缺失。",'
            '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}'
        )
    )

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert draft.degraded is False
    assert draft.citation_chunk_ids == (evidence[0].chunk_id,)


def test_tutor_rejects_nonempty_thinking_before_json(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(
        FixedAdapter(
            '<think>此处内容不应由解析器静默丢弃。</think>'
            '{"answer":"先确认字段约定，再标记缺失。",'
            '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}'
        )
    )

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert draft.degraded is True


def test_tutor_repairs_invalid_maas_format_once(
    evidence: tuple[SearchHit, ...],
) -> None:
    adapter = SequenceAdapter(
        (
            "我先解释一下，再输出答案。",
            '{"answer":"先确认字段约定，再标记缺失。",'
            '"citation_chunk_ids":["SRC-PY-GUIDE-DATA-001-deadbeef00"]}',
        )
    )
    tutor = CourseTutor(adapter)

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert adapter.calls == 2
    assert adapter.last_messages[-2].role == "assistant"
    assert adapter.last_messages[-1].role == "user"
    assert draft.degraded is False
    assert draft.citation_chunk_ids == (evidence[0].chunk_id,)


def test_tutor_rejects_duplicate_keys_and_unknown_citations(
    evidence: tuple[SearchHit, ...],
) -> None:
    tutor = CourseTutor(
        FixedAdapter(
            '{"answer":"第一版","answer":"第二版",'
            '"citation_chunk_ids":["SRC-PY-FAKE"]}'
        )
    )

    draft = asyncio.run(tutor.draft(question="如何处理缺失值？", evidence=evidence))

    assert draft.degraded is True
    assert draft.citation_chunk_ids == (evidence[0].chunk_id,)


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


def test_model_supervisor_approves_only_after_rules(
    evidence: tuple[SearchHit, ...],
) -> None:
    adapter = FixedAdapter('{"approved":true,"reason_code":"approved"}')
    supervisor = QualitySupervisor(adapter)
    draft = TutorDraft(
        answer="先确认字段约定，再标记缺失。",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = asyncio.run(
        supervisor.review(
            draft=draft,
            evidence=evidence,
            learning_context="Python 数据清洗初学课堂",
            student_question="缺失值应该怎样处理？",
            role="ta",
            phase="practice",
        )
    )

    assert decision.accepted is True
    assert decision.model_reviewed is True
    assert decision.model_degraded is False
    assert adapter.calls == 1
    payload = json.loads(adapter.last_messages[1].content)
    assert payload["student_question"] == "缺失值应该怎样处理？"
    assert payload["role"] == "ta"
    assert payload["phase"] == "practice"
    assert "仅当 phase 为 debug、practice 或 homework" in adapter.last_messages[0].content


def test_model_supervisor_can_block_semantically_unsupported_answer(
    evidence: tuple[SearchHit, ...],
) -> None:
    supervisor = QualitySupervisor(
        FixedAdapter('{"approved":false,"reason_code":"unsupported_claim"}')
    )
    draft = TutorDraft(
        answer="先确认字段约定，再标记缺失。",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = asyncio.run(supervisor.review(draft=draft, evidence=evidence))

    assert decision.accepted is False
    assert decision.reason_code == "semantic_unsupported_claim"
    assert decision.model_reviewed is True


def test_invalid_model_verdict_degrades_to_non_bypassable_rules(
    evidence: tuple[SearchHit, ...],
) -> None:
    supervisor = QualitySupervisor(FixedAdapter("不是合法 JSON"))
    draft = TutorDraft(
        answer="先确认字段约定，再标记缺失。",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = asyncio.run(supervisor.review(draft=draft, evidence=evidence))

    assert decision.accepted is False
    assert decision.model_reviewed is False
    assert decision.model_degraded is True
    assert decision.reason_code == "semantic_invalid_verdict"


@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"approved":false,"reason_code":"unsafe_guidance"}\n```',
        '```\n{"approved":false,"reason_code":"question_mismatch"}\n```',
    ],
)
def test_fenced_semantic_rejection_is_never_reversed_to_approval(
    evidence: tuple[SearchHit, ...],
    content: str,
) -> None:
    supervisor = QualitySupervisor(FixedAdapter(content))
    draft = TutorDraft(
        answer="先确认字段约定，再标记缺失。",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = asyncio.run(supervisor.review(draft=draft, evidence=evidence))

    assert decision.accepted is False
    assert decision.model_reviewed is True


@pytest.mark.parametrize("reason_code", [None, 7, [], {}])
def test_invalid_reason_code_types_do_not_raise_or_release_answer(
    evidence: tuple[SearchHit, ...],
    reason_code: object,
) -> None:
    content = json.dumps({"approved": False, "reason_code": reason_code})
    supervisor = QualitySupervisor(FixedAdapter(content))
    draft = TutorDraft(
        answer="先确认字段约定，再标记缺失。",
        citation_chunk_ids=(evidence[0].chunk_id,),
        degraded=False,
    )

    decision = asyncio.run(supervisor.review(draft=draft, evidence=evidence))

    assert decision.accepted is False
    assert decision.reason_code == "semantic_invalid_verdict"


def test_rule_rejection_never_calls_model(
    evidence: tuple[SearchHit, ...],
) -> None:
    adapter = FixedAdapter('{"approved":true,"reason_code":"approved"}')
    supervisor = QualitySupervisor(adapter)
    draft = TutorDraft(
        answer="看似合理但引用不存在。",
        citation_chunk_ids=("SRC-PY-FAKE-001",),
        degraded=False,
    )

    decision = asyncio.run(supervisor.review(draft=draft, evidence=evidence))

    assert decision.accepted is False
    assert decision.reason_code == "fabricated_citation"
    assert adapter.calls == 0
