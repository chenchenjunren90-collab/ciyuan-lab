"""Partial retrieval should supplement, while complete evidence avoids web I/O."""

import asyncio
import json
from collections.abc import Sequence

import httpx
import pytest

from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters.ports import ChatMessage, ModelResponse
from app.modules.orchestration.classroom import (
    ClassroomDialogueRequest,
    ClassroomDialogueService,
    _deterministic_evidence_gap,
    _outline_only_definition,
)
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.ports import SearchHit
from app.modules.rag.python_docs import PythonOfficialDocsRetriever

LOCAL = SearchHit(
    source_id="SRC-PY-CONTROL", chunk_id="control-stage", score=.82,
    content="Python 控制流阶段目标：能处理边界的短代码。",
    metadata={"title": "Python 控制流阶段目标"},
)


class LocalRetriever:
    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        return (LOCAL,)


class Adapter:
    def __init__(self, verdict: object) -> None:
        self.verdict = verdict
        self.coverage_calls = 0
        self.tutor_evidence: list[dict[str, object]] = []

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        if "证据覆盖检查" in messages[0].content:
            self.coverage_calls += 1
            data = self.verdict
        elif "质量监督智能体" in messages[0].content:
            data = {"approved": True, "reason_code": "approved"}
        else:
            self.tutor_evidence = json.loads(messages[-1].content)["evidence"]
            ids = [hit["chunk_id"] for hit in self.tutor_evidence]
            data = {"answer": "在这节编程课里，边界控制指检查索引和循环的起止条件，避免越界。"
                    "例如 range 的终点不包含在序列中。", "citation_chunk_ids": ids}
        return ModelResponse(content=json.dumps(data, ensure_ascii=False),
                             provider="test-fixture", model="fixture", usage={})


PARTIAL = {"in_scope": True, "sufficient": False,
           "search_query": "Python range 端点 索引越界 IndexError"}


def test_boundary_search_prefers_rules_over_signatures_and_one_line_examples() -> None:
    retriever = PythonOfficialDocsRetriever()
    rule = "生成的序列绝不会包括给定的终止值；range(10) 生成长度为10的序列的所有合法索引。"
    ranked = retriever._rank_blocks("Python range 端点 索引越界 IndexError", [
        "class range ( start , stop [ , step ] )", ">>> range ( 10 ) range(0, 10)", rule,
    ])
    assert ranked[0][1] == rule


def test_outline_gate_does_not_override_explanations_or_non_definition_questions() -> None:
    explanation = SearchHit(
        source_id="SRC-PY-RANGE", chunk_id="range-rule", score=.8,
        content="range(5) 不包含终点，生成0到4。例如用于逐一访问列表的合法索引。",
        metadata={"title": "循环解释"},
    )
    assert _outline_only_definition("边界控制是什么", [LOCAL])
    assert not _outline_only_definition("range是什么", [LOCAL, explanation])
    assert not _outline_only_definition("range是什么", [explanation])
    assert not _outline_only_definition("给我代码示例", [LOCAL])


@pytest.mark.parametrize("verdict,expect_web", [
    (PARTIAL, True),
    ({"in_scope": True, "sufficient": True, "search_query": ""}, True),
    ({"in_scope": False, "sufficient": False, "search_query": ""}, True),
    ({"in_scope": "true", "sufficient": False, "search_query": "Python"}, True),
    ({"in_scope": True, "sufficient": False, "search_query": "https://evil.test"}, True),
    ({"in_scope": True, "sufficient": False, "search_query": ""}, True),
])
def test_coverage_advice_controls_supplement_not_answer_release(
    verdict: object, expect_web: bool,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        assert request.url.host == "docs.python.org"
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<p>Python 的 range 序列不包含终点；索引超出范围时会产生 IndexError 异常。</p>"
        ))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = Adapter(verdict)
            service = ClassroomDialogueService(
                courses=CoursePackRepository(), retriever=LocalRetriever(),
                online_retriever=PythonOfficialDocsRetriever(client=client, max_pages=1),
                tutor=CourseTutor(adapter), supervisor=QualitySupervisor(adapter),
            )
            result = await service.answer(ClassroomDialogueRequest(
                student_id="synthetic-partial-evidence", lesson_id="python-list-filter-01",
                phase="concept", role="teacher", message="边界控制是什么",
            ))
            assert bool(calls) == expect_web
            assert adapter.coverage_calls == 1
            assert result.status == "answered"
            ids = {hit["chunk_id"] for hit in adapter.tutor_evidence}
            assert LOCAL.chunk_id in ids  # Never throw away useful local evidence.
            assert any(str(item).startswith("WEB-PYDOC") for item in ids) == expect_web
            has_online = any(citation.source_type == "online" for citation in result.citations)
            assert has_online == expect_web
            if expect_web:
                assert "仅部分覆盖" in result.trace[0].detail
                assert "未命中" not in result.trace[0].detail

    asyncio.run(run())


