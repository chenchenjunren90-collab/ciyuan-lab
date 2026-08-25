"""RAG only answers from eligible sources in the requested course."""

from typing import Any, cast

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def ask(course_id: str, question: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/qa",
        json={"student_id": "rag-test", "course_id": course_id, "question": question},
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def test_retrieves_c_memory_evidence_with_traceable_citation() -> None:
    payload = ask("c", "动态内存为什么要检查 malloc 并且避免重复释放？")

    assert payload["status"] == "answered"
    assert payload["answer"]
    citations = payload["citations"]
    assert citations
    assert all(item["source_id"].startswith("SRC-C-") for item in citations)
    assert all(item["chunk_id"].startswith(item["source_id"]) for item in citations)
    assert [step["component"] for step in payload["trace"]] == [
        "retrieval",
        "course_tutor",
        "quality_supervisor",
    ]


def test_retrieves_python_data_quality_evidence() -> None:
    payload = ask("python", "Python 数据清洗时如何处理缺失值和异常？")

    assert payload["status"] == "answered"
    assert any(item["source_id"] == "SRC-PY-GUIDE-DATA" for item in payload["citations"])


def test_retrieves_data_structure_graph_evidence() -> None:
    payload = ask("data_structures", "BFS 为什么使用队列？Dijkstra 对权重有什么要求？")

    assert payload["status"] == "answered"
    assert any(item["source_id"] == "SRC-DS-GUIDE-TREEGRAPH" for item in payload["citations"])


def test_returns_insufficient_evidence_for_unrelated_question() -> None:
    payload = ask("c", "明天火星基地的天气和航班价格是多少？")

    assert payload["status"] == "insufficient_evidence"
    assert payload["answer"] == ""
    assert payload["citations"] == []
    assert payload["trace"][0]["component"] == "retrieval"
    assert payload["trace"][0]["status"] == "blocked"


def test_rejects_unknown_request_fields() -> None:
    response = client.post(
        "/api/v1/qa",
        json={
            "student_id": "rag-test",
            "course_id": "python",
            "question": "函数是什么？",
            "override_source": "untrusted",
        },
    )

    assert response.status_code == 422
