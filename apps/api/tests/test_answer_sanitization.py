"""Inline internal identifiers must never reach learner-facing answers."""

from __future__ import annotations

from app.modules.orchestration.supervisor import (
    QualitySupervisor,
    sanitize_answer_text,
)
from app.modules.orchestration.tutor import TutorDraft
from app.modules.rag.ports import SearchHit


def test_sanitizer_removes_inline_citation_phrases() -> None:
    text = (
        "对缺失值：应先判断缺失原因，再决定填充、删除或保留"
        "（证据 SRC-PY-GUIDE-DATA-005、SRC-PY-GUIDE-ENGINEERING-001）。"
    )
    cleaned = sanitize_answer_text(text)

    assert "SRC-" not in cleaned
    assert "证据" not in cleaned
    assert "对缺失值：应先判断缺失原因" in cleaned


def test_sanitizer_removes_bare_internal_ids() -> None:
    cleaned = sanitize_answer_text("参见 SRC-PY-GUIDE-DATA-007 与 PY-BASE-04 的内容。")

    assert cleaned == "参见 与 的内容。"


def test_sanitizer_keeps_normal_teaching_text() -> None:
    text = "列表是有序、可变容器，支持索引、切片、append 等操作。"
    assert sanitize_answer_text(text) == text


def test_inspect_sanitizes_draft_answers() -> None:
    hit = SearchHit(
        source_id="SRC-PY-GUIDE-DATA",
        chunk_id="source:SRC-PY-GUIDE-DATA:005:000000000000",
        content="数据清洗应保留异常记录。",
        score=0.6,
        metadata={},
    )
    draft = TutorDraft(
        answer="应保留异常记录（证据 SRC-PY-GUIDE-DATA-005）。",
        citation_chunk_ids=("source:SRC-PY-GUIDE-DATA:005:000000000000",),
        degraded=False,
    )

    result = QualitySupervisor().inspect(draft=draft, evidence=[hit])

    assert result.accepted is True
    assert "SRC-" not in result.answer
    assert result.answer == "应保留异常记录。"


def test_inspect_rejects_answers_that_are_only_internal_ids() -> None:
    hit = SearchHit(
        source_id="SRC-PY-GUIDE-DATA",
        chunk_id="source:SRC-PY-GUIDE-DATA:005:000000000000",
        content="数据清洗应保留异常记录。",
        score=0.6,
        metadata={},
    )
    draft = TutorDraft(
        answer="SRC-PY-GUIDE-DATA-005",
        citation_chunk_ids=("source:SRC-PY-GUIDE-DATA:005:000000000000",),
        degraded=False,
    )

    result = QualitySupervisor().inspect(draft=draft, evidence=[hit])

    assert result.accepted is False
    assert result.reason_code == "invalid_answer"
