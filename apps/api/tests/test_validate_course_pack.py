from __future__ import annotations

import json
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from scripts.validate_course_pack import (
    COURSE_PACKS_ROOT,
    validate_course_packs,
    validate_pack,
)


def make_concept(
    concept_id: str,
    *,
    course: str = "python",
    prerequisites: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": concept_id,
        "title": "示例知识点",
        "course": course,
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "beginner",
        "estimated_minutes": 20,
        "prerequisites": prerequisites or [],
        "learning_objectives": ["能够完成可验证任务"],
        "concepts": ["示例概念"],
        "lesson": {"summary": "这是用于校验器测试的完整学习卡摘要。"},
        "assessment_ids": [f"{concept_id}-Q1"],
        "source_refs": ["SRC-TEST-01"],
        "status": "draft",
    }


def make_pack(
    tmp_path: Path,
    concepts: list[dict[str, object]],
    *,
    course_id: str = "python",
    concept_format: str = "json",
) -> Path:
    pack_dir = tmp_path / course_id
    for directory in ("concepts", "exercises", "projects", "sources"):
        (pack_dir / directory).mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "0.1.0",
        "course": {
            "id": course_id,
            "title": "测试课程",
            "status": "draft",
            "target_core_concepts": 40,
            "implemented_core_concepts": len(concepts),
        },
    }
    (pack_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8"
    )
    for index, concept in enumerate(concepts, start=1):
        concept_path = pack_dir / "concepts" / f"concept-{index}.{concept_format}"
        serialized = (
            yaml.safe_dump(concept, allow_unicode=True)
            if concept_format == "yaml"
            else json.dumps(concept, ensure_ascii=False)
        )
        concept_path.write_text(serialized, encoding="utf-8")
    return pack_dir


def test_current_empty_course_scaffolds_remain_valid() -> None:
    pack_dirs = sorted(
        path
        for path in COURSE_PACKS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    )

    assert validate_course_packs(pack_dirs) == []


def test_valid_concepts_and_existing_prerequisite_pass(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        [
            make_concept("PY-BASE-01"),
            make_concept("PY-FUNC-01", prerequisites=["PY-BASE-01"]),
        ],
    )

    assert validate_pack(pack_dir) == []


def test_yaml_concept_files_are_supported(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        [make_concept("PY-BASE-01")],
        concept_format="yaml",
    )

    assert validate_pack(pack_dir) == []


def test_required_fields_and_non_empty_mappings_are_enforced(tmp_path: Path) -> None:
    concept = make_concept("PY-FUNC-01")
    concept.pop("title")
    concept["learning_objectives"] = []
    concept["assessment_ids"] = []
    concept["source_refs"] = []
    concept["lesson"] = {"summary": ""}
    pack_dir = make_pack(tmp_path, [concept])

    errors = validate_pack(pack_dir)

    assert any("title must be a non-empty string" in error for error in errors)
    assert any("learning_objectives must not be empty" in error for error in errors)
    assert any("assessment_ids must not be empty" in error for error in errors)
    assert any("source_refs must not be empty" in error for error in errors)
    assert any("lesson.summary must be a non-empty string" in error for error in errors)


def test_course_prefix_duplicate_and_missing_prerequisite_are_rejected(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        [
            make_concept(
                "C-BASE-01",
                course="c",
                prerequisites=["PY-MISSING-01"],
            ),
            make_concept("C-BASE-01"),
        ],
    )

    errors = validate_pack(pack_dir)

    assert any("id must start with PY-" in error for error in errors)
    assert any("course must be python" in error for error in errors)
    assert any("duplicate concept id C-BASE-01" in error for error in errors)
    assert any("prerequisite PY-MISSING-01 does not exist" in error for error in errors)


def test_prerequisite_cycle_is_rejected(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        [
            make_concept("PY-A-01", prerequisites=["PY-B-01"]),
            make_concept("PY-B-01", prerequisites=["PY-A-01"]),
        ],
    )

    errors = validate_pack(pack_dir)

    assert any("prerequisite cycle detected" in error for error in errors)
