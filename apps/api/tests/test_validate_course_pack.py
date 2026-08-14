from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from scripts.validate_course_pack import (
    COURSE_PACKS_ROOT,
    validate_concept_file,
    validate_course_packs,
    validate_exercise_file,
    validate_handoff_file,
    validate_pack,
    validate_project_file,
    validate_source_file,
)


def course_prefix(course_id: str) -> str:
    return {"c": "C", "python": "PY", "data_structures": "DS"}[course_id]


def make_source(
    *,
    course_id: str = "python",
    source_id: str | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    prefix = course_prefix(course_id)
    return {
        "id": source_id or f"SRC-{prefix}-TEST-01",
        "title": "测试课程来源",
        "course": course_id,
        "schema_version": "0.1.0",
        "version": 1,
        "source_type": "synthetic",
        "citation": {"locator": "测试夹具自编材料"},
        "rights": {"basis": "synthetic", "note": "测试夹具合成内容"},
        "data_classification": "synthetic",
        "rag": {
            "eligible": status == "reviewed",
            "content": {"mode": "inline", "text": "用于课程包校验器测试的合成正文。"},
        },
        "status": status,
    }


def make_concept(
    concept_id: str,
    *,
    course_id: str = "python",
    prerequisites: list[str] | None = None,
    assessment_ids: list[str] | None = None,
    source_refs: list[str] | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    prefix = course_prefix(course_id)
    return {
        "id": concept_id,
        "title": "示例知识点",
        "course": course_id,
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "beginner",
        "estimated_minutes": 20,
        "prerequisites": prerequisites or [],
        "learning_objectives": ["能够完成可验证任务"],
        "concepts": ["示例概念"],
        "lesson": {"summary": "这是用于校验器测试的完整学习卡摘要。"},
        "assessment_ids": assessment_ids if assessment_ids is not None else [f"{concept_id}-Q1"],
        "source_refs": source_refs if source_refs is not None else [f"SRC-{prefix}-TEST-01"],
        "status": status,
    }


def make_objective_exercise(
    exercise_id: str,
    concept_ids: list[str],
    *,
    course_id: str = "python",
    source_refs: list[str] | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    prefix = course_prefix(course_id)
    return {
        "id": exercise_id,
        "title": "示例客观题",
        "course": course_id,
        "schema_version": "0.1.0",
        "version": 1,
        "type": "objective",
        "difficulty": "beginner",
        "estimated_minutes": 5,
        "concept_ids": concept_ids,
        "prompt": "请选择正确答案。",
        "source_refs": source_refs if source_refs is not None else [f"SRC-{prefix}-TEST-01"],
        "evaluation": {
            "mode": "exact",
            "options": [{"id": "A", "text": "正确"}, {"id": "B", "text": "错误"}],
            "accepted_answers": ["A"],
        },
        "status": status,
    }


def make_code_exercise(
    exercise_id: str,
    concept_ids: list[str],
    *,
    course_id: str = "python",
    status: str = "draft",
) -> dict[str, Any]:
    prefix = course_prefix(course_id)
    language = "c" if course_id == "c" else "python"
    version = "C17" if language == "c" else "3.11"
    entrypoint = "main.c" if language == "c" else "main.py"
    return {
        "id": exercise_id,
        "title": "示例代码题",
        "course": course_id,
        "schema_version": "0.1.0",
        "version": 1,
        "type": "code",
        "difficulty": "beginner",
        "estimated_minutes": 15,
        "concept_ids": concept_ids,
        "prompt": "读取两个整数并输出它们的和。",
        "source_refs": [f"SRC-{prefix}-TEST-01"],
        "evaluation": {
            "mode": "tests",
            "runtime": {
                "language": language,
                "version": version,
                "entrypoint": entrypoint,
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "output_limit_kb": 64,
                "network_access": False,
                "filesystem_access": "isolated",
            },
            "tests": [
                {
                    "id": "public-01",
                    "visibility": "public",
                    "input": "1 2\n",
                    "expected_output": "3\n",
                },
                {
                    "id": "hidden-01",
                    "visibility": "hidden",
                    "input": "-1 2\n",
                    "expected_output": "1\n",
                },
            ],
        },
        "status": status,
    }


def make_short_answer_exercise(
    exercise_id: str,
    concept_ids: list[str],
) -> dict[str, Any]:
    exercise = make_objective_exercise(exercise_id, concept_ids)
    exercise["type"] = "short_answer"
    exercise["prompt"] = "请解释该概念并给出一个例子。"
    exercise["evaluation"] = {
        "mode": "rubric",
        "max_score": 10,
        "rubric": [
            {"criterion": "概念解释正确", "points": 6},
            {"criterion": "示例合理", "points": 4},
        ],
    }
    return exercise


def make_debug_exercise(
    exercise_id: str,
    concept_ids: list[str],
) -> dict[str, Any]:
    exercise = make_code_exercise(exercise_id, concept_ids)
    exercise["type"] = "debug"
    exercise["evaluation"]["starter_code"] = "print(0)"
    return exercise


def make_project(
    project_id: str,
    concept_ids: list[str],
    *,
    course_id: str = "python",
    status: str = "draft",
) -> dict[str, Any]:
    prefix = course_prefix(course_id)
    return {
        "id": project_id,
        "title": "示例综合项目",
        "course": course_id,
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "intermediate",
        "estimated_minutes": 90,
        "concept_ids": concept_ids,
        "summary": "综合运用多个知识点完成可验证任务。",
        "requirements": ["实现核心流程", "处理边界输入"],
        "deliverables": ["可运行代码", "结果说明"],
        "source_refs": [f"SRC-{prefix}-TEST-01"],
        "verification_exercise_ids": [f"{prefix}-BASE-01-C1"],
        "scenario_scope": "none",
        "scenario_provider": "none",
        "data_classification": "synthetic",
        "computer_science_objectives": ["运用函数和数据结构解决问题"],
        "business_context_objectives": [],
        "evaluation": {
            "mode": "rubric",
            "max_score": 10,
            "rubric": [
                {"criterion": "确定性结果正确", "points": 6},
                {"criterion": "代码结构清晰", "points": 4},
            ],
        },
        "status": status,
    }


def make_handoff(
    concept_ids: list[str],
    *,
    source_id: str = "SRC-PY-TEST-01",
    objective_exercise_id: str = "PY-BASE-01-Q1",
    practice_exercise_id: str = "PY-BASE-01-C1",
    project_id: str = "PY-PROJ-01",
    status: str = "draft",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "course_id": "python",
        "package_revision": "develop@0123456",
        "status": status,
        "representative_content": {
            "concept_ids": concept_ids,
            "objective_exercise_id": objective_exercise_id,
            "practice_exercise_id": practice_exercise_id,
            "project_id": project_id,
        },
        "source_refs": [source_id],
        "golden_questions": [
            {
                "id": f"GQ-{index:02d}",
                "question": f"黄金问题{index}",
                "expected_source_refs": [source_id],
            }
            for index in range(1, 6)
        ],
        "insufficient_evidence_questions": [{"id": "IQ-01", "question": "材料外问题"}],
        "wrong_citation_examples": [
            {
                "id": "WQ-01",
                "question": "错误引用问题",
                "incorrect_source_ref": source_id,
                "reason": "该来源不能支持示例结论",
            }
        ],
        "verification_samples": [
            {
                "id": "VS-OK",
                "exercise_id": practice_exercise_id,
                "language": "python",
                "source_code": "print(sum(map(int, input().split())))",
                "expected": {"accepted": True, "passed_tests": 2, "total_tests": 2},
            },
            {
                "id": "VS-BAD",
                "exercise_id": practice_exercise_id,
                "language": "python",
                "source_code": "print(0)",
                "expected": {"accepted": False, "passed_tests": 0, "total_tests": 2},
            },
        ],
        "demo_path": ["进入课程", "完成练习", "查看下一任务"],
        "known_limitations": ["测试交接夹具"],
    }


def write_document(path: Path, document: dict[str, Any], file_format: str = "yaml") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (
        json.dumps(document, ensure_ascii=False, indent=2)
        if file_format == "json"
        else yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
    )
    path.write_text(serialized, encoding="utf-8")


def make_pack(
    tmp_path: Path,
    *,
    course_id: str = "python",
    concepts: list[dict[str, Any]] | None = None,
    exercises: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
    handoff: dict[str, Any] | None = None,
    course_status: str = "draft",
    formats: dict[str, str] | None = None,
) -> Path:
    concepts = concepts or []
    exercises = exercises or []
    sources = sources or []
    projects = projects or []
    formats = formats or {}
    pack_dir = tmp_path / course_id
    for directory in ("concepts", "exercises", "projects", "sources"):
        (pack_dir / directory).mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "0.1.0",
        "course": {
            "id": course_id,
            "title": "测试课程",
            "status": course_status,
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
        "review": {"content_owner": "test-owner", "last_reviewed_at": None},
    }
    write_document(pack_dir / "manifest.yaml", manifest)
    for kind, records in (
        ("concepts", concepts),
        ("exercises", exercises),
        ("sources", sources),
        ("projects", projects),
    ):
        file_format = formats.get(kind, "yaml")
        suffix = "json" if file_format == "json" else "yaml"
        for record in records:
            write_document(pack_dir / kind / f"{record['id']}.{suffix}", record, file_format)
    if handoff is not None:
        write_document(pack_dir / "handoff.yaml", handoff)
    return pack_dir


def test_current_empty_course_scaffolds_remain_valid() -> None:
    pack_dirs = sorted(
        path
        for path in COURSE_PACKS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    )

    assert validate_course_packs(pack_dirs) == []


def test_all_template_examples_match_their_record_schema(tmp_path: Path) -> None:
    template = COURSE_PACKS_ROOT / "_template"
    pack_dir = tmp_path / "python"
    for directory in ("concepts", "exercises", "projects", "sources"):
        (pack_dir / directory).mkdir(parents=True, exist_ok=True)

    concept = yaml.safe_load(
        (template / "concepts" / "PY-FUNC-01.example.yaml").read_text(encoding="utf-8")
    )
    concept_path = pack_dir / "concepts" / f"{concept['id']}.yaml"
    write_document(concept_path, concept)
    concept_errors, _ = validate_concept_file(
        concept_path, course_id="python", expected_prefix="PY-"
    )

    exercise_errors: list[str] = []
    for example in sorted((template / "exercises").glob("*.example.yaml")):
        exercise = yaml.safe_load(example.read_text(encoding="utf-8"))
        exercise_path = pack_dir / "exercises" / f"{exercise['id']}.yaml"
        write_document(exercise_path, exercise)
        errors, _ = validate_exercise_file(exercise_path, course_id="python", expected_prefix="PY-")
        exercise_errors.extend(errors)

    source = yaml.safe_load(
        (template / "sources" / "SRC-PY-OUTLINE-01.example.yaml").read_text(encoding="utf-8")
    )
    source_path = pack_dir / "sources" / f"{source['id']}.yaml"
    write_document(source_path, source)
    source_errors, _ = validate_source_file(
        source_path,
        pack_dir=pack_dir,
        course_id="python",
        expected_prefix="SRC-PY-",
    )

    project = yaml.safe_load(
        (template / "projects" / "PY-PROJ-DATA-01.example.yaml").read_text(encoding="utf-8")
    )
    project_path = pack_dir / "projects" / f"{project['id']}.yaml"
    write_document(project_path, project)
    project_errors, _ = validate_project_file(
        project_path, course_id="python", expected_prefix="PY-"
    )

    handoff = yaml.safe_load((template / "handoff.example.yaml").read_text(encoding="utf-8"))
    handoff_path = pack_dir / "handoff.yaml"
    write_document(handoff_path, handoff)
    handoff_errors, _ = validate_handoff_file(handoff_path, course_id="python")

    assert [
        *concept_errors,
        *exercise_errors,
        *source_errors,
        *project_errors,
        *handoff_errors,
    ] == []


def test_valid_yaml_and_json_records_with_prerequisite_pass(tmp_path: Path) -> None:
    source = make_source()
    base = make_concept("PY-BASE-01")
    function = make_concept("PY-FUNC-01", prerequisites=["PY-BASE-01"])
    pack_dir = make_pack(
        tmp_path,
        concepts=[base, function],
        exercises=[
            make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"]),
            make_objective_exercise("PY-FUNC-01-Q1", ["PY-FUNC-01"]),
        ],
        sources=[source],
        formats={"concepts": "json", "exercises": "yaml", "sources": "json"},
    )

    assert validate_pack(pack_dir) == []


def test_required_unknown_and_filename_fields_are_rejected(tmp_path: Path) -> None:
    concept = make_concept("PY-BASE-01")
    concept["title"] = ""
    concept["learning_objectives"] = []
    concept["unexpected"] = True
    pack_dir = make_pack(
        tmp_path,
        concepts=[concept],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[make_source()],
    )
    original = pack_dir / "concepts" / "PY-BASE-01.yaml"
    original.rename(pack_dir / "concepts" / "wrong-name.yaml")

    errors = validate_pack(pack_dir)

    assert any("title must be a non-empty string" in error for error in errors)
    assert any("learning_objectives must contain at least 1" in error for error in errors)
    assert any("unsupported fields: unexpected" in error for error in errors)
    assert any("filename must be PY-BASE-01.yaml" in error for error in errors)


def test_non_string_keys_and_surrounding_whitespace_are_rejected(tmp_path: Path) -> None:
    concept = make_concept("PY-BASE-01")
    concept[1] = "not-a-field-name"  # type: ignore[index]
    concept["source_refs"] = [" SRC-PY-TEST-01"]
    objective = make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])
    objective["evaluation"]["options"][0]["id"] = " A"
    pack_dir = make_pack(
        tmp_path,
        concepts=[concept],
        exercises=[objective],
        sources=[make_source()],
    )

    errors = validate_pack(pack_dir)

    assert any("field names must be strings" in error for error in errors)
    assert any(
        "source_refs items must not have surrounding whitespace" in error for error in errors
    )
    assert any("id must not have surrounding whitespace" in error for error in errors)


def test_duplicate_missing_reference_and_cycle_are_rejected(tmp_path: Path) -> None:
    source = make_source()
    first = make_concept("PY-A-01", prerequisites=["PY-B-01"])
    second = make_concept("PY-B-01", prerequisites=["PY-A-01"])
    second["assessment_ids"] = ["PY-MISSING-Q1"]
    second["source_refs"] = ["SRC-PY-MISSING-01"]
    pack_dir = make_pack(
        tmp_path,
        concepts=[first, second],
        exercises=[make_objective_exercise("PY-A-01-Q1", ["PY-A-01"])],
        sources=[source],
    )
    duplicate = make_concept("PY-DUP-01")
    write_document(pack_dir / "concepts" / "PY-DUP-01.yaml", duplicate)
    write_document(pack_dir / "concepts" / "PY-DUP-01.json", duplicate, "json")

    errors = validate_pack(pack_dir)

    assert any("duplicate content id PY-DUP-01" in error for error in errors)
    assert any("assessment reference PY-MISSING-Q1 does not exist" in error for error in errors)
    assert any("source reference SRC-PY-MISSING-01 does not exist" in error for error in errors)
    assert any("prerequisite cycle detected" in error for error in errors)


def test_exercise_answer_and_safe_runtime_rules_are_enforced(tmp_path: Path) -> None:
    objective = make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])
    objective["evaluation"]["accepted_answers"] = ["Z"]
    code = make_code_exercise("PY-BASE-01-C1", ["PY-BASE-01"])
    code["evaluation"]["runtime"]["network_access"] = True
    code["evaluation"]["tests"] = [code["evaluation"]["tests"][0]]
    concept = make_concept("PY-BASE-01", assessment_ids=["PY-BASE-01-Q1", "PY-BASE-01-C1"])
    pack_dir = make_pack(
        tmp_path,
        concepts=[concept],
        exercises=[objective, code],
        sources=[make_source()],
    )

    errors = validate_pack(pack_dir)

    assert any("accepted_answers reference unknown options: Z" in error for error in errors)
    assert any("runtime.network_access must be false" in error for error in errors)
    assert any("require at least one public and one hidden test" in error for error in errors)


