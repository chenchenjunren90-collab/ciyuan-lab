"""Vocabulary expansion must preserve the student's words and course isolation."""

import asyncio
from pathlib import Path

import pytest

from app.modules.course_content import CoursePackRepository
from app.modules.rag.evaluation import evaluate_retriever, load_eval_cases
from app.modules.rag.retriever import (
    LexicalKnowledgeRetriever,
    query_is_in_course_scope,
    query_variants,
)


@pytest.mark.parametrize("alias", ["二分搜索", "折半查找"])
def test_binary_search_alias_preserves_question_and_scope(alias: str) -> None:
    question = f"{alias}开始前需要满足什么有序条件？"
    variants = query_variants(question)
    assert variants[0] == question
    assert any("二分查找" in variant for variant in variants)
    assert query_is_in_course_scope(question, "data_structures")
    assert not query_is_in_course_scope(question, "c")


def test_unrelated_question_is_not_expanded_into_course_terms() -> None:
    assert query_variants("明天的天气如何") == ("明天的天气如何",)
    assert query_variants("哈希表冲突")[:2] == ("哈希表冲突", "散列表冲突")


def test_foundation_boundary_dataset_retrieves_reviewed_sources_and_rejects_off_topic() -> None:
    root = Path(__file__).resolve().parents[3]
    cases = load_eval_cases(root / "evals/rag/foundation-boundaries-v1.jsonl")
    retriever = LexicalKnowledgeRetriever.from_repository(CoursePackRepository())
    result = asyncio.run(evaluate_retriever(retriever, cases))
    assert result.recall_at_k == 1.0
    assert result.course_isolation_rate == 1.0
    assert result.unanswerable_rejection_rate == 1.0
    assert result.cross_course_rejection_rate == 1.0
