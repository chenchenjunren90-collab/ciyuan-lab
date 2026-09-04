"""The Python catalog keeps one traceable after-class task per core concept."""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[3]
PYTHON_PACK = ROOT / "course_packs" / "python"


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_every_python_concept_has_a_beginner_adapted_homework() -> None:
    concepts = {
        item["id"]: item
        for item in (
            _load(path) for path in sorted((PYTHON_PACK / "concepts").glob("*.yaml"))
        )
    }
    homework = {
        item["id"]: item
        for item in (
            _load(path)
            for path in sorted((PYTHON_PACK / "exercises").glob("*-H1.yaml"))
        )
    }

    assert len(concepts) == 40
    assert len(homework) == 40
    for concept_id, concept in concepts.items():
        exercise_id = f"{concept_id}-H1"
        assert exercise_id in homework
        assert exercise_id in concept["assessment_ids"]
        exercise = homework[exercise_id]
        assert exercise["concept_ids"] == [concept_id]
        assert exercise["extensions"]["learning_stage"] == "after_class"
        assert exercise["extensions"]["audience"] == "chinese_beginner"


def test_homework_has_scaffolding_examples_and_deterministic_boundaries() -> None:
    for path in sorted((PYTHON_PACK / "exercises").glob("*-H1.yaml")):
        exercise = _load(path)
        extensions = exercise["extensions"]
        tests = exercise["evaluation"]["tests"]

        assert len(extensions["scaffolding"]) == 3
        assert extensions["input_format"]
        assert extensions["output_format"]
        assert extensions["constraints"]
        assert extensions["public_examples"]
        assert extensions["reflection_prompt"]
        assert extensions["source_adaptation"]["source_id"].startswith("SRC-PY-")
        assert any(test["visibility"] == "public" for test in tests)
        assert any(test["visibility"] == "hidden" for test in tests)


def test_every_python_concept_has_a_progressive_lesson_card() -> None:
    for path in sorted((PYTHON_PACK / "concepts").glob("*.yaml")):
        concept = _load(path)
        lesson = concept["lesson"]

        assert len(lesson["learning_sequence"]) == 3
        assert lesson["worked_example"]["problem"]
        assert lesson["worked_example"]["code"]
        assert lesson["checkpoint"]["prompt"]