def test_unsafe_or_unrepeatable_runtime_declarations_are_rejected(tmp_path: Path) -> None:
    code = make_code_exercise("PY-BASE-01-C1", ["PY-BASE-01"])
    runtime = code["evaluation"]["runtime"]
    runtime["version"] = "latest"
    runtime["entrypoint"] = "../../outside.py"
    runtime["time_limit_ms"] = 10**12
    runtime["memory_limit_mb"] = 10**12
    runtime["output_limit_kb"] = 10**12
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01", assessment_ids=["PY-BASE-01-C1"])],
        exercises=[code],
        sources=[make_source()],
    )

    errors = validate_pack(pack_dir)

    assert any("runtime.version must be 3.11" in error for error in errors)
    assert any("runtime.entrypoint must be a plain filename" in error for error in errors)
    assert any("runtime.time_limit_ms must be between 100 and 10000" in error for error in errors)
    assert any("runtime.memory_limit_mb must be between 16 and 512" in error for error in errors)
    assert any("runtime.output_limit_kb must be between 1 and 1024" in error for error in errors)


def test_short_answer_and_debug_variants_pass(tmp_path: Path) -> None:
    concept = make_concept(
        "PY-BASE-01",
        assessment_ids=["PY-BASE-01-S1", "PY-BASE-01-D1"],
    )
    pack_dir = make_pack(
        tmp_path,
        concepts=[concept],
        exercises=[
            make_short_answer_exercise("PY-BASE-01-S1", ["PY-BASE-01"]),
            make_debug_exercise("PY-BASE-01-D1", ["PY-BASE-01"]),
        ],
        sources=[make_source()],
    )

    assert validate_pack(pack_dir) == []