def test_failed_supplement_preserves_local_evidence_and_reports_attempt() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = Adapter(PARTIAL)
            service = ClassroomDialogueService(
                courses=CoursePackRepository(), retriever=LocalRetriever(),
                online_retriever=PythonOfficialDocsRetriever(client=client, max_pages=1),
                tutor=CourseTutor(adapter), supervisor=QualitySupervisor(adapter),
            )
            result = await service.answer(ClassroomDialogueRequest(
                student_id="synthetic-partial-offline", lesson_id="python-list-filter-01",
                phase="concept", role="teacher", message="边界控制是什么",
            ))
            assert result.status == "answered"
            assert [citation.chunk_id for citation in result.citations] == [LOCAL.chunk_id]
            assert "未取得可用新证据" in result.trace[0].detail

    asyncio.run(run())


@pytest.mark.parametrize("repairs_citation", [True, False])
def test_outline_only_citation_is_repaired_without_publishing_unrelated_excerpts(
    repairs_citation: bool,
) -> None:
    class MissingCitationAdapter(Adapter):
        tutor_calls = 0

        async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
            response = await super().complete(messages)
            if "evidence" not in json.loads(messages[-1].content):
                return response
            if "课程辅导" not in messages[0].content:
                return response
            self.tutor_calls += 1
            if self.tutor_calls > 1:
                assert "missing_supplement_citation" in messages[0].content
                assert all(hit["source_type"] == "online" for hit in self.tutor_evidence)
            if self.tutor_calls == 1:
                data = json.loads(response.content)
                data["citation_chunk_ids"] = [LOCAL.chunk_id]
                return ModelResponse(content=json.dumps(data, ensure_ascii=False),
                                     provider="test-fixture", model="fixture", usage={})
            if not repairs_citation:
                data = json.loads(response.content)
                data["answer"] = "边界" * 910  # Still violates the role limit after repair.
                return ModelResponse(content=json.dumps(data, ensure_ascii=False),
                                     provider="test-fixture", model="fixture", usage={})
            return response

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<p>Python 的 range 序列不包含终点；索引超出范围时会产生 IndexError 异常。</p>"
        ))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = MissingCitationAdapter(PARTIAL)
            service = ClassroomDialogueService(
                courses=CoursePackRepository(), retriever=LocalRetriever(),
                online_retriever=PythonOfficialDocsRetriever(client=client, max_pages=1),
                tutor=CourseTutor(adapter), supervisor=QualitySupervisor(adapter),
            )
            result = await service.answer(ClassroomDialogueRequest(
                student_id="synthetic-citation-repair", lesson_id="python-list-filter-01",
                phase="concept", role="teacher", message="边界控制是什么",
            ))
            assert adapter.tutor_calls == 2  # Bounded repair, not an unbounded retry.
            if repairs_citation:
                assert result.status == "answered"
                assert any(citation.source_type == "online" for citation in result.citations)
            else:
                assert result.status == "insufficient_evidence"
                assert "请重试" in result.answer
                assert "range 序列不包含终点" not in result.answer
                assert "哪些操作改变" not in result.answer

    asyncio.run(run())


