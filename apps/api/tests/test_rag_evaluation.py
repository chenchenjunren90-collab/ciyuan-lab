import json
from pathlib import Path

import pytest

from app.modules.rag.evaluation import load_eval_cases

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "evals" / "rag" / "retrieval-v1.jsonl"


def test_retrieval_eval_set_has_balanced_course_and_query_types() -> None:
    cases = load_eval_cases(DATASET)

    assert len(cases) == 75
    assert len({case.id for case in cases}) == 75
    for course_id in ("c", "python", "data_structures"):
        course_cases = [case for case in cases if case.course_id == course_id]
        assert len(course_cases) == 25
        assert sum(case.kind == "answerable" for case in course_cases) == 15
        assert sum(case.kind == "unanswerable" for case in course_cases) == 5
        assert sum(case.kind == "cross_course" for case in course_cases) == 5


def test_eval_loader_rejects_answerable_case_without_expected_source(tmp_path: Path) -> None:
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "bad-1",
                "course_id": "c",
                "query": "有效问题",
                "kind": "answerable",
                "expected_source_ids": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 1"):
        load_eval_cases(path)