def test_c_and_data_structures_accept_only_their_supported_runtimes(tmp_path: Path) -> None:
    c_pack = make_pack(
        tmp_path,
        course_id="c",
        concepts=[
            make_concept(
                "C-BASE-01",
                course_id="c",
                assessment_ids=["C-BASE-01-C1"],
            )
        ],
        exercises=[make_code_exercise("C-BASE-01-C1", ["C-BASE-01"], course_id="c")],
        sources=[make_source(course_id="c")],
    )
    ds_pack = make_pack(
        tmp_path,
        course_id="data_structures",
        concepts=[
            make_concept(
                "DS-BASE-01",
                course_id="data_structures",
                assessment_ids=["DS-BASE-01-C1"],
            )
        ],
        exercises=[
            make_code_exercise(
                "DS-BASE-01-C1",
                ["DS-BASE-01"],
                course_id="data_structures",
            )
        ],
        sources=[make_source(course_id="data_structures")],
    )

    assert validate_pack(c_pack) == []
    assert validate_pack(ds_pack) == []


def test_c_and_python_reject_each_others_runtime(tmp_path: Path) -> None:
    python_code = make_code_exercise("PY-BASE-01-C1", ["PY-BASE-01"])
    python_code["evaluation"]["runtime"].update(
        {"language": "c", "version": "C17", "entrypoint": "main.c"}
    )
    python_pack = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01", assessment_ids=["PY-BASE-01-C1"])],
        exercises=[python_code],
        sources=[make_source()],
    )

    c_code = make_code_exercise("C-BASE-01-C1", ["C-BASE-01"], course_id="c")
    c_code["evaluation"]["runtime"].update(
        {"language": "python", "version": "3.11", "entrypoint": "main.py"}
    )
    c_pack = make_pack(
        tmp_path,
        course_id="c",
        concepts=[
            make_concept(
                "C-BASE-01",
                course_id="c",
                assessment_ids=["C-BASE-01-C1"],
            )
        ],
        exercises=[c_code],
        sources=[make_source(course_id="c")],
    )

    errors = [*validate_pack(python_pack), *validate_pack(c_pack)]

    assert any("runtime.language must be python for course python" in error for error in errors)
    assert any("runtime.language must be c for course c" in error for error in errors)