def test_boundary_query_keeps_introductory_rules_ahead_of_async_syntax() -> None:
    retriever = PythonOfficialDocsRetriever()
    targets = retriever._rank_targets("边界控制是什么 Python for while 循环起止条件")
    assert {target.path for _, target in targets[:2]} == {
        "tutorial/controlflow.html", "library/stdtypes.html",
    }
    ranked = retriever._rank_blocks("边界控制是什么 Python for while", [
        "async for TARGET in ITER : SUITE else : SUITE2",
        "range 生成的序列不会包括给定的终止值。range(10) 生成从0到9的序列。",
    ])
    assert "不会包括" in ranked[0][1]


def test_list_expression_requires_list_operation_evidence_not_just_print() -> None:
    print_only = SearchHit(
        source_id="SRC-PY-PRINT",
        chunk_id="print-only",
        score=.9,
        content="print 会把对象转换成便于阅读的文本并写到标准输出。",
        metadata={"title": "print 输出"},
    )
    list_rule = SearchHit(
        source_id="WEB-PYDOC-STDTYPES",
        chunk_id="list-concatenation",
        score=.9,
        content="列表属于序列；+ 运算用于拼接相同类型的序列。",
        metadata={"title": "内置类型", "source_type": "online"},
    )

    assert _deterministic_evidence_gap("print([1, 2] + [3, 4]) 的结果是什么？", [print_only])
    assert not _deterministic_evidence_gap(
        "print([1, 2] + [3, 4]) 的结果是什么？", [print_only, list_rule]
    )

    retriever = PythonOfficialDocsRetriever(max_pages=1)
    assert retriever._rank_targets("print([1, 2] + [3, 4]) 输出结果")[0][1].path == (
        "library/stdtypes.html"
    )
    ranked = retriever._rank_blocks("print([1, 2] + [3, 4]) 输出结果", [
        "print 会把对象输出到标准输出流，默认以空格分隔并在末尾换行。",
        "列表属于序列；相同类型的序列可以使用 + 运算拼接和连接，结果仍是列表。",
    ])
    assert "拼接" in ranked[0][1]


def test_print_hit_is_supplemented_before_answering_list_concatenation() -> None:
    print_only = SearchHit(
        source_id="SRC-PY-PRINT",
        chunk_id="print-only",
        score=.9,
        content="print 会把对象写到标准输出。",
        metadata={"title": "print 输出"},
    )

    class PrintRetriever:
        async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
            del query, course_id, top_k
            return (print_only,)

    class ListAdapter:
        async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
            if "证据覆盖检查" in messages[0].content:
                data = {"in_scope": True, "sufficient": True, "search_query": ""}
            elif "质量监督智能体" in messages[0].content:
                data = {"approved": True, "reason_code": "approved"}
            else:
                evidence = json.loads(messages[-1].content)["evidence"]
                online_id = next(
                    item["chunk_id"] for item in evidence if item["source_type"] == "online"
                )
                data = {
                    "answer": "列表的 + 会按顺序拼接两个列表，所以输出 [1, 2, 3, 4]。",
                    "citation_chunk_ids": [online_id],
                }
            return ModelResponse(
                content=json.dumps(data, ensure_ascii=False),
                provider="test-fixture",
                model="fixture",
                usage={},
            )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "docs.python.org"
        assert request.url.path.endswith("/library/stdtypes.html")
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<p>列表属于序列；相同类型的序列可以使用 + 运算进行拼接和连接，"
            "拼接后的元素保持原有顺序。</p>"
        ))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ListAdapter()
            service = ClassroomDialogueService(
                courses=CoursePackRepository(),
                retriever=PrintRetriever(),
                online_retriever=PythonOfficialDocsRetriever(client=client, max_pages=1),
                tutor=CourseTutor(adapter),
                supervisor=QualitySupervisor(adapter),
            )
            result = await service.answer(ClassroomDialogueRequest(
                student_id="synthetic-list-concat",
                lesson_id="python-list-filter-01",
                phase="concept",
                role="teacher",
                message="print([1, 2] + [3, 4]) 的输出结果是什么？请解释原因。",
            ))

            assert result.status == "answered"
            assert "[1, 2, 3, 4]" in result.answer
            assert any(citation.source_type == "online" for citation in result.citations)
            assert "仅部分覆盖" in result.trace[0].detail

    asyncio.run(run())
