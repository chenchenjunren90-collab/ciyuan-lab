"""HTTP smoke test for the complete deterministic MVP learning loop."""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = "http://127.0.0.1:8000/api/v1"


def request(path: str, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urlopen(req, timeout=10) as response:  # noqa: S310 - fixed localhost URL
        return json.load(response)


def main() -> int:
    student_id = f"smoke-{uuid4().hex[:10]}"
    health = request("/health")
    courses = request("/courses")
    course_knowledge = {
        course["id"]: request(f"/courses/{course['id']}/knowledge-points")["items"]
        for course in courses
    }
    knowledge = course_knowledge["python"]
    knowledge_detail = request(f"/courses/python/knowledge-points/{knowledge[0]['id']}")
    assessment = request(
        "/assessments",
        {
            "student_id": student_id,
            "course_id": "python",
            "answers": [
                {"knowledge_point_id": item["id"], "is_correct": index < 2}
                for index, item in enumerate(knowledge[:8])
            ],
        },
    )
    qa = request(
        "/qa",
        {
            "student_id": student_id,
            "course_id": "python",
            "question": "数据清洗如何处理缺失值并保留错误原因？",
        },
    )
    scenario = request(
        "/courses/python/projects/PY-PROJ-FINANCE-DATA-01/scenario"
    )
    activities = request("/courses/python/activities")
    hint_activity = next(item for item in activities if item["type"] != "project")
    hint = request(
        f"/activities/{hint_activity['id']}/hint?course_id=python",
        {"student_id": student_id, "level": 1},
    )
    project_submission = request(
        "/projects/PY-PROJ-FINANCE-DATA-01/submissions?course_id=python",
        {
            "student_id": student_id,
            "artifact_summary": (
                "完成了解析、校验、异常分类和统计汇总模块，"
                "并记录正常、边界与错误路径的测试证据。"
            ),
            "test_evidence": ["smoke: project intake path reached"],
        },
    )

    assert health["status"] == "ok"
    assert {course["id"] for course in courses} == {"c", "python", "data_structures"}
    assert all(len(items) == 40 for items in course_knowledge.values())
    assert knowledge_detail["lesson"]["key_points"]
    assert assessment["plan"]["next_activity"]["activity_id"]
    assert qa["status"] == "answered" and qa["citations"] and len(qa["trace"]) == 3
    assert scenario["mode"] in {"tuoling", "fixed_synthetic"}
    assert hint["level"] == 1 and hint["answer_revealed"] is False
    assert project_submission["status"] == "received_for_review"
    print(
        "MVP v0.2 smoke passed: 120 concepts, plan, grounded QA trace, "
        "progressive hint, scenario fallback, project review intake"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, HTTPError, URLError, TimeoutError) as exc:
        print(f"MVP smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