def test_source_rights_and_path_escape_are_rejected(tmp_path: Path) -> None:
    source = make_source()
    source["rights"] = {"basis": "open_license", "note": "不匹配的授权说明"}
    source["data_classification"] = "authorized_desensitized"
    source["rag"] = {"eligible": True, "content": {"mode": "file", "path": "../secret.txt"}}
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01")],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[source],
    )

    errors = validate_pack(pack_dir)

    assert any(
        "authorized_desensitized sources require authorized rights" in error for error in errors
    )
    assert any("rag.content.path must stay inside sources/" in error for error in errors)


def test_synthetic_source_requires_consistent_rights_and_classification(tmp_path: Path) -> None:
    source = make_source()
    source["rights"] = {"basis": "open_license", "note": "incorrect synthetic declaration"}
    source["data_classification"] = "public"
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01")],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[source],
    )

    errors = validate_pack(pack_dir)

    assert any(
        "source_type synthetic requires synthetic rights and classification" in error
        for error in errors
    )


def test_only_reviewed_sources_can_be_marked_rag_eligible(tmp_path: Path) -> None:
    draft_source = make_source()
    draft_source["rag"]["eligible"] = True
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01")],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[draft_source],
    )

    errors = validate_pack(pack_dir)
    assert any("only reviewed sources may be RAG eligible" in error for error in errors)

    reviewed_source = make_source(status="reviewed")
    write_document(pack_dir / "sources" / "SRC-PY-TEST-01.yaml", reviewed_source)
    assert validate_pack(pack_dir) == []


