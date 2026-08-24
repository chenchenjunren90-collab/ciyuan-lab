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
    knowledge = request("/courses/python/knowledge-points")["items"]
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

    assert health["status"] == "ok"
    assert {course["id"] for course in courses} == {"c", "python", "data_structures"}
    assert assessment["plan"]["next_activity"]["activity_id"]
    assert qa["status"] == "answered" and qa["citations"]
    assert scenario["mode"] in {"tuoling", "fixed_synthetic"}
    print("MVP smoke test passed: health, 3 courses, plan, grounded QA, scenario fallback")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, HTTPError, URLError, TimeoutError) as exc:
        print(f"MVP smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
