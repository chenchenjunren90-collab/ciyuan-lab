"""HTTP smoke test for the complete deterministic MVP learning loop."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = "http://127.0.0.1:8000/api/v1"
REQUEST_TIMEOUT_SECONDS = 90.0

COURSE_QUESTIONS = {
    "c": "动态内存为什么要检查分配结果并避免重复释放？",
    "python": "Python 数据清洗如何处理缺失值并保留错误原因？",
    "data_structures": "BFS 为什么使用队列？Dijkstra 对权重有什么要求？",
}

CODE_SAMPLES = {
    "c": (
        "C-ARRAY-01-C1",
        "c",
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    int n, value, maximum;\n"
        "    if (scanf(\"%d\", &n) != 1 || n <= 0) return 1;\n"
        "    for (int i = 0; i < n; ++i) {\n"
        "        if (scanf(\"%d\", &value) != 1) return 1;\n"
        "        if (i == 0 || value > maximum) maximum = value;\n"
        "    }\n"
        "    printf(\"%d\\n\", maximum);\n"
        "    return 0;\n"
        "}\n",
    ),
    "python": (
        "PY-FUNC-01-C1",
        "python",
        "n = int(input())\nresult = 1\nfor value in range(2, n + 1):\n"
        "    result *= value\nprint(result)\n",
    ),
    "data_structures": (
        "DS-LINEAR-01-C1",
        "python",
        "n = int(input())\nvalues = list(map(int, input().split()))\n"
        "target = int(input())\n"
        "print(values[:n].index(target) if target in values[:n] else -1)\n",
    ),
}

ADAPTIVE_SOLUTIONS = {
    "LIST-SUMMARY": (
        "n = int(input())\nvalues = list(map(int, input().split())) if n else []\n"
        "if not values:\n    print('EMPTY')\n"
        "else:\n    print(len(values), sum(values), min(values), max(values))\n"
    ),
    "DICT-COUNT": (
        "n = int(input())\ncounts = {}\n"
        "for _ in range(n):\n    label = input().strip()\n"
        "    counts[label] = counts.get(label, 0) + 1\n"
        "for label in sorted(counts):\n    print(label, counts[label])\n"
    ),
    "LIST-FILTER": (
        "values = list(map(int, input().split()))\n"
        "print(*[value * value for value in values if value > 0 and value % 2 == 0])\n"
    ),
    "SAFE-PARSE": (
        "n = int(input())\nvalid = []\n"
        "for _ in range(n):\n"
        "    try:\n        valid.append(int(input()))\n"
        "    except ValueError:\n        pass\n"
        "print(len(valid), sum(valid))\n"
    ),
}


def request(path: str, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.load(response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="API 根地址，默认 %(default)s",
    )
    parser.add_argument(
        "--with-code-execution",
        action="store_true",
        help="提交三门课的真实代码题；服务必须显式启用 Docker 代码执行",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=REQUEST_TIMEOUT_SECONDS,
        help="单次 HTTP 请求超时秒数，默认 %(default)s",
    )
    return parser.parse_args()


def main() -> int:
    global BASE_URL, REQUEST_TIMEOUT_SECONDS
    args = parse_args()
    if args.request_timeout <= 0:
        raise ValueError("request timeout must be greater than zero")
    BASE_URL = args.base_url.rstrip("/")
    REQUEST_TIMEOUT_SECONDS = args.request_timeout
    student_id = f"smoke-{uuid4().hex[:10]}"
    health = request("/health")
    courses = request("/courses")
    course_knowledge = {
        course["id"]: request(f"/courses/{course['id']}/knowledge-points")["items"]
        for course in courses
    }
    expected_concept_counts = {
        course["id"]: course["implemented_core_concepts"] for course in courses
    }
    total_concepts = sum(len(items) for items in course_knowledge.values())
    assert health["status"] == "ok"
    assert {course["id"] for course in courses} == {"c", "python", "data_structures"}
    assert all(
        len(items) == expected_concept_counts[course_id]
        for course_id, items in course_knowledge.items()
    )
    assert total_concepts >= 120

    for course_id, knowledge in course_knowledge.items():
        detail = request(f"/courses/{course_id}/knowledge-points/{knowledge[0]['id']}")
        diagnostic = request(f"/diagnostics?course_id={course_id}&phase=initial")
        assert "accepted_answers" not in json.dumps(diagnostic)
        assessment = request(
            "/diagnostics/submissions",
            {
                "student_id": student_id,
                "course_id": course_id,
                "phase": "initial",
                "answers": [
                    {
                        "exercise_id": item["exercise_id"],
                        "response": item["options"][0]["id"],
                    }
                    for item in diagnostic["items"]
                ],
            },
        )
        qa = request(
            "/qa",
            {
                "student_id": student_id,
                "course_id": course_id,
                "question": COURSE_QUESTIONS[course_id],
            },
        )
        activities = request(f"/courses/{course_id}/activities")
        hint_activity = next(item for item in activities if item["type"] != "project")
        project = next(item for item in activities if item["type"] == "project")
        hint = request(
            f"/activities/{hint_activity['id']}/hint?course_id={course_id}",
            {"student_id": student_id, "level": 1},
        )
        project_submission = request(
            f"/projects/{project['id']}/submissions?course_id={course_id}",
            {
                "student_id": student_id,
                "artifact_summary": (
                    "完成了核心模块、边界处理和错误路径设计，"
                    "并记录正常、边界与异常输入对应的可复核测试证据。"
                ),
                "test_evidence": [f"smoke: {course_id} project evidence path reached"],
            },
        )

        assert detail["lesson"]["key_points"]
        assert assessment["total_count"] == len(diagnostic["items"])
        assert assessment["plan"]["next_activity"]["activity_id"]
        assert qa["status"] == "answered" and qa["citations"] and len(qa["trace"]) == 3
        assert hint["level"] == 1 and hint["answer_revealed"] is False
        assert project_submission["status"] == "evidence_recorded"

        if args.with_code_execution:
            exercise_id, language, source_code = CODE_SAMPLES[course_id]
            submission = request(
                f"/exercises/{exercise_id}/submissions?course_id={course_id}",
                {
                    "student_id": student_id,
                    "language": language,
                    "source_code": source_code,
                },
            )
            assert submission["verification"]["accepted"] is True
            assert submission["verification"]["passed_tests"] == submission["verification"][
                "total_tests"
            ]

    structured_lesson = request("/courses/python/knowledge-points/PY-LIST-01")
    assert structured_lesson["lesson"]["learning_sequence"]
    assert structured_lesson["lesson"]["worked_example"]["steps"]
    generated_problem = request(
        "/adaptive-problems/generate",
        {"student_id": student_id, "course_id": "python", "attempt_index": 1},
    )
    assert "hidden" not in json.dumps(generated_problem).lower()
    if args.with_code_execution:
        template_id = next(
            template
            for template in ADAPTIVE_SOLUTIONS
            if f"-{template}-" in generated_problem["problem_id"]
        )
        adaptive_submission = request(
            f"/adaptive-problems/{generated_problem['problem_id']}/submissions",
            {
                "student_id": student_id,
                "source_code": ADAPTIVE_SOLUTIONS[template_id],
            },
        )
        assert adaptive_submission["verification"]["accepted"] is True
        assert adaptive_submission["next_problem"]["problem_id"] != generated_problem[
            "problem_id"
        ]

    scenario = request("/courses/python/projects/PY-PROJ-FINANCE-DATA-01/scenario")
    assert scenario["mode"] == "fixed_synthetic"
    generated_project = request(
        "/courses/python/scenario-projects/generate",
        {
            "course_id": "python",
            "template_project_id": "PY-PROJ-BANK-MARKETING-01",
            "learner_goal": "练习字典分组、复合键去重与确定性测试",
            "target_concept_ids": ["PY-DICT-02", "PY-FILE-03"],
            "difficulty": "intermediate",
            "estimated_minutes": 120,
        },
    )
    assert generated_project["data_classification"] == "synthetic"
    assert generated_project["dataset"]["rows"]
    assert generated_project["source_refs"]
    assert generated_project["ai_generated_notice"]
    print(
        f"MVP smoke passed for C, Python and data structures: {total_concepts} concepts, "
        "server-graded diagnostics, plans, structured lessons, adaptive problems, "
        "grounded QA traces, progressive hints, controlled synthetic "
        "project generation and project evidence intake"
        + (", plus real Docker code verification" if args.with_code_execution else "")
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, HTTPError, URLError, TimeoutError) as exc:
        print(f"MVP smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