def test_finance_project_rules_and_rubric_are_enforced(tmp_path: Path) -> None:
    project = make_project("PY-PROJ-01", ["PY-A-01", "PY-B-01"])
    project["scenario_scope"] = "post_course_finance_practice"
    project["scenario_provider"] = "none"
    project["business_context_objectives"] = []
    project["evaluation"]["max_score"] = 9
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-A-01"), make_concept("PY-B-01")],
        exercises=[
            make_objective_exercise("PY-A-01-Q1", ["PY-A-01"]),
            make_objective_exercise("PY-B-01-Q1", ["PY-B-01"]),
        ],
        sources=[make_source()],
        projects=[project],
    )

    errors = validate_pack(pack_dir)

    assert any(
        "finance practice requires tuoling or fixed_synthetic provider" in error for error in errors
    )
    assert any("finance practice requires business_context_objectives" in error for error in errors)
    assert any("rubric points must sum to max_score" in error for error in errors)


def test_finance_scope_and_fixed_synthetic_source_are_enforced(tmp_path: Path) -> None:
    project = make_project("PY-PROJ-01", ["PY-A-01", "PY-B-01"])
    project["business_context_objectives"] = ["should not appear in a non-finance project"]
    source = make_source()
    source.update(
        {
            "source_type": "open_resource",
            "rights": {"basis": "open_license", "note": "public test source"},
            "data_classification": "public",
        }
    )
    pack_dir = make_pack(
        tmp_path,
        concepts=[
            make_concept("PY-A-01", assessment_ids=["PY-BASE-01-C1"]),
            make_concept("PY-B-01", assessment_ids=["PY-BASE-01-C1"]),
        ],
        exercises=[make_code_exercise("PY-BASE-01-C1", ["PY-A-01", "PY-B-01"])],
        sources=[source],
        projects=[project],
    )

    errors = validate_pack(pack_dir)
    assert any("must not define business_context_objectives" in error for error in errors)

    project["scenario_scope"] = "post_course_finance_practice"
    project["scenario_provider"] = "fixed_synthetic"
    project["data_classification"] = "public"
    write_document(pack_dir / "projects" / "PY-PROJ-01.yaml", project)
    errors = validate_pack(pack_dir)

    assert any(
        "fixed_synthetic projects must use synthetic data_classification" in error
        for error in errors
    )
    assert any(
        "fixed_synthetic projects require at least one consistently declared synthetic source"
        in error
        for error in errors
    )


