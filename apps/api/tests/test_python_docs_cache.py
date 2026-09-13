"""Public-document cache: shared concurrent reads, expiry, recovery and context misses."""
import asyncio
from collections.abc import Sequence

import httpx
import pytest
from test_python_online_docs import _service

from app.modules.orchestration.classroom import ClassroomDialogueRequest, ClassroomDialogueTurn
from app.modules.rag.ports import SearchHit
from app.modules.rag.python_docs import PythonOfficialDocsRetriever


def test_public_pages_are_shared_then_expire(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [10.0]
    monkeypatch.setattr("app.modules.rag.python_docs.time.monotonic", lambda: now[0])
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        await asyncio.sleep(0)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<p>match 语句将主题值与 case 模式比较。</p>"
        ))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            retriever = PythonOfficialDocsRetriever(client=client, max_pages=1,
                                                    cache_ttl_seconds=60)
            first, second = await asyncio.gather(
                retriever.search("match case", "python", 2),
                retriever.search("match case", "python", 2),
            )
            assert first == second and first
            assert len(calls) == 1
            assert await retriever.search("match case", "python", 2) == first
            assert len(calls) == 1
            now[0] += 61
            assert await retriever.search("match case", "python", 2)
            assert len(calls) == 2
    asyncio.run(run())


def test_failed_fetch_is_not_cached_forever(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [10.0]
    monkeypatch.setattr("app.modules.rag.python_docs.time.monotonic", lambda: now[0])
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, headers={"content-type": "text/html"},
                              text="<p>match 会将值与 case 模式比较。</p>")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            retriever = PythonOfficialDocsRetriever(client=client, max_pages=1)
            assert not await retriever.search("match case", "python", 1)
            assert not await retriever.search("match case", "python", 1)
            assert calls == 1
            now[0] += 16
            assert await retriever.search("match case", "python", 1)
            assert calls == 2
    asyncio.run(run())


def test_followup_uses_resolved_topic_for_online_fallback() -> None:
    queries: list[str] = []

    class RecordingOnline:
        async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
            queries.append(query)
            return ()

    service = _service()
    service._online_retriever = RecordingOnline()
    asyncio.run(service.answer(ClassroomDialogueRequest(
        student_id="synthetic-online-context", lesson_id="python-list-filter-01",
        phase="concept", role="teacher", message="那这个再解释一下",
        recent_turns=[ClassroomDialogueTurn(role="student", content="match case 是什么？")],
    )))
    assert queries and "match case" in queries[0]
