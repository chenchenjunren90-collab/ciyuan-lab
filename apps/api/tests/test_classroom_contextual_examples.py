"""Reproduce the real generic-code request; assert content, not just HTTP status."""
import ast
import asyncio
import json
import re
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters.ports import ChatMessage, ModelResponse
from app.modules.orchestration.classroom import ClassroomDialogueRequest, ClassroomDialogueService
from app.modules.orchestration.dialogue_context import redact_dialogue_text
from app.modules.orchestration.supervisor import QualitySupervisor, sanitize_answer_text
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.retriever import LexicalKnowledgeRetriever

client = TestClient(app)
ROLES = ("teacher", "ta", "peer_cautious", "peer_debugger", "peer_summarizer")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("history", [[], [
    {"role": "student", "content": "给我举一个详细的代码示例"},
    {"role": "teacher", "content": "别着急，先抓住一句：【完整学习闭环】规划和测评。"},
]])
def test_real_example_request_uses_the_current_board(
    role: str, history: list[dict[str, str]],
) -> None:
    response = client.post("/api/v1/classroom/dialogue", json={
        "student_id": "synthetic-example-regression",
        "lesson_id": "python-adaptive--PY-BASE-07",
        "beat_id": "adaptive-concept--PY-BASE-07",
        "phase": "concept", "role": role,
        "message": "给我举一个详细的代码示例", "recent_turns": history,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "answered", result
    code = re.search(r"```python\n(.*?)```", result["answer"], re.S)
    assert code, result["answer"]
    ast.parse(code[1])
    assert "range(5)" in code[1] and "    print(number)" in code[1]
    assert "不包含" in result["answer"]  # Real curriculum explanation, not a generic invitation.
    assert "完整学习闭环" not in result["answer"]
    assert result["citations"]


def test_explicit_new_topic_is_not_overridden_by_current_board() -> None:
    result = client.post("/api/v1/classroom/dialogue", json={
        "student_id": "synthetic-new-topic", "lesson_id": "python-adaptive--PY-BASE-07",
        "beat_id": "adaptive-concept--PY-BASE-07", "phase": "concept", "role": "teacher",
        "message": "print 是什么意思？",
    }).json()
    assert result["status"] == "answered"
    assert "print" in result["answer"]
    assert "range(5)" not in result["answer"]


def test_unknown_beat_cannot_supply_fabricated_classroom_context() -> None:
    result = client.post("/api/v1/classroom/dialogue", json={
        "student_id": "synthetic-forged-beat", "lesson_id": "python-adaptive--PY-BASE-07",
        "beat_id": "adaptive-concept--PY-BASE-01", "phase": "concept", "role": "teacher",
        "message": "给个代码示例",
    })
    assert result.status_code == 404


def test_answer_sanitizer_preserves_multiline_python_and_markdown_structure() -> None:
    code = "for i in range(3):\n    if i:\n        print(i)\n"
    answer = f"示例：\n\n```python\n{code}```\n\n逐行解释：\n第一行遍历。"
    result = sanitize_answer_text(answer)
    assert f"```python\n{code}```" in result
    assert "\n\n逐行解释" in result
    match = re.search(r"```python\n(.*?)```", result, re.S)
    assert match
    ast.parse(match[1])


def test_context_redacts_contact_fields_without_changing_indentation() -> None:
    text = "姓名：测试同学 邮箱 a@example.com 电话 13800000000\n    print(1)"
    result = redact_dialogue_text(text)
    assert "测试同学" not in result and "a@example.com" not in result
    assert "13800000000" not in result and "\n    print(1)" in result


def test_generated_example_is_repaired_once_without_replacing_it_with_stock_prose() -> None:
    class Adapter:
        calls = 0

        async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse:
            if "质量监督智能体" in messages[0].content:
                content = json.dumps({"approved": True, "reason_code": "approved"})
            else:
                self.calls += 1
                payload = json.loads(messages[-1].content)
                example = next(hit for hit in payload["evidence"]
                               if hit["chunk_id"].startswith("COURSE-EXAMPLE-"))
                content = json.dumps({
                    "answer": "先看课程的学习闭环。" if self.calls == 1 else
                    "range(5) 提供 0 到 4。\n```python\nfor number in range(5):\n"
                    "    print(number)\n```\n每次循环输出当前的 number；不包含终点 5。",
                    "citation_chunk_ids": [example["chunk_id"]],
                })
            return ModelResponse(
                content=content, provider="test-fixture", model="fixture", usage={},
            )

    courses = CoursePackRepository()
    adapter = Adapter()
    service = ClassroomDialogueService(
        courses=courses, retriever=LexicalKnowledgeRetriever.from_repository(courses),
        tutor=CourseTutor(adapter), supervisor=QualitySupervisor(adapter),
    )
    result = asyncio.run(service.answer(ClassroomDialogueRequest(
        student_id="synthetic-repair", lesson_id="python-adaptive--PY-BASE-07",
        beat_id="adaptive-concept--PY-BASE-07", phase="concept", role="teacher",
        message="给我举一个详细的代码示例",
    )))
    assert adapter.calls == 2
    assert result.status == "answered" and "```python" in result.answer
    assert result.trace[1].status == "completed"