def test_tuoling_project_requires_fixed_synthetic_fallback(tmp_path: Path) -> None:
    project = make_project("PY-PROJ-01", ["PY-A-01", "PY-B-01"])
    project["scenario_scope"] = "post_course_finance_practice"
    project["scenario_provider"] = "tuoling"
    project["business_context_objectives"] = ["理解字段含义"]
    pack_dir = make_pack(
        tmp_path,
        concepts=[
            make_concept("PY-A-01", assessment_ids=["PY-BASE-01-C1"]),
            make_concept("PY-B-01", assessment_ids=["PY-BASE-01-C1"]),
        ],
        exercises=[make_code_exercise("PY-BASE-01-C1", ["PY-A-01", "PY-B-01"])],
        sources=[make_source()],
        projects=[project],
    )

    errors = validate_pack(pack_dir)
    assert any("tuoling projects require a fixed_synthetic fallback" in error for error in errors)

    project["fallback"] = {
        "mode": "fixed_synthetic",
        "source_refs": ["SRC-PY-TEST-01"],
        "note": "驼灵不可用时使用固定合成背景",
    }
    write_document(pack_dir / "projects" / "PY-PROJ-01.yaml", project)
    assert validate_pack(pack_dir) == []

    public_source = make_source()
    public_source.update(
        {
            "source_type": "open_resource",
            "rights": {"basis": "open_license", "note": "public test source"},
            "data_classification": "public",
        }
    )
    write_document(pack_dir / "sources" / "SRC-PY-TEST-01.yaml", public_source)
    errors = validate_pack(pack_dir)
    assert any("fallback source SRC-PY-TEST-01 must be" in error for error in errors)


