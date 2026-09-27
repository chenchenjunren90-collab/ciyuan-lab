"""Pinned provenance, classroom integration and adapted exercise oracles.

These tests validate authored data, not sandboxed C compilation/execution.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi.testclient import TestClient

from app.main import app
from app.modules.course_content import CoursePackRepository

ROOT = Path(__file__).resolve().parents[3]
LEDGER = json.loads((ROOT / "docs/external-course-resources.json").read_text(encoding="utf-8"))
RESOURCES = LEDGER["resources"]
REPOSITORY = CoursePackRepository()
CLIENT = TestClient(app)


@pytest.mark.parametrize("item", RESOURCES, ids=lambda item: item["source_id"])
def test_external_provenance_and_review_gate(item: dict[str, Any]) -> None:
    pack = ROOT / "course_packs" / item["course"]
    source = yaml.safe_load((pack / "sources" / f"{item['source_id']}.yaml").read_text("utf-8"))
    provenance = source["extensions"]["provenance"]
    assert re.fullmatch(r"[0-9a-f]{40}", provenance["commit"])
    assert provenance["commit"] == item["commit"]
    assert provenance["repository"] == item["repository"]
    assert provenance["license"] == item["license"]
    assert item["commit"] in source["citation"]["url"]
    assert source["status"] == "draft"
    assert REPOSITORY.get_source(item["course"], item["source_id"]).id == item["source_id"]
    assert source["rag"]["eligible"] is False
    assert provenance["human_review"] == "pending"
    assert item["source_id"] not in {
        entry.id for entry in REPOSITORY.list_rag_source_records(item["course"])
    }
    if item["adaptation"] == "external_link_only":
        assert source["rag"]["content"] == {"mode": "reference_only"}
    for identifier in item["concept_ids"]:
        concept = yaml.safe_load((pack / "concepts" / f"{identifier}.yaml").read_text("utf-8"))
        if "exercise_id" in item:
            assert item["exercise_id"] in concept["assessment_ids"]
        else:
            assert item["source_id"] in concept["source_refs"]
            text = "\n".join(scene["content"] for scene in concept["lesson"]["learning_sequence"])
            assert source["citation"]["url"] in text
            assert item["license"] in text
            response = CLIENT.get(f"/api/v1/courses/{item['course']}/knowledge-points/{identifier}")
            assert response.status_code == 200
            assert source["citation"]["url"] in json.dumps(response.json())


EXERCISES = [item for item in RESOURCES if "exercise_id" in item]


@pytest.mark.parametrize("item", EXERCISES, ids=lambda item: item["exercise_id"])
def test_adapted_exercise_contract_privacy_and_oracle(item: dict[str, Any]) -> None:
    identifier = item["exercise_id"]
    path = ROOT / "course_packs/c/exercises" / f"{identifier}.yaml"
    record = yaml.safe_load(path.read_text("utf-8"))
    assert record["source_refs"] == [item["source_id"]]
    assert record["extensions"]["source_adaptation"]["source_id"] == item["source_id"]
    tests = record["evaluation"]["tests"]
    assert len(tests) >= 7
    for case in tests:
        data = case["input"]
        if identifier.endswith("REVERSE"):
            expected = data[:-1][::-1]
        elif identifier.endswith("LEAP"):
            year = int(data)
            expected = str(int(year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)))
        elif identifier.endswith("RAINDROPS"):
            number = int(data)
            expected = "".join(
                sound
                for divisor, sound in [(3, "Pling"), (5, "Plang"), (7, "Plong")]
                if number % divisor == 0
            ) or str(number)
        else:
            assert identifier.endswith("HAMMING")
            first, second = data[:-1].split("\n")
            expected = str(
                -1
                if len(first) != len(second)
                else sum(a != b for a, b in zip(first, second, strict=True))
            )
        assert case["expected_output"] == expected + "\n", case["id"]
    response = CLIENT.get(f"/api/v1/courses/c/activities/{identifier}")
    assert response.status_code == 200
    public = response.json()
    assert public["evaluation"]["tests"] == [
        test for test in tests if test["visibility"] == "public"
    ]
    assert public["evaluation"]["runtime"]["language"] == "c"
    assert public["source_adaptation"]["source_id"] == item["source_id"]
    assert public["input_format"] and public["output_format"]
    linked = CLIENT.get(
        "/api/v1/courses/c/activities",
        params={"knowledge_point_id": item["concept_ids"][0]},
    )
    assert linked.status_code == 200
    assert identifier in {activity["id"] for activity in linked.json()}
    assert len(public["scaffolding"]) == 3
    runtime = record["evaluation"]["runtime"]
    assert runtime["network_access"] is False
    assert runtime["filesystem_access"] == "isolated"


@pytest.mark.parametrize(
    "path, copyright",
    [
        ("c/sources/EXERCISM-LICENSE.txt", "Copyright (c) 2021 Exercism"),
        ("data_structures/sources/OPENDSA-LICENSE.txt", "Ville Karavirta and Cliff Shaffer"),
    ],
)
def test_mit_notice_is_distributed(path: str, copyright: str) -> None:
    notice = (ROOT / "course_packs" / path).read_text("utf-8")
    assert copyright in notice
    assert "Permission is hereby granted" in notice
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in notice
