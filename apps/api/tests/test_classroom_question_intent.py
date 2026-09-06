"""Regression: a relevant card is not necessarily an answer to the question."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ROLES = ("teacher", "ta", "peer_cautious", "peer_debugger", "peer_summarizer")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(("question", "required"), [
    ("elif 和 else if 的区别是什么？", ("不能写成 else if", "缩进")),
    ("if 能嵌套吗？", ("可以嵌套", "外层条件成立", "同一缩进")),
])
def test_degraded_roles_answer_the_specific_question(
    role: str, question: str, required: tuple[str, ...],
) -> None:
    response = client.post("/api/v1/classroom/dialogue", json={
        "student_id": "synthetic-intent-regression",
        "lesson_id": "python-adaptive--PY-BASE-05",
        "phase": "concept", "role": role, "message": question,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert all(text in payload["answer"] for text in required), payload["answer"]
    assert payload["citations"]
    assert payload["trace"][1]["status"] == "degraded"


@pytest.mark.parametrize("role", ROLES)
def test_missing_debug_code_requests_context_instead_of_guessing(role: str) -> None:
    payload = client.post("/api/v1/classroom/dialogue", json={
        "student_id": "synthetic-missing-code",
        "lesson_id": "python-adaptive--PY-BASE-05",
        "phase": "debug", "role": role, "message": "这段代码哪错了？",
    }).json()
    assert payload["status"] == "insufficient_evidence"
    assert "代码" in payload["answer"]
    assert payload["citations"] == []