def test_complete_handoff_passes_and_broken_handoff_is_rejected(tmp_path: Path) -> None:
    concept_ids = ["PY-BASE-01", "PY-FUNC-01", "PY-FILE-01"]
    concepts = [
        make_concept(
            concept_id,
            assessment_ids=["PY-BASE-01-Q1", "PY-BASE-01-C1"],
        )
        for concept_id in concept_ids
    ]
    handoff = make_handoff(concept_ids)
    pack_dir = make_pack(
        tmp_path,
        concepts=concepts,
        exercises=[
            make_objective_exercise("PY-BASE-01-Q1", concept_ids),
            make_code_exercise("PY-BASE-01-C1", concept_ids),
        ],
        sources=[make_source()],
        projects=[make_project("PY-PROJ-01", concept_ids[:2])],
        handoff=handoff,
    )

    assert validate_pack(pack_dir) == []

    handoff["golden_questions"] = handoff["golden_questions"][:1]
    handoff["representative_content"]["practice_exercise_id"] = "PY-BASE-01-Q1"
    write_document(pack_dir / "handoff.yaml", handoff)
    errors = validate_pack(pack_dir)

    assert any("golden_questions must contain at least 5" in error for error in errors)
    assert any("practice_exercise_id must reference code or debug" in error for error in errors)


def test_handoff_revision_language_and_test_count_must_match(tmp_path: Path) -> None:
    concept_ids = ["PY-BASE-01", "PY-FUNC-01", "PY-FILE-01"]
    handoff = make_handoff(concept_ids)
    handoff["package_revision"] = "develop@placeholder"
    handoff["verification_samples"][0]["language"] = "c"
    handoff["verification_samples"][1]["expected"]["total_tests"] = 99
    pack_dir = make_pack(
        tmp_path,
        concepts=[
            make_concept(
                concept_id,
                assessment_ids=["PY-BASE-01-Q1", "PY-BASE-01-C1"],
            )
            for concept_id in concept_ids
        ],
        exercises=[
            make_objective_exercise("PY-BASE-01-Q1", concept_ids),
            make_code_exercise("PY-BASE-01-C1", concept_ids),
        ],
        sources=[make_source()],
        projects=[make_project("PY-PROJ-01", concept_ids[:2])],
        handoff=handoff,
    )

    errors = validate_pack(pack_dir)

    assert any("package_revision must match" in error for error in errors)
    assert any("verification sample language c does not match" in error for error in errors)
    assert any("expected.total_tests does not match" in error for error in errors)


