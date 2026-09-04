"""Tests for the learning planner and safe degradation (Issue AGENT-01)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

from app.modules.learner_profile.models import LearnerProfile, MasteryState
from app.modules.learner_profile.records import RecommendationCandidate
from app.modules.model_adapters import (
    MockAdapter,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
)
from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse
from app.modules.orchestration import (
    CourseNotFoundError,
    LearningPlanner,
    PlannedActivity,
    load_course_catalog,
)
from app.modules.orchestration.catalog import (
    CourseActivity,
    CourseCatalog,
    CourseCatalogError,
)
from app.modules.orchestration.catalog import (
    load_course_catalog as load_catalog,
)
from app.modules.orchestration.prompts import build_planning_messages, parse_model_choice
from app.modules.orchestration.service import build_learning_planner

PY_COURSE = "python"
PY_BASE_01 = "PY-BASE-01"
PY_BASE_02 = "PY-BASE-02"
PY_FUNC_01 = "PY-FUNC-01"


class FakeModelAdapter(ModelAdapter):
    """Configurable adapter for deterministic planner tests."""

    def __init__(
        self,
        *,
        reply: str = "",
        error: Exception | None = None,
    ) -> None:
        self._reply = reply
        self._error = error
        self.requests: list[Sequence[ChatMessage]] = []

    async def complete(
        self, messages: Sequence[ChatMessage]
    ) -> ModelResponse:
        self.requests.append(messages)
        if self._error is not None:
            raise self._error
        return ModelResponse(
            content=self._reply,
            provider="fake",
            model="fake",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )


def make_profile(
    *,
    student_id: str = "s-1",
    course_id: str = PY_COURSE,
    mastery: Sequence[tuple[str, float, int]] = (),
) -> LearnerProfile:
    return LearnerProfile(
        student_id=student_id,
        course_id=course_id,
        mastery=[
            MasteryState(
                knowledge_point_id=knowledge_point_id,
                score=score,
                evidence_count=evidence_count,
            )
            for knowledge_point_id, score, evidence_count in mastery
        ],
    )


def write_pack(
    root: Path,
    *,
    course_id: str,
    concepts: Sequence[dict[str, object]],
    exercises: Sequence[dict[str, object]] = (),
    projects: Sequence[dict[str, object]] = (),
) -> None:
    pack_dir = root / course_id
    (pack_dir / "concepts").mkdir(parents=True)
    (pack_dir / "exercises").mkdir(parents=True)
    (pack_dir / "projects").mkdir(parents=True)
    (pack_dir / "sources").mkdir(parents=True)
    manifest = {
        "schema_version": "0.1.0",
        "course": {
            "id": course_id,
            "title": f"Course {course_id}",
            "status": "draft",
            "target_core_concepts": 40,
            "implemented_core_concepts": len(concepts),
        },
        "content": {
            "concepts_dir": "concepts",
            "exercises_dir": "exercises",
            "projects_dir": "projects",
            "sources_dir": "sources",
        },
        "features": {
            "rag_qa": "planned",
            "adaptive_practice": "planned",
            "debug_tasks": "planned",
            "comprehensive_project": "planned",
        },
        "review": {"content_owner": "成员3", "last_reviewed_at": None},
    }
    (pack_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8"
    )
    for concept in concepts:
        record_id = str(concept["id"])
        (pack_dir / "concepts" / f"{record_id}.yaml").write_text(
            yaml.safe_dump(concept, allow_unicode=True), encoding="utf-8"
        )
    for exercise in exercises:
        record_id = str(exercise["id"])
        (pack_dir / "exercises" / f"{record_id}.yaml").write_text(
            yaml.safe_dump(exercise, allow_unicode=True), encoding="utf-8"
        )
    for project in projects:
        record_id = str(project["id"])
        (pack_dir / "projects" / f"{record_id}.yaml").write_text(
            yaml.safe_dump(project, allow_unicode=True), encoding="utf-8"
        )


def make_python_pack(root: Path) -> None:
    write_pack(
        root,
        course_id=PY_COURSE,
        concepts=[
            {"id": PY_BASE_01, "title": "基础语法", "prerequisites": [], "assessment_ids": []},
            {
                "id": PY_BASE_02,
                "title": "分支循环",
                "prerequisites": [PY_BASE_01],
                "assessment_ids": [],
            },
            {
                "id": PY_FUNC_01,
                "title": "函数",
                "prerequisites": [PY_BASE_01],
                "assessment_ids": [],
            },
        ],
        exercises=[
            {
                "id": f"{PY_BASE_01}-Q1",
                "title": "基础客观题",
                "type": "objective",
                "concept_ids": [PY_BASE_01],
            },
            {
                "id": f"{PY_BASE_01}-C1",
                "title": "基础编程题",
                "type": "code",
                "concept_ids": [PY_BASE_01],
            },
            {
                "id": f"{PY_BASE_02}-Q1",
                "title": "分支客观题",
                "type": "objective",
                "concept_ids": [PY_BASE_02],
            },
        ],
    )


def make_c_pack(root: Path) -> None:
    write_pack(
        root,
        course_id="c",
        concepts=[
            {"id": "C-01", "title": "C 入门", "prerequisites": [], "assessment_ids": []}
        ],
        exercises=[
            {
                "id": "C-01-Q1",
                "title": "C 客观题",
                "type": "objective",
                "concept_ids": ["C-01"],
            }
        ],
    )


def make_ds_pack(root: Path) -> None:
    write_pack(
        root,
        course_id="data_structures",
        concepts=[
            {"id": "DS-01", "title": "线性表", "prerequisites": [], "assessment_ids": []}
        ],
    )


@pytest.fixture
def python_catalog(tmp_path: Path) -> CourseCatalog:
    make_python_pack(tmp_path)
    return load_catalog(PY_COURSE, packs_root=tmp_path)


def run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


def test_planner_returns_model_choice_when_legal(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps(
            {"activity_id": f"{PY_BASE_01}-C1", "activity_type": "code"}
        )
    )
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert isinstance(result, PlannedActivity)
    assert result.activity_id == f"{PY_BASE_01}-C1"
    assert result.activity_type == "code"
    assert result.reason
    assert "巩固" in result.reason


def test_planner_falls_back_when_model_returns_unknown_id(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps({"activity_id": "NOT-EXIST", "activity_type": "concept"})
    )
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id in {
        PY_BASE_01,
        f"{PY_BASE_01}-Q1",
        f"{PY_BASE_01}-C1",
    }


def test_planner_falls_back_when_model_crosses_courses(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps({"activity_id": "C-01", "activity_type": "concept"})
    )
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id in {
        PY_BASE_01,
        f"{PY_BASE_01}-Q1",
        f"{PY_BASE_01}-C1",
    }
    assert result.activity_id != "C-01"


def test_planner_falls_back_when_model_type_mismatches(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps({"activity_id": PY_BASE_01, "activity_type": "code"})
    )
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id in {PY_BASE_01, f"{PY_BASE_01}-Q1", f"{PY_BASE_01}-C1"}


@pytest.mark.parametrize(
    "error",
    [
        ModelTimeoutError("timed out"),
        ModelRateLimitError("rate limited"),
        ModelUpstreamError("upstream failed"),
    ],
)
def test_planner_falls_back_when_model_fails(
    python_catalog: CourseCatalog, error: Exception
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(error=error)
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert isinstance(result, PlannedActivity)
    assert result.activity_id in {PY_BASE_01, f"{PY_BASE_01}-Q1", f"{PY_BASE_01}-C1"}


def test_planner_degrades_with_mock_adapter(python_catalog: CourseCatalog) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=MockAdapter()
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert isinstance(result, PlannedActivity)
    assert result.activity_id == f"{PY_BASE_01}-C1"
    assert result.activity_type == "code"


def test_planner_degrades_on_non_json_model_output(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(reply="抱歉，无法回答")
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id in {PY_BASE_01, f"{PY_BASE_01}-Q1", f"{PY_BASE_01}-C1"}


def test_planner_starts_from_basic_concept_without_history(
    python_catalog: CourseCatalog,
) -> None:
    model = FakeModelAdapter()
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: None, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id == PY_BASE_01
    assert result.activity_type == "concept"
    assert "尚无学习证据" in result.reason or "开始" in result.reason


def test_low_mastery_enters_reinforcement_path(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter()
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_type == "code"
    assert result.activity_id == f"{PY_BASE_01}-C1"


def test_exercise_cannot_bypass_unmet_concept_prerequisite(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_02, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps(
            {"activity_id": f"{PY_BASE_02}-Q1", "activity_type": "objective"}
        )
    )
    planner = LearningPlanner(
        catalog=python_catalog,
        profile_provider=lambda _s, _c: profile,
        model_adapter=model,
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_id == PY_BASE_01
    assert result.activity_id != f"{PY_BASE_02}-Q1"


@pytest.mark.parametrize(
    ("profile", "message"),
    [
        (make_profile(student_id="another-student"), "student_id"),
        (make_profile(course_id="c"), "course_id"),
    ],
)
def test_planner_rejects_profile_for_another_request(
    python_catalog: CourseCatalog,
    profile: LearnerProfile,
    message: str,
) -> None:
    planner = LearningPlanner(
        catalog=python_catalog,
        profile_provider=lambda _s, _c: profile,
        model_adapter=MockAdapter(),
    )

    with pytest.raises(ValueError, match=message):
        run(planner.next_activity("s-1", PY_COURSE))


def test_planner_does_not_hide_programming_errors(
    python_catalog: CourseCatalog,
) -> None:
    planner = LearningPlanner(
        catalog=python_catalog,
        profile_provider=lambda _s, _c: make_profile(),
        model_adapter=FakeModelAdapter(error=RuntimeError("implementation bug")),
    )

    with pytest.raises(RuntimeError, match="implementation bug"):
        run(planner.next_activity("s-1", PY_COURSE))


def test_high_mastery_progresses_to_next_concept(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(
        mastery=[
            (PY_BASE_01, 0.9, 6),
        ]
    )
    model = FakeModelAdapter()
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert result.activity_type == "concept"
    assert result.activity_id == PY_BASE_02
    assert "尚无学习证据" in result.reason


def test_three_courses_reuse_same_planning_logic(tmp_path: Path) -> None:
    make_python_pack(tmp_path)
    make_c_pack(tmp_path)
    make_ds_pack(tmp_path)

    for course_id in (PY_COURSE, "c", "data_structures"):
        planner = build_learning_planner(
            course_id=course_id,
            profile_provider=lambda _s, _c: None,
            model_adapter=MockAdapter(),
            packs_root=str(tmp_path),
        )
        result = run(planner.next_activity("s-1", course_id))
        assert isinstance(result, PlannedActivity)
        assert result.activity_type == "concept"
        assert result.activity_id


def test_course_isolation_blocks_cross_course_ids(tmp_path: Path) -> None:
    make_python_pack(tmp_path)
    make_c_pack(tmp_path)

    python_model = FakeModelAdapter(
        reply=json.dumps({"activity_id": "C-01", "activity_type": "concept"})
    )
    c_model = FakeModelAdapter(
        reply=json.dumps({"activity_id": PY_BASE_01, "activity_type": "concept"})
    )
    python_planner = build_learning_planner(
        course_id=PY_COURSE,
        profile_provider=lambda _s, _c: None,
        model_adapter=python_model,
        packs_root=str(tmp_path),
    )
    c_planner = build_learning_planner(
        course_id="c",
        profile_provider=lambda _s, _c: None,
        model_adapter=c_model,
        packs_root=str(tmp_path),
    )

    python_result = run(python_planner.next_activity("s-1", PY_COURSE))
    c_result = run(c_planner.next_activity("s-1", "c"))

    assert python_result.activity_id != "C-01"
    assert c_result.activity_id != PY_BASE_01


def test_mock_fixed_input_is_reproducible(python_catalog: CourseCatalog) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2), (PY_BASE_02, 0.7, 3)])
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=MockAdapter()
    )

    first = run(planner.next_activity("s-1", PY_COURSE))
    second = run(planner.next_activity("s-1", PY_COURSE))

    assert first == second


def test_reason_does_not_invent_facts(python_catalog: CourseCatalog) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=MockAdapter()
    )

    result = run(planner.next_activity("s-1", PY_COURSE))

    assert "0.40" in result.reason
    assert "满分" not in result.reason
    assert "通过" not in result.reason


def test_prompt_never_sends_personal_information(
    python_catalog: CourseCatalog,
) -> None:
    profile = make_profile(mastery=[(PY_BASE_01, 0.4, 2)])
    model = FakeModelAdapter(
        reply=json.dumps({"activity_id": f"{PY_BASE_01}-C1", "activity_type": "code"})
    )
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: profile, model_adapter=model
    )

    run(planner.next_activity("s-1", PY_COURSE))

    payload = "".join(message.content for message in model.requests[0])
    assert "s-1" not in payload
    assert "姓名" not in payload
    assert "学号" not in payload


def test_catalog_loads_real_python_pack() -> None:
    catalog = load_course_catalog(PY_COURSE)
    assert catalog.course_id == PY_COURSE
    assert len([item for item in catalog.activities if item.activity_type == "concept"]) == 40
    assert len([item for item in catalog.activities if item.activity_type == "objective"]) >= 1


def test_catalog_rejects_missing_course(tmp_path: Path) -> None:
    with pytest.raises(CourseNotFoundError):
        load_catalog("missing", packs_root=tmp_path)


def test_catalog_rejects_activity_with_unknown_concept(tmp_path: Path) -> None:
    write_pack(
        tmp_path,
        course_id=PY_COURSE,
        concepts=[
            {"id": PY_BASE_01, "title": "基础语法", "prerequisites": []}
        ],
        exercises=[
            {
                "id": "PY-UNKNOWN-Q1",
                "title": "错误关联",
                "type": "objective",
                "concept_ids": ["PY-UNKNOWN"],
            }
        ],
    )

    with pytest.raises(CourseCatalogError, match="unknown concept_ids"):
        load_catalog(PY_COURSE, packs_root=tmp_path)


def test_catalog_indexes_multi_concept_activity_for_every_concept(
    tmp_path: Path,
) -> None:
    write_pack(
        tmp_path,
        course_id=PY_COURSE,
        concepts=[
            {"id": PY_BASE_01, "title": "基础语法", "prerequisites": []},
            {"id": PY_BASE_02, "title": "分支循环", "prerequisites": []},
        ],
        exercises=[
            {
                "id": "PY-MULTI-C1",
                "title": "综合题",
                "type": "code",
                "concept_ids": [PY_BASE_01, PY_BASE_02],
            },
            {
                "id": "PY-MULTI-C2",
                "title": "综合题二",
                "type": "code",
                "concept_ids": [PY_BASE_01, PY_BASE_02],
            },
        ],
    )

    catalog = load_catalog(PY_COURSE, packs_root=tmp_path)

    assert [item.activity_id for item in catalog.exercises_for_kp(PY_BASE_01)] == [
        "PY-MULTI-C1",
        "PY-MULTI-C2",
    ]
    assert [item.activity_id for item in catalog.exercises_for_kp(PY_BASE_02)] == [
        "PY-MULTI-C1",
        "PY-MULTI-C2",
    ]


def test_parse_model_choice_accepts_valid_json() -> None:
    choice = parse_model_choice('{"activity_id": "A-1", "activity_type": "concept"}')
    assert choice is not None
    assert choice.activity_id == "A-1"
    assert choice.activity_type == "concept"


def test_parse_model_choice_rejects_invalid_payloads() -> None:
    assert parse_model_choice("not json") is None
    assert parse_model_choice('{"activity_id": "A-1"}') is None
    assert parse_model_choice('{"activity_type": "concept"}') is None
    assert parse_model_choice('{"activity_id": 1, "activity_type": "concept"}') is None
    assert parse_model_choice('{"activity_id": "A-1", "activity_type": "unknown"}') is None


def test_parse_model_choice_accepts_code_fence() -> None:
    choice = parse_model_choice(
        '```json\n{"activity_id": "A-1", "activity_type": "code"}\n```'
    )
    assert choice is not None
    assert choice.activity_id == "A-1"
    assert choice.activity_type == "code"


def test_planner_rejects_wrong_course(python_catalog: CourseCatalog) -> None:
    planner = LearningPlanner(
        catalog=python_catalog, profile_provider=lambda _s, _c: None, model_adapter=MockAdapter()
    )
    with pytest.raises(CourseNotFoundError):
        run(planner.next_activity("s-1", "c"))


def test_planner_rejects_invalid_top_k(python_catalog: CourseCatalog) -> None:
    with pytest.raises(ValueError, match="top_k"):
        LearningPlanner(
            catalog=python_catalog,
            profile_provider=lambda _s, _c: None,
            model_adapter=MockAdapter(),
            top_k=0,
        )


def test_build_planning_messages_only_contains_safe_facts() -> None:
    candidate = RecommendationCandidate(
        knowledge_point_id=PY_BASE_01,
        score=0.4,
        evidence_count=2,
        confidence=0.4,
        priority=0.36,
        reason_code="needs_reinforcement",
    )
    activity = CourseActivity(
        activity_id=f"{PY_BASE_01}-C1",
        activity_type="code",
        title="基础编程题",
        concept_ids=(PY_BASE_01,),
        prerequisites=(),
    )
    messages = build_planning_messages(
        course_id=PY_COURSE, candidates=[candidate], whitelist=[activity]
    )
    payload = json.dumps(
        json.loads(messages[1].content),
        ensure_ascii=False,
    )
    assert "s-1" not in payload
    assert PY_BASE_01 in payload
    assert "code" in payload
