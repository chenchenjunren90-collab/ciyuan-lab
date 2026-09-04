"""Official-doc fallback stays bounded, traceable and course-isolated."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import httpx

from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters.mock import MockAdapter
from app.modules.orchestration.classroom import (
    ClassroomDialogueRequest,
    ClassroomDialogueService,
)
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.python_docs import PythonOfficialDocsRetriever


def _docs_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, timeout=2.0)


def test_official_docs_retriever_extracts_only_matching_python_evidence() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                "<html><body><nav>不应进入证据</nav>"
                "<p>match 语句接受一个主题值，并将它与一个或多个 case 模式进行比较。</p>"
                "<pre>&gt;&gt;&gt; value = 2\n&gt;&gt;&gt; match value:\n"
                "...     case 2: print('匹配成功')</pre>"
                "<p>其他没有关键词重叠的介绍文字不会排到前面。</p>"
                "</body></html>"
            ),
        )

    async def run() -> tuple[SearchHit, ...]:
        async with _docs_client(httpx.MockTransport(handler)) as client:
            retriever = PythonOfficialDocsRetriever(client=client, max_pages=2)
            return tuple(await retriever.search("match case 是什么？请举一个例子", "python", 3))

    hits = asyncio.run(run())
    assert hits
    assert all(host == "docs.python.org" for host in requested_hosts)
    assert all(hit.source_id.startswith("WEB-PYDOC-") for hit in hits)
    assert all(hit.metadata["source_type"] == "online" for hit in hits)
    assert all(str(hit.metadata["url"]).startswith("https://docs.python.org/") for hit in hits)
    assert "REFERENCE-COMPOUND-STMTS" in hits[0].source_id
    assert "match" in hits[0].content.casefold()
    assert any("print" in hit.content for hit in hits)
    assert "不应进入证据" not in hits[0].content


def test_official_docs_retriever_never_runs_for_another_course() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    async def run() -> tuple[SearchHit, ...]:
        async with _docs_client(httpx.MockTransport(handler)) as client:
            retriever = PythonOfficialDocsRetriever(client=client)
            return tuple(await retriever.search("match case", "c", 3))

    assert asyncio.run(run()) == ()
    assert calls == 0


class _EmptyRetriever:
    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        del query, course_id, top_k
        return ()


class _BroadButIrrelevantRetriever:
    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        del query, course_id, top_k
        return (
            SearchHit(
                source_id="SRC-PY-LIST-LOCAL",
                chunk_id="SRC-PY-LIST-LOCAL-generic",
                content="列表遍历时可以使用 for 循环逐个处理元素。",
                score=0.71,
                metadata={"source_type": "course", "title": "列表遍历"},
            ),
        )


class _OnlineFixtureRetriever:
    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        del query, top_k
        assert course_id == "python"
        return (
            SearchHit(
                source_id="WEB-PYDOC-REFERENCE-COMPOUND-STMTS-HTML",
                chunk_id="WEB-PYDOC-REFERENCE-COMPOUND-STMTS-HTML-demo",
                content="match 语句接受一个主题值，并将它与一个或多个 case 模式进行比较。",
                score=0.92,
                metadata={
                    "source_type": "online",
                    "title": "复合语句",
                    "url": "https://docs.python.org/zh-cn/3.11/reference/compound_stmts.html",
                },
            ),
        )


def _service(local_retriever: KnowledgeRetriever | None = None) -> ClassroomDialogueService:
    model = MockAdapter()
    return ClassroomDialogueService(
        courses=CoursePackRepository(),
        retriever=local_retriever or _EmptyRetriever(),
        online_retriever=_OnlineFixtureRetriever(),
        tutor=CourseTutor(model),
        supervisor=QualitySupervisor(model),
        top_k=3,
    )


def test_classroom_uses_online_docs_only_after_local_miss() -> None:
    result = asyncio.run(
        _service().answer(
            ClassroomDialogueRequest(
                student_id="online-docs-student",
                lesson_id="python-list-filter-01",
                phase="concept",
                role="teacher",
                message="match case 是什么？",
            )
        )
    )

    assert result.status == "answered"
    assert result.question_scope == "python_course_extension"
    assert result.citations[0].source_type == "online"
    assert result.citations[0].source_url is not None
    assert "联网检索" in result.trace[0].detail
    assert "match" in result.answer.casefold()


def test_broad_vector_hit_cannot_suppress_official_docs_fallback() -> None:
    result = asyncio.run(
        _service(_BroadButIrrelevantRetriever()).answer(
            ClassroomDialogueRequest(
                student_id="broad-vector-student",
                lesson_id="python-list-filter-01",
                phase="concept",
                role="teacher",
                message="match case 是什么？",
            )
        )
    )

    assert result.status == "answered"
    assert result.question_scope == "python_course_extension"
    assert result.citations[0].source_type == "online"
    assert "联网检索" in result.trace[0].detail


def test_classroom_rules_block_clear_off_topic_before_online_search() -> None:
    result = asyncio.run(
        _service().answer(
            ClassroomDialogueRequest(
                student_id="off-topic-student",
                lesson_id="python-list-filter-01",
                phase="concept",
                role="teacher",
                message="请给我推荐今天的股票新闻。",
            )
        )
    )

    assert result.status == "insufficient_evidence"
    assert result.question_scope == "outside_course"
    assert result.citations == []
    assert "不属于 Python 课程" in (result.scope_notice or "")
