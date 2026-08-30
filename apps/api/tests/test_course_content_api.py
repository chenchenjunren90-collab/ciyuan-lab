"""Course APIs expose versioned learning content without answer leakage."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import (
    CoursePackRepository,
    CourseRecordNotFoundError,
)

client = TestClient(app)


def test_lists_three_courses_with_real_progress() -> None:
    response = client.get("/api/v1/courses")

    assert response.status_code == 200
    courses = {item["id"]: item for item in response.json()}
    assert set(courses) == {"c", "python", "data_structures"}
    assert courses["python"]["implemented_core_concepts"] == 40
    assert courses["c"]["implemented_core_concepts"] == 42
    assert courses["data_structures"]["implemented_core_concepts"] == 40


def test_lists_real_python_knowledge_points() -> None:
    response = client.get("/api/v1/courses/python/knowledge-points")

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == "python"
    assert len(payload["items"]) == 40
    function = next(
        item for item in payload["items"] if item["id"] == "PY-FUNC-01"
    )
    assert function["title"] == "函数定义与调用"
    assert len(function["concepts"]) >= 3
    assert function["source_refs"]

    detail = client.get(
        "/api/v1/courses/python/knowledge-points/PY-FUNC-01"
    ).json()
    assert detail["lesson"]["key_points"]


def test_course_detail_returns_404_for_unknown_record() -> None:
    response = client.get("/api/v1/courses/python/knowledge-points/PY-NOT-FOUND")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_activity_never_exposes_answer_keys_or_hidden_tests() -> None:
    objective = client.get(
        "/api/v1/courses/python/activities/PY-BASE-01-Q1"
    ).json()
    code = client.get("/api/v1/courses/python/activities/PY-FUNC-01-C1").json()

    assert "accepted_answers" not in objective["evaluation"]
    assert all(
        test["visibility"] == "public" for test in code["evaluation"]["tests"]
    )
    assert not any(
        test["visibility"] == "hidden" for test in code["evaluation"]["tests"]
    )


def test_filters_activities_by_knowledge_point() -> None:
    response = client.get(
        "/api/v1/courses/python/activities",
        params={"knowledge_point_id": "PY-FUNC-01"},
    )

    assert response.status_code == 200
    assert response.json()
    assert all("PY-FUNC-01" in item["concept_ids"] for item in response.json())


def test_exposes_beginner_scaffolding_without_hidden_tests() -> None:
    response = client.get("/api/v1/courses/python/activities/PY-BASE-04-H1")

    assert response.status_code == 200
    activity = response.json()
    assert activity["learning_stage"] == "after_class"
    assert activity["audience"] == "chinese_beginner"
    assert len(activity["scaffolding"]) == 3
    assert activity["input_format"] == "一行两个整数。"
    assert activity["output_format"] == "输出两个整数的和。"
    assert activity["public_examples"][0]["expected_output"] == "8\n"
    assert activity["reflection_prompt"]
    assert activity["source_adaptation"]["source_id"] == "SRC-PY-EXERCISM-TRACK"
    assert all(
        test["visibility"] == "public" for test in activity["evaluation"]["tests"]
    )


def test_filters_after_class_activities_for_a_knowledge_point() -> None:
    response = client.get(
        "/api/v1/courses/python/activities",
        params={"knowledge_point_id": "PY-FUNC-01", "learning_stage": "after_class"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["PY-FUNC-01-H1"]


def test_rejects_unknown_learning_stage() -> None:
    response = client.get(
        "/api/v1/courses/python/activities",
        params={"learning_stage": "homework-ish"},
    )

    assert response.status_code == 422


def test_lists_registered_sources_with_rag_eligibility() -> None:
    response = client.get("/api/v1/courses/python/sources")

    assert response.status_code == 200
    sources = {item["id"]: item for item in response.json()}
    assert {
        "SRC-PY-OFFICIAL-REF",
        "SRC-PY-OFFICIAL-TUTORIAL",
        "SRC-PY-OUTLINE-01",
        "SRC-PY-GUIDE-BASE",
        "SRC-PY-GUIDE-FUNCTIONS",
        "SRC-PY-GUIDE-DATA",
        "SRC-PY-GUIDE-ENGINEERING",
        "SRC-PY-GUIDE-CASE-FALLBACK",
    }.issubset(sources)
    assert sources["SRC-PY-OUTLINE-01"]["rag_eligible"] is False
    assert sources["SRC-PY-GUIDE-DATA"]["rag_eligible"] is True


def test_repository_rejects_record_path_traversal() -> None:
    repository = CoursePackRepository()

    try:
        repository.get_activity("python", "../manifest")
    except CourseRecordNotFoundError as exc:
        assert "invalid path" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("path traversal id should have been rejected")
