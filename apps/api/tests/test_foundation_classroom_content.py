"""C / data-structure classroom content and student-facing contract checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import CoursePackRepository
from app.modules.course_content.models import CourseId
from app.modules.rag.evaluation import load_eval_cases

client = TestClient(app)
REPOSITORY = CoursePackRepository()
EXAMPLE_OUTPUTS = {
    "DS-STACK-01": "True\nFalse\nTrue\n",
    "DS-QUEUE-01": "A B C\n0\n",
    "DS-SEARCH-02": "1\n-1\n-1\n",
    "DS-SORT-02": "[1, 2, 2, 5]\n[]\n",
    "DS-GRAPH-02": "[0, 1, 2, 3]\n[0, 1, 1, 2, -1]\n",
    "DS-LINEAR-03": "[3, 2, 1]\nNone\n",
    "DS-TREE-02": "A B C\nB A C\nB C A\n",
    "DS-GRAPH-05": "[0, 3, 1, 4]\n",
    "DS-HASH-02": "3 -1\n6 0\n",
    "DS-GRAPH-03": "[0, 1, 3, 2, 4]\n[]\n[0]\n",
    "DS-TREE-03": "[3, 5, 6, 7]\n[3, 6, 7]\n[7]\n",
}


@pytest.mark.parametrize("identifier, expected", EXAMPLE_OUTPUTS.items())
def test_authored_ds_examples_execute(identifier: str, expected: str) -> None:
    # These are repository-authored fixed examples, never learner-provided code.
    detail = REPOSITORY.get_knowledge_point("data_structures", identifier)
    result = subprocess.run(
        [sys.executable, "-I", "-c", detail.lesson["worked_example"]["code"]],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected
    assert len(detail.lesson["learning_sequence"]) >= 3
    assert detail.lesson["checkpoint"]["prompt"]


@pytest.mark.parametrize("course, count", [("c", 42), ("data_structures", 40)])
def test_whole_course_can_be_loaded_and_has_linked_exercises(course: str, count: int) -> None:
    response = client.get(f"/api/v1/courses/{course}/knowledge-points")
    assert response.status_code == 200
    points = response.json()["items"]
    assert len(points) == count
    for point in points:
        detail = client.get(f"/api/v1/courses/{course}/knowledge-points/{point['id']}")
        assert detail.status_code == 200
        assert detail.json()["lesson"]["summary"]
        activities = client.get(
            f"/api/v1/courses/{course}/activities",
            params={"knowledge_point_id": point["id"]},
        ).json()
        assert activities, point["id"]
        for activity in activities:
            public = client.get(f"/api/v1/courses/{course}/activities/{activity['id']}").json()
            assert "accepted_answers" not in public["evaluation"]
            assert all(
                test["visibility"] == "public" for test in public["evaluation"].get("tests", [])
            )


@pytest.mark.parametrize("course", ["c", "data_structures"])
def test_new_knowledge_sources_stay_outside_production_retrieval(course: CourseId) -> None:
    sources = client.get(f"/api/v1/courses/{course}/sources").json()
    drafted = [item for item in sources if item["id"].endswith("-WALKTHROUGH")]
    assert len(drafted) == (10 if course == "c" else 11)
    assert all(item["status"] == "draft" and not item["rag_eligible"] for item in drafted)
    accepted = {source.id for source in REPOSITORY.list_rag_source_records(course)}
    assert accepted
    assert not accepted.intersection(item["id"] for item in drafted)


@pytest.mark.parametrize(
    "course, exercise",
    [
        ("c", "C-ARRAY-01-C1"),
        ("c", "C-MEM-01-C1"),
        ("data_structures", "DS-SEARCH-02-C1"),
        ("data_structures", "DS-SORT-02-C1"),
    ],
)
def test_empty_input_tests_and_contract_are_present(course: CourseId, exercise: str) -> None:
    record = REPOSITORY.get_practice_activity(course, exercise)
    assert any(test["id"] == "hidden-empty" for test in record.evaluation["tests"])
    detail = REPOSITORY.get_activity(course, exercise)
    assert detail.input_format
    assert detail.output_format
    assert len(detail.scaffolding) == 3


def test_no_cross_course_concept_lookup() -> None:
    assert client.get("/api/v1/courses/c/knowledge-points/DS-GRAPH-02").status_code == 404
    assert client.get("/api/v1/courses/data_structures/activities/C-PTR-01-C1").status_code == 404


def test_boundary_retrieval_cases_only_expect_reviewed_sources() -> None:
    root = Path(__file__).resolve().parents[3]
    cases = load_eval_cases(root / "evals/rag/foundation-boundaries-v1.jsonl")
    assert len(cases) == 16
    for course in ("c", "data_structures"):
        selected = [case for case in cases if case.course_id == course]
        assert len(selected) == 8
        assert sum(case.kind == "answerable" for case in selected) == 4
        sources = {source.id for source in REPOSITORY.list_rag_source_records(course)}
        for case in selected:
            assert set(case.expected_source_ids) <= sources


@pytest.mark.parametrize(
    "identifier, checks",
    [
        (
            "DS-TREE-03",
            "root = None\n"
            "assert erase(root, 3) is None\n"
            "for key in range(2001): root = insert(root, key)\n"
            "root = insert(root, 1000)\n"
            "assert inorder(root) == list(range(2001))\n"
            "for key in range(2001): root = erase(root, key)\n"
            "assert inorder(root) == []\n"
            "root = None\n"
            "for key in [5, 2, 9, 6, 7]: root = insert(root, key)\n"
            "root = erase(root, 5)\n"
            "assert inorder(root) == [2, 6, 7, 9]\n"
            "root = erase(root, 99)\n"
            "assert inorder(root) == [2, 6, 7, 9]\n",
        ),
        (
            "DS-HASH-02",
            "t = [EMPTY] * 3\n"
            "for k in [0, 3, 6]: insert(t, k)\n"
            "assert find(t, 9) == -1\n"
            "try:\n"
            "    insert(t, 9)\n"
            "except ValueError:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError('full table must reject a new key')\n"
            "t[0] = DELETED\n"
            "insert(t, 6)\n"
            "assert t[0] is DELETED\n"
            "insert(t, -3)\n"
            "assert find(t, -3) == 0\n"
            "assert find(t, 6) == 2\n",
        ),
        (
            "DS-GRAPH-03",
            "assert dfs_forest([[], [], []]) == [0, 1, 2]\n"
            "assert dfs_forest([[1, 1], [0]]) == [0, 1]\n"
            "chain = [[i + 1] for i in range(2000)] + [[]]\n"
            "assert dfs_forest(chain) == list(range(2001))\n",
        ),
    ],
)
def test_new_fixed_examples_cover_algorithm_boundaries(identifier: str, checks: str) -> None:
    example = REPOSITORY.get_knowledge_point("data_structures", identifier)
    result = subprocess.run(
        [sys.executable, "-I", "-c", example.lesson["worked_example"]["code"] + checks],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