def test_reviewed_handoff_cannot_hide_a_draft_verification_exercise(tmp_path: Path) -> None:
    concept_ids = ["PY-BASE-01", "PY-FUNC-01", "PY-FILE-01"]
    handoff = make_handoff(concept_ids, status="reviewed")
    for sample in handoff["verification_samples"]:
        sample["exercise_id"] = "PY-BASE-01-C2"
    pack_dir = make_pack(
        tmp_path,
        concepts=[
            make_concept(
                concept_id,
                assessment_ids=["PY-BASE-01-Q1", "PY-BASE-01-C1"],
                status="reviewed",
            )
            for concept_id in concept_ids
        ],
        exercises=[
            make_objective_exercise("PY-BASE-01-Q1", concept_ids, status="reviewed"),
            make_code_exercise("PY-BASE-01-C1", concept_ids, status="reviewed"),
            make_code_exercise("PY-BASE-01-C2", concept_ids),
        ],
        sources=[make_source(status="reviewed")],
        projects=[make_project("PY-PROJ-01", concept_ids[:2], status="reviewed")],
        handoff=handoff,
    )

    errors = validate_pack(pack_dir)

    assert any("reviewed handoff references draft content" in error for error in errors)


def test_reviewed_handoff_golden_sources_must_be_rag_eligible(tmp_path: Path) -> None:
    concept_ids = ["PY-BASE-01", "PY-FUNC-01", "PY-FILE-01"]
    source = make_source(status="reviewed")
    source["rag"]["eligible"] = False
    handoff = make_handoff(concept_ids, status="reviewed")
    pack_dir = make_pack(
        tmp_path,
        concepts=[
            make_concept(
                concept_id,
                assessment_ids=["PY-BASE-01-Q1", "PY-BASE-01-C1"],
                status="reviewed",
            )
            for concept_id in concept_ids
        ],
        exercises=[
            make_objective_exercise("PY-BASE-01-Q1", concept_ids, status="reviewed"),
            make_code_exercise("PY-BASE-01-C1", concept_ids, status="reviewed"),
        ],
        sources=[source],
        projects=[make_project("PY-PROJ-01", concept_ids[:2], status="reviewed")],
        handoff=handoff,
    )

    errors = validate_pack(pack_dir)

    assert any("golden question source SRC-PY-TEST-01 must be" in error for error in errors)


def test_reviewed_records_cannot_reference_drafts(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01", status="reviewed")],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[make_source()],
    )

    errors = validate_pack(pack_dir)

    assert any("reviewed content references draft" in error for error in errors)


def test_manifest_and_published_release_gates_are_enforced(tmp_path: Path) -> None:
    pack_dir = make_pack(
        tmp_path,
        concepts=[make_concept("PY-BASE-01")],
        exercises=[make_objective_exercise("PY-BASE-01-Q1", ["PY-BASE-01"])],
        sources=[make_source()],
        course_status="published",
    )
    manifest_path = pack_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["content"]["concepts_dir"] = "wrong"
    write_document(manifest_path, manifest)

    errors = validate_pack(pack_dir)

    assert any("content.concepts_dir must be concepts" in error for error in errors)
    assert any("review/published courses require last_reviewed_at" in error for error in errors)
    assert any("published courses must reach target_core_concepts" in error for error in errors)
    assert any("published courses require at least one project" in error for error in errors)
    assert any("published courses may contain only reviewed records" in error for error in errors)
    assert any("published courses require a reviewed handoff.yaml" in error for error in errors)
