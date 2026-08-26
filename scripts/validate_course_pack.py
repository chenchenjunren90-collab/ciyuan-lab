"""Validate the shared course-pack contract.

The validator intentionally checks metadata, references and safe execution
declarations only. It does not judge teaching quality, source truthfulness or
run student code. Those remain human-review and practice-module concerns.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]
COURSE_PACKS_ROOT = REPO_ROOT / "course_packs"
SCHEMA_VERSION = "0.1.0"
CONTENT_SUFFIXES = {".json", ".yaml", ".yml"}
CONTENT_DIRECTORIES = {
    "concepts_dir": "concepts",
    "exercises_dir": "exercises",
    "projects_dir": "projects",
    "sources_dir": "sources",
}
COURSE_ID_PREFIXES = {
    "c": "C-",
    "python": "PY-",
    "data_structures": "DS-",
}
SOURCE_ID_PREFIXES = {
    "c": "SRC-C-",
    "python": "SRC-PY-",
    "data_structures": "SRC-DS-",
}
COURSE_STATUSES = {"scaffold", "draft", "review", "published"}
RECORD_STATUSES = {"draft", "reviewed"}
FEATURE_STATUSES = {"planned", "in_progress", "ready", "disabled"}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
EXERCISE_TYPES = {"objective", "short_answer", "code", "debug"}
SAFE_DATA_CLASSIFICATIONS = {"public", "authorized_desensitized", "synthetic"}
ID_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")


@dataclass(frozen=True)
class ContentRecord:
    """Fields retained after one content file has been parsed."""

    kind: str
    record_id: str
    course_id: str
    status: str
    path: Path
    prerequisites: tuple[str, ...] = ()
    concept_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    assessment_refs: tuple[str, ...] = ()
    exercise_type: str | None = None
    runtime_language: str | None = None
    test_count: int | None = None
    is_synthetic_source: bool = False
    rag_eligible: bool = False
    scenario_provider: str | None = None
    fallback_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class HandoffRecord:
    """References retained from the optional course handoff document."""

    status: str
    concept_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    golden_source_refs: tuple[str, ...]
    objective_exercise_id: str
    practice_exercise_id: str
    project_id: str
    verification_samples: tuple[tuple[str, str, int | None], ...]
    algorithm_exercise_refs: tuple[str, ...]


@dataclass(frozen=True)
class PackValidation:
    """Validation result plus content IDs used for repository-wide checks."""

    errors: list[str]
    records: tuple[ContentRecord, ...]


RecordValidator = Callable[[Path], tuple[list[str], ContentRecord | None]]


class UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """YAML loader that rejects duplicate mapping keys instead of overwriting them."""


def construct_unique_yaml_mapping(
    loader: UniqueKeyLoader, node: Any, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    seen: set[tuple[str, str]] = set()
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        marker = (type(key).__qualname__, repr(key))
        if marker in seen:
            raise ValueError(f"duplicate mapping key: {key!r}")
        seen.add(marker)
        try:
            mapping[key] = loader.construct_object(value_node, deep=deep)
        except TypeError as exc:
            raise ValueError(f"mapping key must be hashable: {key!r}") from exc
    return mapping


def construct_unique_json_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"duplicate mapping key: {key!r}")
        mapping[key] = value
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_yaml_mapping,
)


def load_mapping(path: Path, description: str) -> dict[str, Any]:
    """Load a YAML/JSON file and require a mapping at its root."""

    with path.open(encoding="utf-8") as content_file:
        data = (
            json.load(content_file, object_pairs_hook=construct_unique_json_mapping)
            if path.suffix.lower() == ".json"
            else yaml.load(content_file, Loader=UniqueKeyLoader)
        )
    if not isinstance(data, dict):
        raise ValueError(f"{description} root must be a mapping")
    return data


def is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def contains_control_characters(value: str) -> bool:
    """Return whether a stored path-like value contains unsafe control bytes."""

    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def is_http_url(value: object) -> bool:
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        return False
    if contains_control_characters(value):
        return False
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(hostname)


def validate_trimmed_string(
    value: object, *, field_name: str, file_label: str
) -> tuple[list[str], str]:
    """Require a non-empty string whose stored value is already normalized."""

    if not is_non_empty_string(value):
        return [f"{file_label}: {field_name} must be a non-empty string"], ""
    normalized = str(value).strip()
    if value != normalized:
        return [f"{file_label}: {field_name} must not have surrounding whitespace"], normalized
    return [], normalized


def validate_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None,
    file_label: str,
) -> list[str]:
    errors: list[str] = []
    invalid_keys = [key for key in value if not isinstance(key, str)]
    if invalid_keys:
        rendered = ", ".join(repr(key) for key in invalid_keys)
        errors.append(f"{file_label}: field names must be strings: {rendered}")
    string_keys = {key for key in value if isinstance(key, str)}
    missing = required - string_keys
    unknown = string_keys - required - (optional or set())
    if missing:
        errors.append(f"{file_label}: missing fields: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{file_label}: unsupported fields: {', '.join(sorted(unknown))}")
    return errors


def validate_string_list(
    value: object,
    *,
    field_name: str,
    file_label: str,
    min_items: int = 0,
    max_items: int | None = None,
) -> tuple[list[str], tuple[str, ...]]:
    """Validate a list of non-empty, non-duplicated strings."""

    if not isinstance(value, list):
        return [f"{file_label}: {field_name} must be a list"], ()
    if len(value) < min_items:
        return [f"{file_label}: {field_name} must contain at least {min_items} item(s)"], ()
    if max_items is not None and len(value) > max_items:
        return [f"{file_label}: {field_name} must contain at most {max_items} item(s)"], ()
    if not all(is_non_empty_string(item) for item in value):
        return [f"{file_label}: {field_name} must contain only non-empty strings"], ()
    if any(item != item.strip() for item in value):
        return [f"{file_label}: {field_name} items must not have surrounding whitespace"], ()
    values = tuple(str(item).strip() for item in value)
    if len(values) != len(set(values)):
        return [f"{file_label}: {field_name} contains duplicate values"], values
    return [], values


def validate_positive_int(value: object, field_name: str, file_label: str) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return [f"{file_label}: {field_name} must be a positive integer"]
    return []


def validate_bounded_int(
    value: object,
    *,
    field_name: str,
    file_label: str,
    minimum: int,
    maximum: int,
) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        return [f"{file_label}: {field_name} must be between {minimum} and {maximum}"]
    return []


def validate_enum(value: object, allowed: set[str], field_name: str, file_label: str) -> list[str]:
    if not isinstance(value, str) or value not in allowed:
        return [f"{file_label}: {field_name} must be one of: {', '.join(sorted(allowed))}"]
    return []


def validate_extensions(value: object, file_label: str) -> list[str]:
    if value is not None and not isinstance(value, dict):
        return [f"{file_label}: extensions must be a mapping"]
    return []


def validate_record_header(
    document: dict[str, Any],
    *,
    path: Path,
    file_label: str,
    course_id: str,
    expected_prefix: str,
) -> tuple[list[str], str, str]:
    errors: list[str] = []
    record_id_value = document.get("id")
    record_id = record_id_value.strip() if isinstance(record_id_value, str) else ""
    if not record_id:
        errors.append(f"{file_label}: id must be a non-empty string")
    else:
        if record_id_value != record_id:
            errors.append(f"{file_label}: id must not have surrounding whitespace")
        if not record_id.startswith(expected_prefix) or len(record_id) == len(expected_prefix):
            errors.append(
                f"{file_label}: id must start with {expected_prefix} and include a suffix"
            )
        if ID_PATTERN.fullmatch(record_id) is None:
            errors.append(f"{file_label}: id must use uppercase letters, digits and hyphens")
        if path.stem != record_id:
            errors.append(f"{file_label}: filename must be {record_id}{path.suffix.lower()}")
    if not is_non_empty_string(document.get("title")):
        errors.append(f"{file_label}: title must be a non-empty string")
    if document.get("course") != course_id:
        errors.append(f"{file_label}: course must be {course_id}")
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{file_label}: schema_version must be {SCHEMA_VERSION}")
    errors.extend(validate_positive_int(document.get("version"), "version", file_label))
    status_value = document.get("status")
    status = status_value if isinstance(status_value, str) else ""
    errors.extend(validate_enum(status_value, RECORD_STATUSES, "status", file_label))
    errors.extend(validate_extensions(document.get("extensions"), file_label))
    return errors, record_id, status


def validate_learning_card(lesson: object, file_label: str) -> list[str]:
    if not isinstance(lesson, dict):
        return [f"{file_label}: lesson must be a mapping"]
    errors = validate_keys(
        lesson,
        required={"summary"},
        optional={
            "key_points",
            "examples",
            "common_mistakes",
            "learning_sequence",
            "worked_example",
            "checkpoint",
        },
        file_label=f"{file_label}.lesson",
    )
    if not is_non_empty_string(lesson.get("summary")):
        errors.append(f"{file_label}: lesson.summary must be a non-empty string")
    for field_name in ("key_points", "examples", "common_mistakes"):
        if field_name in lesson:
            field_errors, _ = validate_string_list(
                lesson[field_name], field_name=f"lesson.{field_name}", file_label=file_label
            )
            errors.extend(field_errors)
    sequence = lesson.get("learning_sequence")
    if sequence is not None:
        if not isinstance(sequence, list) or not sequence:
            errors.append(f"{file_label}: lesson.learning_sequence must be a non-empty list")
        else:
            for index, step in enumerate(sequence):
                step_label = f"{file_label}.lesson.learning_sequence[{index}]"
                if not isinstance(step, dict):
                    errors.append(f"{step_label}: step must be a mapping")
                    continue
                errors.extend(
                    validate_keys(
                        step,
                        required={"title", "content"},
                        optional=None,
                        file_label=step_label,
                    )
                )
                for field_name in ("title", "content"):
                    if not is_non_empty_string(step.get(field_name)):
                        errors.append(f"{step_label}: {field_name} must be a non-empty string")
    worked_example = lesson.get("worked_example")
    if worked_example is not None:
        example_label = f"{file_label}.lesson.worked_example"
        if not isinstance(worked_example, dict):
            errors.append(f"{example_label}: worked_example must be a mapping")
        else:
            errors.extend(
                validate_keys(
                    worked_example,
                    required={"problem", "steps", "code", "reflection"},
                    optional=None,
                    file_label=example_label,
                )
            )
            for field_name in ("problem", "code", "reflection"):
                if not is_non_empty_string(worked_example.get(field_name)):
                    errors.append(f"{example_label}: {field_name} must be a non-empty string")
            step_errors, _ = validate_string_list(
                worked_example.get("steps"),
                field_name="steps",
                file_label=example_label,
                min_items=2,
            )
            errors.extend(step_errors)
    checkpoint = lesson.get("checkpoint")
    if checkpoint is not None:
        checkpoint_label = f"{file_label}.lesson.checkpoint"
        if not isinstance(checkpoint, dict):
            errors.append(f"{checkpoint_label}: checkpoint must be a mapping")
        else:
            errors.extend(
                validate_keys(
                    checkpoint,
                    required={"prompt", "guidance"},
                    optional=None,
                    file_label=checkpoint_label,
                )
            )
            for field_name in ("prompt", "guidance"):
                if not is_non_empty_string(checkpoint.get(field_name)):
                    errors.append(f"{checkpoint_label}: {field_name} must be a non-empty string")
    return errors


def validate_concept_file(
    path: Path, *, course_id: str, expected_prefix: str
) -> tuple[list[str], ContentRecord | None]:
    file_label = f"{course_id}/concepts/{path.name}"
    try:
        concept = load_mapping(path, "concept")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read concept: {exc}"], None
    errors = validate_keys(
        concept,
        required={
            "id",
            "title",
            "course",
            "schema_version",
            "version",
            "difficulty",
            "estimated_minutes",
            "prerequisites",
            "learning_objectives",
            "concepts",
            "lesson",
            "assessment_ids",
            "source_refs",
            "status",
        },
        optional={"extensions"},
        file_label=file_label,
    )
    header_errors, concept_id, status = validate_record_header(
        concept,
        path=path,
        file_label=file_label,
        course_id=course_id,
        expected_prefix=expected_prefix,
    )
    errors.extend(header_errors)
    errors.extend(validate_enum(concept.get("difficulty"), DIFFICULTIES, "difficulty", file_label))
    errors.extend(
        validate_positive_int(concept.get("estimated_minutes"), "estimated_minutes", file_label)
    )
    prerequisite_errors, prerequisites = validate_string_list(
        concept.get("prerequisites"), field_name="prerequisites", file_label=file_label
    )
    errors.extend(prerequisite_errors)
    list_values: dict[str, tuple[str, ...]] = {}
    for field_name in ("learning_objectives", "concepts", "assessment_ids", "source_refs"):
        field_errors, values = validate_string_list(
            concept.get(field_name), field_name=field_name, file_label=file_label, min_items=1
        )
        errors.extend(field_errors)
        list_values[field_name] = values
    errors.extend(validate_learning_card(concept.get("lesson"), file_label))
    if not concept_id:
        return errors, None
    return errors, ContentRecord(
        kind="concept",
        record_id=concept_id,
        course_id=course_id,
        status=status,
        path=path,
        prerequisites=prerequisites,
        source_refs=list_values.get("source_refs", ()),
        assessment_refs=list_values.get("assessment_ids", ()),
    )


def validate_rubric(evaluation: dict[str, Any], file_label: str) -> list[str]:
    errors: list[str] = []
    max_score = evaluation.get("max_score")
    errors.extend(validate_positive_int(max_score, "evaluation.max_score", file_label))
    rubric = evaluation.get("rubric")
    if not isinstance(rubric, list) or not rubric:
        return [*errors, f"{file_label}: evaluation.rubric must be a non-empty list"]
    total = 0
    for index, item in enumerate(rubric):
        item_label = f"{file_label}.evaluation.rubric[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: must be a mapping")
            continue
        errors.extend(
            validate_keys(
                item, required={"criterion", "points"}, optional=None, file_label=item_label
            )
        )
        if not is_non_empty_string(item.get("criterion")):
            errors.append(f"{item_label}: criterion must be a non-empty string")
        points = item.get("points")
        errors.extend(validate_positive_int(points, "points", item_label))
        if isinstance(points, int) and not isinstance(points, bool) and points > 0:
            total += points
    if isinstance(max_score, int) and not isinstance(max_score, bool) and total != max_score:
        errors.append(f"{file_label}: evaluation.rubric points must sum to max_score")
    return errors


def validate_objective_evaluation(evaluation: dict[str, Any], file_label: str) -> list[str]:
    errors = validate_keys(
        evaluation,
        required={"mode", "options", "accepted_answers"},
        optional=None,
        file_label=f"{file_label}.evaluation",
    )
    if evaluation.get("mode") != "exact":
        errors.append(f"{file_label}: objective evaluation.mode must be exact")
    options = evaluation.get("options")
    option_ids: list[str] = []
    if not isinstance(options, list) or len(options) < 2:
        errors.append(f"{file_label}: evaluation.options must contain at least two options")
    else:
        for index, option in enumerate(options):
            option_label = f"{file_label}.evaluation.options[{index}]"
            if not isinstance(option, dict):
                errors.append(f"{option_label}: must be a mapping")
                continue
            errors.extend(
                validate_keys(
                    option, required={"id", "text"}, optional=None, file_label=option_label
                )
            )
            option_errors, option_id = validate_trimmed_string(
                option.get("id"), field_name="id", file_label=option_label
            )
            errors.extend(option_errors)
            if option_id:
                option_ids.append(option_id)
            if not is_non_empty_string(option.get("text")):
                errors.append(f"{option_label}: text must be a non-empty string")
    if len(option_ids) != len(set(option_ids)):
        errors.append(f"{file_label}: evaluation option ids must be unique")
    answer_errors, accepted_answers = validate_string_list(
        evaluation.get("accepted_answers"),
        field_name="evaluation.accepted_answers",
        file_label=file_label,
        min_items=1,
    )
    errors.extend(answer_errors)
    unknown_answers = set(accepted_answers) - set(option_ids)
    if unknown_answers:
        errors.append(
            f"{file_label}: accepted_answers reference unknown options: "
            + ", ".join(sorted(unknown_answers))
        )
    return errors


def validate_test_evaluation(
    evaluation: dict[str, Any], *, exercise_type: str, file_label: str, course_id: str
) -> tuple[list[str], str | None, int | None]:
    required = {"mode", "runtime", "tests"}
    optional = {"starter_code"} if exercise_type == "code" else set()
    if exercise_type == "debug":
        required.add("starter_code")
    errors = validate_keys(
        evaluation,
        required=required,
        optional=optional,
        file_label=f"{file_label}.evaluation",
    )
    if evaluation.get("mode") != "tests":
        errors.append(f"{file_label}: {exercise_type} evaluation.mode must be tests")
    if "starter_code" in evaluation and not is_non_empty_string(evaluation.get("starter_code")):
        errors.append(f"{file_label}: evaluation.starter_code must be a non-empty string")
    runtime_language: str | None = None
    test_count: int | None = None
    runtime = evaluation.get("runtime")
    if not isinstance(runtime, dict):
        errors.append(f"{file_label}: evaluation.runtime must be a mapping")
    else:
        errors.extend(
            validate_keys(
                runtime,
                required={
                    "language",
                    "version",
                    "entrypoint",
                    "time_limit_ms",
                    "memory_limit_mb",
                    "output_limit_kb",
                    "network_access",
                    "filesystem_access",
                },
                optional=None,
                file_label=f"{file_label}.evaluation.runtime",
            )
        )
        language = runtime.get("language")
        if not isinstance(language, str) or language not in {"c", "python"}:
            errors.append(f"{file_label}: runtime.language must be c or python")
        else:
            runtime_language = str(language)
            allowed_languages = {
                "c": {"c"},
                "python": {"python"},
                "data_structures": {"c", "python"},
            }.get(course_id, {"c", "python"})
            if language not in allowed_languages:
                allowed_text = " or ".join(sorted(allowed_languages))
                errors.append(
                    f"{file_label}: runtime.language must be {allowed_text} for course {course_id}"
                )
        version = runtime.get("version")
        required_version = {"c": "C17", "python": "3.11"}.get(str(language))
        if required_version is not None and version != required_version:
            errors.append(
                f"{file_label}: runtime.version must be {required_version} for {language}"
            )
        entrypoint_errors, entrypoint = validate_trimmed_string(
            runtime.get("entrypoint"),
            field_name="runtime.entrypoint",
            file_label=file_label,
        )
        errors.extend(entrypoint_errors)
        if entrypoint:
            entrypoint_path = Path(entrypoint)
            required_suffix = {"c": ".c", "python": ".py"}.get(str(language))
            if (
                contains_control_characters(entrypoint)
                or "/" in entrypoint
                or "\\" in entrypoint
                or entrypoint_path.name != entrypoint
                or entrypoint_path.is_absolute()
            ):
                errors.append(f"{file_label}: runtime.entrypoint must be a plain filename")
            if required_suffix is not None and entrypoint_path.suffix != required_suffix:
                errors.append(f"{file_label}: runtime.entrypoint must end with {required_suffix}")
        for field_name, minimum, maximum in (
            ("time_limit_ms", 100, 10_000),
            ("memory_limit_mb", 16, 512),
            ("output_limit_kb", 1, 1_024),
        ):
            errors.extend(
                validate_bounded_int(
                    runtime.get(field_name),
                    field_name=f"runtime.{field_name}",
                    file_label=file_label,
                    minimum=minimum,
                    maximum=maximum,
                )
            )
        if runtime.get("network_access") is not False:
            errors.append(f"{file_label}: runtime.network_access must be false")
        if runtime.get("filesystem_access") != "isolated":
            errors.append(f"{file_label}: runtime.filesystem_access must be isolated")
    tests = evaluation.get("tests")
    visibilities: set[str] = set()
    test_ids: list[str] = []
    if not isinstance(tests, list) or len(tests) < 2:
        errors.append(f"{file_label}: evaluation.tests must contain public and hidden tests")
    else:
        test_count = len(tests)
        for index, test_case in enumerate(tests):
            test_label = f"{file_label}.evaluation.tests[{index}]"
            if not isinstance(test_case, dict):
                errors.append(f"{test_label}: must be a mapping")
                continue
            errors.extend(
                validate_keys(
                    test_case,
                    required={"id", "visibility", "input", "expected_output"},
                    optional=None,
                    file_label=test_label,
                )
            )
            test_id_errors, test_id = validate_trimmed_string(
                test_case.get("id"), field_name="id", file_label=test_label
            )
            errors.extend(test_id_errors)
            if test_id:
                test_ids.append(test_id)
            visibility = test_case.get("visibility")
            if not isinstance(visibility, str) or visibility not in {"public", "hidden"}:
                errors.append(f"{test_label}: visibility must be public or hidden")
            else:
                visibilities.add(str(visibility))
            for field_name in ("input", "expected_output"):
                if not isinstance(test_case.get(field_name), str):
                    errors.append(f"{test_label}: {field_name} must be a string")
    if len(test_ids) != len(set(test_ids)):
        errors.append(f"{file_label}: evaluation test ids must be unique")
    if tests and visibilities != {"public", "hidden"}:
        errors.append(
            f"{file_label}: evaluation.tests require at least one public and one hidden test"
        )
    return errors, runtime_language, test_count


def validate_exercise_file(
    path: Path, *, course_id: str, expected_prefix: str
) -> tuple[list[str], ContentRecord | None]:
    file_label = f"{course_id}/exercises/{path.name}"
    try:
        exercise = load_mapping(path, "exercise")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read exercise: {exc}"], None
    errors = validate_keys(
        exercise,
        required={
            "id",
            "title",
            "course",
            "schema_version",
            "version",
            "type",
            "difficulty",
            "estimated_minutes",
            "concept_ids",
            "prompt",
            "source_refs",
            "evaluation",
            "status",
        },
        optional={"extensions"},
        file_label=file_label,
    )
    header_errors, exercise_id, status = validate_record_header(
        exercise,
        path=path,
        file_label=file_label,
        course_id=course_id,
        expected_prefix=expected_prefix,
    )
    errors.extend(header_errors)
    exercise_type_value = exercise.get("type")
    exercise_type = exercise_type_value if isinstance(exercise_type_value, str) else ""
    errors.extend(validate_enum(exercise_type_value, EXERCISE_TYPES, "type", file_label))
    errors.extend(validate_enum(exercise.get("difficulty"), DIFFICULTIES, "difficulty", file_label))
    errors.extend(
        validate_positive_int(exercise.get("estimated_minutes"), "estimated_minutes", file_label)
    )
    concept_errors, concept_refs = validate_string_list(
        exercise.get("concept_ids"), field_name="concept_ids", file_label=file_label, min_items=1
    )
    source_errors, source_refs = validate_string_list(
        exercise.get("source_refs"), field_name="source_refs", file_label=file_label, min_items=1
    )
    errors.extend(concept_errors)
    errors.extend(source_errors)
    if not is_non_empty_string(exercise.get("prompt")):
        errors.append(f"{file_label}: prompt must be a non-empty string")
    runtime_language: str | None = None
    test_count: int | None = None
    evaluation = exercise.get("evaluation")
    if not isinstance(evaluation, dict):
        errors.append(f"{file_label}: evaluation must be a mapping")
    elif exercise_type == "objective":
        errors.extend(validate_objective_evaluation(evaluation, file_label))
    elif exercise_type == "short_answer":
        errors.extend(
            validate_keys(
                evaluation,
                required={"mode", "max_score", "rubric"},
                optional=None,
                file_label=f"{file_label}.evaluation",
            )
        )
        if evaluation.get("mode") != "rubric":
            errors.append(f"{file_label}: short_answer evaluation.mode must be rubric")
        errors.extend(validate_rubric(evaluation, file_label))
    elif isinstance(exercise_type, str) and exercise_type in {"code", "debug"}:
        test_errors, runtime_language, test_count = validate_test_evaluation(
            evaluation,
            exercise_type=exercise_type,
            file_label=file_label,
            course_id=course_id,
        )
        errors.extend(test_errors)
    if not exercise_id:
        return errors, None
    return errors, ContentRecord(
        kind="exercise",
        record_id=exercise_id,
        course_id=course_id,
        status=status,
        path=path,
        concept_refs=concept_refs,
        source_refs=source_refs,
        exercise_type=exercise_type or None,
        runtime_language=runtime_language,
        test_count=test_count,
    )


def safe_source_content_path(pack_dir: Path, value: object) -> Path | None:
    if not is_non_empty_string(value):
        return None
    raw_path = str(value)
    if raw_path != raw_path.strip() or contains_control_characters(raw_path) or "\\" in raw_path:
        return None
    try:
        relative_path = Path(raw_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            return None
        sources_root = (pack_dir / "sources").resolve()
        candidate = (sources_root / relative_path).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(sources_root):
        return None
    return candidate


def validate_source_file(
    path: Path, *, pack_dir: Path, course_id: str, expected_prefix: str
) -> tuple[list[str], ContentRecord | None]:
    file_label = f"{course_id}/sources/{path.name}"
    try:
        source = load_mapping(path, "source")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read source: {exc}"], None
    errors = validate_keys(
        source,
        required={
            "id",
            "title",
            "course",
            "schema_version",
            "version",
            "source_type",
            "citation",
            "rights",
            "data_classification",
            "rag",
            "status",
        },
        optional={"extensions"},
        file_label=file_label,
    )
    header_errors, source_id, status = validate_record_header(
        source,
        path=path,
        file_label=file_label,
        course_id=course_id,
        expected_prefix=expected_prefix,
    )
    errors.extend(header_errors)
    source_type = source.get("source_type")
    errors.extend(
        validate_enum(
            source_type,
            {
                "course_outline",
                "textbook",
                "official_documentation",
                "open_resource",
                "authorized_case",
                "synthetic",
            },
            "source_type",
            file_label,
        )
    )
    citation = source.get("citation")
    if not isinstance(citation, dict):
        errors.append(f"{file_label}: citation must be a mapping")
    else:
        errors.extend(
            validate_keys(
                citation,
                required={"locator"},
                optional={"publisher", "edition", "published_at", "url"},
                file_label=f"{file_label}.citation",
            )
        )
        if not is_non_empty_string(citation.get("locator")):
            errors.append(f"{file_label}: citation.locator must be a non-empty string")
        url = citation.get("url")
        if url is not None and not is_http_url(url):
            errors.append(f"{file_label}: citation.url must be an http(s) URL")
    rights = source.get("rights")
    rights_basis: object = None
    if not isinstance(rights, dict):
        errors.append(f"{file_label}: rights must be a mapping")
    else:
        errors.extend(
            validate_keys(
                rights,
                required={"basis", "note"},
                optional={"license"},
                file_label=f"{file_label}.rights",
            )
        )
        rights_basis = rights.get("basis")
        errors.extend(
            validate_enum(
                rights_basis,
                {"open_license", "authorized", "synthetic"},
                "rights.basis",
                file_label,
            )
        )
        if not is_non_empty_string(rights.get("note")):
            errors.append(f"{file_label}: rights.note must record the usage basis")
    classification = source.get("data_classification")
    errors.extend(
        validate_enum(classification, SAFE_DATA_CLASSIFICATIONS, "data_classification", file_label)
    )
    if rights_basis == "synthetic" and classification != "synthetic":
        errors.append(f"{file_label}: synthetic sources must use synthetic data_classification")
    if source_type == "synthetic" and (
        rights_basis != "synthetic" or classification != "synthetic"
    ):
        errors.append(
            f"{file_label}: source_type synthetic requires synthetic rights and classification"
        )
    if rights_basis == "synthetic" and source_type != "synthetic":
        errors.append(f"{file_label}: synthetic rights require source_type synthetic")
    if classification == "authorized_desensitized" and rights_basis != "authorized":
        errors.append(f"{file_label}: authorized_desensitized sources require authorized rights")
    rag = source.get("rag")
    rag_eligible = False
    if not isinstance(rag, dict):
        errors.append(f"{file_label}: rag must be a mapping")
    else:
        errors.extend(
            validate_keys(
                rag,
                required={"eligible", "content"},
                optional=None,
                file_label=f"{file_label}.rag",
            )
        )
        eligible = rag.get("eligible")
        if not isinstance(eligible, bool):
            errors.append(f"{file_label}: rag.eligible must be a boolean")
        else:
            rag_eligible = eligible
        content = rag.get("content")
        if not isinstance(content, dict):
            errors.append(f"{file_label}: rag.content must be a mapping")
        else:
            errors.extend(
                validate_keys(
                    content,
                    required={"mode"},
                    optional={"text", "path"},
                    file_label=f"{file_label}.rag.content",
                )
            )
            mode = content.get("mode")
            errors.extend(
                validate_enum(
                    mode, {"inline", "file", "reference_only"}, "rag.content.mode", file_label
                )
            )
            if mode == "inline" and not is_non_empty_string(content.get("text")):
                errors.append(f"{file_label}: inline RAG content requires non-empty text")
            if mode == "inline" and content.get("path") is not None:
                errors.append(f"{file_label}: inline RAG content cannot define path")
            if mode == "file":
                if content.get("text") is not None:
                    errors.append(f"{file_label}: file RAG content cannot define text")
                content_path = safe_source_content_path(pack_dir, content.get("path"))
                if content_path is None:
                    errors.append(f"{file_label}: rag.content.path must stay inside sources/")
                elif content_path.suffix.lower() not in {".md", ".txt"}:
                    errors.append(f"{file_label}: RAG content files must be .md or .txt")
                elif not content_path.is_file():
                    errors.append(
                        f"{file_label}: RAG content file does not exist: {content.get('path')}"
                    )
            if mode == "reference_only" and eligible is True:
                errors.append(f"{file_label}: reference_only sources cannot be RAG eligible")
            if mode == "reference_only" and (
                content.get("text") is not None or content.get("path") is not None
            ):
                errors.append(f"{file_label}: reference_only sources cannot define text or path")
        if eligible is True and status != "reviewed":
            errors.append(f"{file_label}: only reviewed sources may be RAG eligible")
    if not source_id:
        return errors, None
    return errors, ContentRecord(
        kind="source",
        record_id=source_id,
        course_id=course_id,
        status=status,
        path=path,
        is_synthetic_source=(
            source_type == "synthetic"
            and rights_basis == "synthetic"
            and classification == "synthetic"
        ),
        rag_eligible=rag_eligible,
    )


def validate_project_file(
    path: Path, *, course_id: str, expected_prefix: str
) -> tuple[list[str], ContentRecord | None]:
    file_label = f"{course_id}/projects/{path.name}"
    try:
        project = load_mapping(path, "project")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read project: {exc}"], None
    errors = validate_keys(
        project,
        required={
            "id",
            "title",
            "course",
            "schema_version",
            "version",
            "difficulty",
            "estimated_minutes",
            "concept_ids",
            "summary",
            "requirements",
            "deliverables",
            "source_refs",
            "verification_exercise_ids",
            "scenario_scope",
            "scenario_provider",
            "data_classification",
            "computer_science_objectives",
            "business_context_objectives",
            "evaluation",
            "status",
        },
        optional={"extensions", "fallback"},
        file_label=file_label,
    )
    header_errors, project_id, status = validate_record_header(
        project,
        path=path,
        file_label=file_label,
        course_id=course_id,
        expected_prefix=expected_prefix,
    )
    errors.extend(header_errors)
    errors.extend(validate_enum(project.get("difficulty"), DIFFICULTIES, "difficulty", file_label))
    errors.extend(
        validate_positive_int(project.get("estimated_minutes"), "estimated_minutes", file_label)
    )
    concept_errors, concept_refs = validate_string_list(
        project.get("concept_ids"), field_name="concept_ids", file_label=file_label, min_items=2
    )
    source_errors, source_refs = validate_string_list(
        project.get("source_refs"), field_name="source_refs", file_label=file_label, min_items=1
    )
    verification_errors, verification_refs = validate_string_list(
        project.get("verification_exercise_ids"),
        field_name="verification_exercise_ids",
        file_label=file_label,
        min_items=1,
    )
    errors.extend(concept_errors)
    errors.extend(source_errors)
    errors.extend(verification_errors)
    if not is_non_empty_string(project.get("summary")):
        errors.append(f"{file_label}: summary must be a non-empty string")
    for field_name in ("requirements", "deliverables", "computer_science_objectives"):
        field_errors, _ = validate_string_list(
            project.get(field_name), field_name=field_name, file_label=file_label, min_items=1
        )
        errors.extend(field_errors)
    business_errors, business_objectives = validate_string_list(
        project.get("business_context_objectives"),
        field_name="business_context_objectives",
        file_label=file_label,
    )
    errors.extend(business_errors)
    scope = project.get("scenario_scope")
    provider = project.get("scenario_provider")
    classification = project.get("data_classification")
    errors.extend(
        validate_enum(scope, {"none", "post_course_finance_practice"}, "scenario_scope", file_label)
    )
    errors.extend(
        validate_enum(
            provider, {"none", "tuoling", "fixed_synthetic"}, "scenario_provider", file_label
        )
    )
    errors.extend(
        validate_enum(classification, SAFE_DATA_CLASSIFICATIONS, "data_classification", file_label)
    )
    if scope == "post_course_finance_practice":
        if not isinstance(provider, str) or provider not in {"tuoling", "fixed_synthetic"}:
            errors.append(
                f"{file_label}: finance practice requires tuoling or fixed_synthetic provider"
            )
        if not business_objectives:
            errors.append(f"{file_label}: finance practice requires business_context_objectives")
        if provider == "fixed_synthetic" and classification != "synthetic":
            errors.append(
                f"{file_label}: fixed_synthetic projects must use synthetic data_classification"
            )
    elif scope == "none":
        if provider != "none":
            errors.append(f"{file_label}: non-finance projects must use scenario_provider none")
        if business_objectives:
            errors.append(
                f"{file_label}: non-finance projects must not define business_context_objectives"
            )
    fallback = project.get("fallback")
    fallback_refs: tuple[str, ...] = ()
    if provider == "tuoling" and not isinstance(fallback, dict):
        errors.append(f"{file_label}: tuoling projects require a fixed_synthetic fallback")
    if fallback is not None:
        if not isinstance(fallback, dict):
            errors.append(f"{file_label}: fallback must be a mapping")
        else:
            errors.extend(
                validate_keys(
                    fallback,
                    required={"mode", "source_refs", "note"},
                    optional=None,
                    file_label=f"{file_label}.fallback",
                )
            )
            if fallback.get("mode") != "fixed_synthetic":
                errors.append(f"{file_label}: fallback.mode must be fixed_synthetic")
            fallback_errors, fallback_refs = validate_string_list(
                fallback.get("source_refs"),
                field_name="fallback.source_refs",
                file_label=file_label,
                min_items=1,
            )
            errors.extend(fallback_errors)
            if not is_non_empty_string(fallback.get("note")):
                errors.append(f"{file_label}: fallback.note must be a non-empty string")
    evaluation = project.get("evaluation")
    if not isinstance(evaluation, dict):
        errors.append(f"{file_label}: evaluation must be a mapping")
    else:
        errors.extend(
            validate_keys(
                evaluation,
                required={"mode", "max_score", "rubric"},
                optional=None,
                file_label=f"{file_label}.evaluation",
            )
        )
        if evaluation.get("mode") != "rubric":
            errors.append(f"{file_label}: project evaluation.mode must be rubric")
        errors.extend(validate_rubric(evaluation, file_label))
    if not project_id:
        return errors, None
    return errors, ContentRecord(
        kind="project",
        record_id=project_id,
        course_id=course_id,
        status=status,
        path=path,
        concept_refs=concept_refs,
        source_refs=tuple(dict.fromkeys((*source_refs, *fallback_refs))),
        assessment_refs=verification_refs,
        scenario_provider=provider if isinstance(provider, str) else None,
        fallback_refs=fallback_refs,
    )


def validate_question_list(
    value: object,
    *,
    field_name: str,
    file_label: str,
    min_items: int,
    with_sources: bool,
) -> tuple[list[str], tuple[str, ...]]:
    errors: list[str] = []
    source_refs: list[str] = []
    if not isinstance(value, list) or len(value) < min_items:
        return [f"{file_label}: {field_name} must contain at least {min_items} item(s)"], ()
    question_ids: list[str] = []
    for index, item in enumerate(value):
        item_label = f"{file_label}.{field_name}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: must be a mapping")
            continue
        required = (
            {"id", "question", "expected_source_refs"} if with_sources else {"id", "question"}
        )
        errors.extend(validate_keys(item, required=required, optional=None, file_label=item_label))
        question_id_errors, question_id = validate_trimmed_string(
            item.get("id"), field_name="id", file_label=item_label
        )
        errors.extend(question_id_errors)
        if question_id:
            question_ids.append(question_id)
        if not is_non_empty_string(item.get("question")):
            errors.append(f"{item_label}: question must be a non-empty string")
        if with_sources:
            ref_errors, refs = validate_string_list(
                item.get("expected_source_refs"),
                field_name="expected_source_refs",
                file_label=item_label,
                min_items=1,
            )
            errors.extend(ref_errors)
            source_refs.extend(refs)
    if len(question_ids) != len(set(question_ids)):
        errors.append(f"{file_label}: {field_name} ids must be unique")
    return errors, tuple(source_refs)


def validate_algorithm_expectations(
    value: object, *, file_label: str, required: bool
) -> tuple[list[str], tuple[str, ...], tuple[str, ...]]:
    """Validate optional algorithm boundary and complexity expectations."""

    if value is None and not required:
        return [], (), ()
    if not isinstance(value, list) or not value:
        requirement = "a non-empty list" if required else "a list when provided"
        return [f"{file_label}: algorithm_expectations must be {requirement}"], (), ()

    errors: list[str] = []
    expectation_ids: list[str] = []
    exercise_refs: list[str] = []
    source_refs: list[str] = []
    for index, item in enumerate(value):
        item_label = f"{file_label}.algorithm_expectations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: must be a mapping")
            continue
        errors.extend(
            validate_keys(
                item,
                required={
                    "id",
                    "exercise_id",
                    "boundary_cases",
                    "expected_complexity",
                    "rationale",
                    "source_refs",
                },
                optional=None,
                file_label=item_label,
            )
        )
        expectation_errors, expectation_id = validate_trimmed_string(
            item.get("id"), field_name="id", file_label=item_label
        )
        exercise_errors, exercise_id = validate_trimmed_string(
            item.get("exercise_id"), field_name="exercise_id", file_label=item_label
        )
        complexity_errors, _ = validate_trimmed_string(
            item.get("expected_complexity"),
            field_name="expected_complexity",
            file_label=item_label,
        )
        rationale_errors, _ = validate_trimmed_string(
            item.get("rationale"), field_name="rationale", file_label=item_label
        )
        boundary_errors, _ = validate_string_list(
            item.get("boundary_cases"),
            field_name="boundary_cases",
            file_label=item_label,
            min_items=1,
        )
        source_errors, item_source_refs = validate_string_list(
            item.get("source_refs"),
            field_name="source_refs",
            file_label=item_label,
            min_items=1,
        )
        errors.extend(
            (
                *expectation_errors,
                *exercise_errors,
                *complexity_errors,
                *rationale_errors,
                *boundary_errors,
                *source_errors,
            )
        )
        if expectation_id:
            expectation_ids.append(expectation_id)
        if exercise_id:
            exercise_refs.append(exercise_id)
        source_refs.extend(item_source_refs)
    if len(expectation_ids) != len(set(expectation_ids)):
        errors.append(f"{file_label}: algorithm_expectations ids must be unique")
    return errors, tuple(exercise_refs), tuple(source_refs)


def validate_handoff_file(path: Path, *, course_id: str) -> tuple[list[str], HandoffRecord | None]:
    file_label = f"{course_id}/handoff.yaml"
    try:
        handoff = load_mapping(path, "handoff")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read handoff: {exc}"], None
    errors = validate_keys(
        handoff,
        required={
            "schema_version",
            "course_id",
            "package_revision",
            "status",
            "representative_content",
            "source_refs",
            "golden_questions",
            "insufficient_evidence_questions",
            "wrong_citation_examples",
            "verification_samples",
            "demo_path",
            "known_limitations",
        },
        optional={"algorithm_expectations"},
        file_label=file_label,
    )
    if handoff.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{file_label}: schema_version must be {SCHEMA_VERSION}")
    if handoff.get("course_id") != course_id:
        errors.append(f"{file_label}: course_id must be {course_id}")
    package_revision = handoff.get("package_revision")
    revision_match = (
        re.fullmatch(r"develop@([0-9a-f]{7,40})", package_revision)
        if isinstance(package_revision, str)
        else None
    )
    revision_hash = revision_match.group(1) if revision_match is not None else ""
    if (
        revision_match is None
        or revision_hash == "0123456789abcdef"
        or (revision_hash and len(set(revision_hash)) == 1)
    ):
        errors.append(
            f"{file_label}: package_revision must match a non-placeholder "
            "develop@<7-40 lowercase hex commit>"
        )
    status_value = handoff.get("status")
    status = status_value if isinstance(status_value, str) else ""
    errors.extend(validate_enum(status_value, RECORD_STATUSES, "status", file_label))
    concept_refs: tuple[str, ...] = ()
    objective_exercise_id = ""
    practice_exercise_id = ""
    project_id = ""
    representative = handoff.get("representative_content")
    if not isinstance(representative, dict):
        errors.append(f"{file_label}: representative_content must be a mapping")
    else:
        errors.extend(
            validate_keys(
                representative,
                required={
                    "concept_ids",
                    "objective_exercise_id",
                    "practice_exercise_id",
                    "project_id",
                },
                optional=None,
                file_label=f"{file_label}.representative_content",
            )
        )
        concept_errors, concept_refs = validate_string_list(
            representative.get("concept_ids"),
            field_name="representative_content.concept_ids",
            file_label=file_label,
            min_items=3,
            max_items=5,
        )
        errors.extend(concept_errors)
        representative_values: dict[str, str] = {}
        for field_name in ("objective_exercise_id", "practice_exercise_id", "project_id"):
            value_errors, normalized = validate_trimmed_string(
                representative.get(field_name),
                field_name=f"representative_content.{field_name}",
                file_label=file_label,
            )
            errors.extend(value_errors)
            representative_values[field_name] = normalized
        objective_exercise_id = representative_values["objective_exercise_id"]
        practice_exercise_id = representative_values["practice_exercise_id"]
        project_id = representative_values["project_id"]
    source_errors, source_refs = validate_string_list(
        handoff.get("source_refs"), field_name="source_refs", file_label=file_label, min_items=1
    )
    errors.extend(source_errors)
    golden_errors, golden_refs = validate_question_list(
        handoff.get("golden_questions"),
        field_name="golden_questions",
        file_label=file_label,
        min_items=5,
        with_sources=True,
    )
    errors.extend(golden_errors)
    insufficient_errors, _ = validate_question_list(
        handoff.get("insufficient_evidence_questions"),
        field_name="insufficient_evidence_questions",
        file_label=file_label,
        min_items=1,
        with_sources=False,
    )
    errors.extend(insufficient_errors)
    wrong_refs: list[str] = []
    wrong_examples = handoff.get("wrong_citation_examples")
    if not isinstance(wrong_examples, list) or not wrong_examples:
        errors.append(f"{file_label}: wrong_citation_examples must be a non-empty list")
    else:
        wrong_ids: list[str] = []
        for index, item in enumerate(wrong_examples):
            item_label = f"{file_label}.wrong_citation_examples[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: must be a mapping")
                continue
            errors.extend(
                validate_keys(
                    item,
                    required={"id", "question", "incorrect_source_ref", "reason"},
                    optional=None,
                    file_label=item_label,
                )
            )
            wrong_id_errors, wrong_id = validate_trimmed_string(
                item.get("id"), field_name="id", file_label=item_label
            )
            errors.extend(wrong_id_errors)
            if wrong_id:
                wrong_ids.append(wrong_id)
            wrong_ref_errors, wrong_ref = validate_trimmed_string(
                item.get("incorrect_source_ref"),
                field_name="incorrect_source_ref",
                file_label=item_label,
            )
            errors.extend(wrong_ref_errors)
            if wrong_ref:
                wrong_refs.append(wrong_ref)
            for field_name in ("question", "reason"):
                if not is_non_empty_string(item.get(field_name)):
                    errors.append(f"{item_label}: {field_name} must be a non-empty string")
        if len(wrong_ids) != len(set(wrong_ids)):
            errors.append(f"{file_label}: wrong_citation_examples ids must be unique")
    verification_samples: list[tuple[str, str, int | None]] = []
    accepted_values: set[bool] = set()
    samples = handoff.get("verification_samples")
    if not isinstance(samples, list) or len(samples) < 2:
        errors.append(
            f"{file_label}: verification_samples must contain correct and incorrect samples"
        )
    else:
        sample_ids: list[str] = []
        for index, item in enumerate(samples):
            item_label = f"{file_label}.verification_samples[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: must be a mapping")
                continue
            errors.extend(
                validate_keys(
                    item,
                    required={"id", "exercise_id", "language", "source_code", "expected"},
                    optional=None,
                    file_label=item_label,
                )
            )
            sample_id_errors, sample_id = validate_trimmed_string(
                item.get("id"), field_name="id", file_label=item_label
            )
            errors.extend(sample_id_errors)
            if sample_id:
                sample_ids.append(sample_id)
            exercise_id_errors, exercise_id = validate_trimmed_string(
                item.get("exercise_id"), field_name="exercise_id", file_label=item_label
            )
            errors.extend(exercise_id_errors)
            language_errors, language = validate_trimmed_string(
                item.get("language"), field_name="language", file_label=item_label
            )
            errors.extend(language_errors)
            if language not in {"c", "python"}:
                errors.append(f"{item_label}: language must be c or python")
            if not is_non_empty_string(item.get("source_code")):
                errors.append(f"{item_label}: source_code must be a non-empty string")
            expected = item.get("expected")
            if not isinstance(expected, dict):
                errors.append(f"{item_label}: expected must be a mapping")
                continue
            errors.extend(
                validate_keys(
                    expected,
                    required={"accepted", "passed_tests", "total_tests", "diagnostics"},
                    optional=None,
                    file_label=f"{item_label}.expected",
                )
            )
            accepted = expected.get("accepted")
            passed = expected.get("passed_tests")
            total = expected.get("total_tests")
            if not isinstance(accepted, bool):
                errors.append(f"{item_label}: expected.accepted must be a boolean")
            else:
                accepted_values.add(accepted)
            diagnostic_errors, _ = validate_string_list(
                expected.get("diagnostics"),
                field_name="expected.diagnostics",
                file_label=item_label,
                min_items=1 if accepted is False else 0,
                max_items=10,
            )
            errors.extend(diagnostic_errors)
            if isinstance(total, bool) or not isinstance(total, int) or total < 1:
                errors.append(f"{item_label}: expected.total_tests must be a positive integer")
                valid_total: int | None = None
            else:
                valid_total = total
            if isinstance(passed, bool) or not isinstance(passed, int) or passed < 0:
                errors.append(f"{item_label}: expected.passed_tests must be a non-negative integer")
            if isinstance(passed, int) and isinstance(total, int) and passed > total:
                errors.append(f"{item_label}: passed_tests cannot exceed total_tests")
            if (
                accepted is True
                and isinstance(passed, int)
                and isinstance(total, int)
                and passed != total
            ):
                errors.append(f"{item_label}: accepted samples must pass all tests")
            if (
                accepted is False
                and isinstance(passed, int)
                and isinstance(total, int)
                and passed == total
            ):
                errors.append(f"{item_label}: rejected samples cannot pass all tests")
            if exercise_id and language in {"c", "python"}:
                verification_samples.append((exercise_id, language, valid_total))
        if len(sample_ids) != len(set(sample_ids)):
            errors.append(f"{file_label}: verification sample ids must be unique")
        if accepted_values != {False, True}:
            errors.append(
                f"{file_label}: verification_samples require accepted and rejected examples"
            )
    algorithm_errors, algorithm_exercise_refs, algorithm_source_refs = (
        validate_algorithm_expectations(
            handoff.get("algorithm_expectations"),
            file_label=file_label,
            required=course_id == "data_structures",
        )
    )
    errors.extend(algorithm_errors)
    for field_name, min_items in (("demo_path", 1), ("known_limitations", 0)):
        field_errors, _ = validate_string_list(
            handoff.get(field_name),
            field_name=field_name,
            file_label=file_label,
            min_items=min_items,
        )
        errors.extend(field_errors)
    all_source_refs = tuple(
        dict.fromkeys((*source_refs, *golden_refs, *wrong_refs, *algorithm_source_refs))
    )
    return errors, HandoffRecord(
        status=status,
        concept_refs=concept_refs,
        source_refs=all_source_refs,
        golden_source_refs=golden_refs,
        objective_exercise_id=objective_exercise_id,
        practice_exercise_id=practice_exercise_id,
        project_id=project_id,
        verification_samples=tuple(verification_samples),
        algorithm_exercise_refs=algorithm_exercise_refs,
    )


def parse_iso_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_manifest(
    manifest: dict[str, Any], *, pack_dir: Path
) -> tuple[list[str], str, str, int | None, int | None]:
    file_label = f"{pack_dir.name}/manifest.yaml"
    errors = validate_keys(
        manifest,
        required={"schema_version", "course", "content", "features", "review"},
        optional=None,
        file_label=file_label,
    )
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{file_label}: schema_version must be {SCHEMA_VERSION}")
    course_id = ""
    status = ""
    target: int | None = None
    implemented: int | None = None
    course = manifest.get("course")
    if not isinstance(course, dict):
        errors.append(f"{file_label}: course must be a mapping")
    else:
        errors.extend(
            validate_keys(
                course,
                required={
                    "id",
                    "title",
                    "status",
                    "target_core_concepts",
                    "implemented_core_concepts",
                },
                optional=None,
                file_label=f"{file_label}.course",
            )
        )
        course_id_value = course.get("id")
        course_id = course_id_value if isinstance(course_id_value, str) else ""
        if course_id != pack_dir.name:
            errors.append(f"{file_label}: course.id must match the directory name")
        if course_id not in COURSE_ID_PREFIXES:
            errors.append(f"{file_label}: unsupported course.id")
        if not is_non_empty_string(course.get("title")):
            errors.append(f"{file_label}: course.title must be a non-empty string")
        status_value = course.get("status")
        status = status_value if isinstance(status_value, str) else ""
        errors.extend(validate_enum(status_value, COURSE_STATUSES, "course.status", file_label))
        target_value = course.get("target_core_concepts")
        implemented_value = course.get("implemented_core_concepts")
        if (
            isinstance(target_value, bool)
            or not isinstance(target_value, int)
            or not 30 <= target_value <= 50
        ):
            errors.append(f"{file_label}: target_core_concepts must be between 30 and 50")
        else:
            target = target_value
        if (
            isinstance(implemented_value, bool)
            or not isinstance(implemented_value, int)
            or implemented_value < 0
        ):
            errors.append(f"{file_label}: implemented_core_concepts must be a non-negative integer")
        else:
            implemented = implemented_value
        if target is not None and implemented is not None and implemented > target:
            errors.append(f"{file_label}: implemented_core_concepts exceeds target")
    content = manifest.get("content")
    if not isinstance(content, dict):
        errors.append(f"{file_label}: content must be a mapping")
    else:
        errors.extend(
            validate_keys(
                content,
                required=set(CONTENT_DIRECTORIES),
                optional=None,
                file_label=f"{file_label}.content",
            )
        )
        for field_name, directory in CONTENT_DIRECTORIES.items():
            if content.get(field_name) != directory:
                errors.append(f"{file_label}: content.{field_name} must be {directory}")
    features = manifest.get("features")
    required_features = {"rag_qa", "adaptive_practice", "debug_tasks", "comprehensive_project"}
    if not isinstance(features, dict):
        errors.append(f"{file_label}: features must be a mapping")
    else:
        errors.extend(
            validate_keys(
                features,
                required=required_features,
                optional=None,
                file_label=f"{file_label}.features",
            )
        )
        for field_name in required_features:
            errors.extend(
                validate_enum(
                    features.get(field_name), FEATURE_STATUSES, f"features.{field_name}", file_label
                )
            )
    review = manifest.get("review")
    if not isinstance(review, dict):
        errors.append(f"{file_label}: review must be a mapping")
    else:
        errors.extend(
            validate_keys(
                review,
                required={"content_owner", "last_reviewed_at"},
                optional=None,
                file_label=f"{file_label}.review",
            )
        )
        owner_errors, owner = validate_trimmed_string(
            review.get("content_owner"),
            field_name="review.content_owner",
            file_label=file_label,
        )
        errors.extend(owner_errors)
        if status != "scaffold" and owner == "unassigned":
            errors.append(f"{file_label}: non-scaffold courses require an assigned content_owner")
        reviewed_at = review.get("last_reviewed_at")
        if reviewed_at is not None and not parse_iso_datetime(reviewed_at):
            errors.append(f"{file_label}: review.last_reviewed_at must be null or ISO 8601")
        if status in {"review", "published"} and not parse_iso_datetime(reviewed_at):
            errors.append(f"{file_label}: review/published courses require last_reviewed_at")
    return errors, course_id, status, target, implemented


def find_prerequisite_cycles(records_by_id: dict[str, ContentRecord]) -> list[str]:
    state: dict[str, int] = {}
    trail: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(concept_id: str) -> None:
        state[concept_id] = 1
        trail.append(concept_id)
        for prerequisite in records_by_id[concept_id].prerequisites:
            if prerequisite not in records_by_id:
                continue
            prerequisite_state = state.get(prerequisite, 0)
            if prerequisite_state == 0:
                visit(prerequisite)
            elif prerequisite_state == 1:
                cycle_start = trail.index(prerequisite)
                cycles.add(tuple(trail[cycle_start:] + [prerequisite]))
        trail.pop()
        state[concept_id] = 2

    for concept_id in sorted(records_by_id):
        if state.get(concept_id, 0) == 0:
            visit(concept_id)
    return [" -> ".join(cycle) for cycle in sorted(cycles)]


def record_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in CONTENT_SUFFIXES
    )


def add_missing_reference_errors(
    errors: list[str],
    *,
    record: ContentRecord,
    refs: tuple[str, ...],
    target_records: dict[str, ContentRecord],
    field_name: str,
    course_id: str,
) -> None:
    for reference in refs:
        target = target_records.get(reference)
        if target is None:
            errors.append(
                f"{course_id}/{record.kind}s/{record.path.name}: "
                f"{field_name} {reference} does not exist"
            )
        elif record.status == "reviewed" and target.status != "reviewed":
            errors.append(
                f"{course_id}/{record.kind}s/{record.path.name}: "
                f"reviewed content references draft {reference}"
            )


def validate_handoff_references(
    errors: list[str],
    *,
    handoff: HandoffRecord,
    records_by_kind: dict[str, dict[str, ContentRecord]],
    course_id: str,
) -> None:
    concepts = records_by_kind["concept"]
    exercises = records_by_kind["exercise"]
    projects = records_by_kind["project"]
    sources = records_by_kind["source"]
    for concept_id in handoff.concept_refs:
        if concept_id not in concepts:
            errors.append(f"{course_id}/handoff.yaml: concept {concept_id} does not exist")
    for source_id in handoff.source_refs:
        if source_id not in sources:
            errors.append(f"{course_id}/handoff.yaml: source {source_id} does not exist")
    if handoff.status == "reviewed":
        for source_id in handoff.golden_source_refs:
            source = sources.get(source_id)
            if source is not None and not source.rag_eligible:
                errors.append(
                    f"{course_id}/handoff.yaml: golden question source {source_id} "
                    "must be reviewed and RAG eligible"
                )
    objective = exercises.get(handoff.objective_exercise_id)
    if objective is None:
        errors.append(f"{course_id}/handoff.yaml: objective exercise does not exist")
    elif objective.exercise_type != "objective":
        errors.append(
            f"{course_id}/handoff.yaml: objective_exercise_id must reference an objective exercise"
        )
    practice = exercises.get(handoff.practice_exercise_id)
    if practice is None:
        errors.append(f"{course_id}/handoff.yaml: practice exercise does not exist")
    elif practice.exercise_type not in {"code", "debug"}:
        errors.append(
            f"{course_id}/handoff.yaml: practice_exercise_id must reference code or debug"
        )
    if handoff.project_id not in projects:
        errors.append(f"{course_id}/handoff.yaml: project {handoff.project_id} does not exist")
    for exercise_id, language, expected_total in handoff.verification_samples:
        exercise = exercises.get(exercise_id)
        if exercise is None:
            errors.append(
                f"{course_id}/handoff.yaml: verification exercise {exercise_id} does not exist"
            )
        elif exercise.exercise_type not in {"code", "debug"}:
            errors.append(
                f"{course_id}/handoff.yaml: verification samples require code/debug exercises"
            )
        elif exercise.runtime_language != language:
            errors.append(
                f"{course_id}/handoff.yaml: verification sample language {language} "
                f"does not match {exercise_id}"
            )
        elif expected_total is not None and exercise.test_count != expected_total:
            errors.append(
                f"{course_id}/handoff.yaml: verification sample expected.total_tests "
                f"does not match {exercise_id} test count"
            )
    for exercise_id in handoff.algorithm_exercise_refs:
        exercise = exercises.get(exercise_id)
        if exercise is None:
            errors.append(
                f"{course_id}/handoff.yaml: algorithm exercise {exercise_id} does not exist"
            )
        elif exercise.exercise_type not in {"code", "debug"}:
            errors.append(
                f"{course_id}/handoff.yaml: algorithm expectations require code/debug exercises"
            )
    if handoff.status == "reviewed":
        referenced = [
            *(concepts.get(item) for item in handoff.concept_refs),
            *(sources.get(item) for item in handoff.source_refs),
            objective,
            practice,
            projects.get(handoff.project_id),
            *(exercises.get(exercise_id) for exercise_id, _, _ in handoff.verification_samples),
            *(exercises.get(exercise_id) for exercise_id in handoff.algorithm_exercise_refs),
        ]
        if any(record is not None and record.status != "reviewed" for record in referenced):
            errors.append(f"{course_id}/handoff.yaml: reviewed handoff references draft content")


def validate_pack_details(pack_dir: Path) -> PackValidation:
    errors: list[str] = []
    manifest_path = pack_dir / "manifest.yaml"
    if not manifest_path.is_file():
        return PackValidation([f"{pack_dir.name}: manifest.yaml is missing"], ())
    try:
        manifest = load_mapping(manifest_path, "manifest")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return PackValidation([f"{pack_dir.name}: cannot read manifest: {exc}"], ())
    manifest_errors, course_id, course_status, target, implemented = validate_manifest(
        manifest, pack_dir=pack_dir
    )
    errors.extend(manifest_errors)
    if course_id not in COURSE_ID_PREFIXES:
        course_id = pack_dir.name
    content_roots = {pack_dir / directory for directory in CONTENT_DIRECTORIES.values()}
    for directory in CONTENT_DIRECTORIES.values():
        content_root = pack_dir / directory
        if not content_root.is_dir():
            errors.append(f"{pack_dir.name}: missing {directory}/")
    allowed_root_files = {manifest_path, pack_dir / "handoff.yaml"}
    for misplaced_record in sorted(
        path
        for path in pack_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in CONTENT_SUFFIXES
        and path not in allowed_root_files
        and path.parent not in content_roots
    ):
        relative_path = misplaced_record.relative_to(pack_dir)
        errors.append(
            f"{pack_dir.name}: YAML/JSON records must use the canonical flat layout: "
            f"{relative_path}"
        )
    expected_prefix = COURSE_ID_PREFIXES.get(course_id)
    source_prefix = SOURCE_ID_PREFIXES.get(course_id)
    if expected_prefix is None or source_prefix is None:
        return PackValidation(errors, ())
    records: list[ContentRecord] = []
    validators: tuple[tuple[str, RecordValidator], ...] = (
        (
            "concepts",
            lambda path: validate_concept_file(
                path, course_id=course_id, expected_prefix=expected_prefix
            ),
        ),
        (
            "exercises",
            lambda path: validate_exercise_file(
                path, course_id=course_id, expected_prefix=expected_prefix
            ),
        ),
        (
            "sources",
            lambda path: validate_source_file(
                path,
                pack_dir=pack_dir,
                course_id=course_id,
                expected_prefix=source_prefix,
            ),
        ),
        (
            "projects",
            lambda path: validate_project_file(
                path, course_id=course_id, expected_prefix=expected_prefix
            ),
        ),
    )
    concept_count = 0
    for directory, validator in validators:
        paths = record_paths(pack_dir / directory)
        if directory == "concepts":
            concept_count = len(paths)
        for path in paths:
            record_errors, record = validator(path)
            errors.extend(record_errors)
            if record is not None:
                records.append(record)
    if implemented is not None and implemented != concept_count:
        errors.append(
            f"{pack_dir.name}: implemented_core_concepts={implemented}, "
            f"but {concept_count} concept files exist"
        )
    records_by_id: dict[str, list[ContentRecord]] = {}
    for record in records:
        records_by_id.setdefault(record.record_id, []).append(record)
    for record_id, duplicates in sorted(records_by_id.items()):
        if len(duplicates) > 1:
            locations = ", ".join(str(record.path.relative_to(pack_dir)) for record in duplicates)
            errors.append(f"{pack_dir.name}: duplicate content id {record_id} in {locations}")
    unique_records = {
        record_id: duplicates[0]
        for record_id, duplicates in records_by_id.items()
        if len(duplicates) == 1
    }
    records_by_kind = {
        kind: {
            record_id: record for record_id, record in unique_records.items() if record.kind == kind
        }
        for kind in ("concept", "exercise", "project", "source")
    }
    for record in records:
        add_missing_reference_errors(
            errors,
            record=record,
            refs=record.prerequisites,
            target_records=records_by_kind["concept"],
            field_name="prerequisite",
            course_id=course_id,
        )
        if record.kind == "concept":
            for exercise_id in record.assessment_refs:
                exercise = records_by_kind["exercise"].get(exercise_id)
                if exercise is not None and record.record_id not in exercise.concept_refs:
                    errors.append(
                        f"{course_id}/concepts/{record.path.name}: assessment {exercise_id} "
                        "does not reference this concept"
                    )
        if record.kind == "project":
            for exercise_id in record.assessment_refs:
                exercise = records_by_kind["exercise"].get(exercise_id)
                if exercise is not None and exercise.exercise_type not in {"code", "debug"}:
                    errors.append(
                        f"{course_id}/projects/{record.path.name}: verification exercise "
                        f"{exercise_id} must be code or debug"
                    )
                elif exercise is not None and not set(record.concept_refs).intersection(
                    exercise.concept_refs
                ):
                    errors.append(
                        f"{course_id}/projects/{record.path.name}: verification exercise "
                        f"{exercise_id} must cover a project concept"
                    )
            if record.scenario_provider == "tuoling":
                for source_id in record.fallback_refs:
                    source = records_by_kind["source"].get(source_id)
                    if source is not None and not source.is_synthetic_source:
                        errors.append(
                            f"{course_id}/projects/{record.path.name}: fallback source "
                            f"{source_id} must be a consistently declared synthetic source"
                        )
            if record.scenario_provider == "fixed_synthetic" and not any(
                source is not None and source.is_synthetic_source
                for source in (
                    records_by_kind["source"].get(source_id) for source_id in record.source_refs
                )
            ):
                errors.append(
                    f"{course_id}/projects/{record.path.name}: fixed_synthetic projects "
                    "require at least one consistently declared synthetic source"
                )
        add_missing_reference_errors(
            errors,
            record=record,
            refs=record.concept_refs,
            target_records=records_by_kind["concept"],
            field_name="concept reference",
            course_id=course_id,
        )
        add_missing_reference_errors(
            errors,
            record=record,
            refs=record.source_refs,
            target_records=records_by_kind["source"],
            field_name="source reference",
            course_id=course_id,
        )
        add_missing_reference_errors(
            errors,
            record=record,
            refs=record.assessment_refs,
            target_records=records_by_kind["exercise"],
            field_name="assessment reference",
            course_id=course_id,
        )
    for cycle in find_prerequisite_cycles(records_by_kind["concept"]):
        errors.append(f"{pack_dir.name}: prerequisite cycle detected: {cycle}")
    handoff: HandoffRecord | None = None
    handoff_path = pack_dir / "handoff.yaml"
    for candidate in sorted(path for path in pack_dir.glob("handoff*") if path.is_file()):
        if candidate.name != handoff_path.name:
            errors.append(
                f"{pack_dir.name}: handoff file must be named handoff.yaml, not {candidate.name}"
            )
    if handoff_path.is_file():
        handoff_errors, handoff = validate_handoff_file(handoff_path, course_id=course_id)
        errors.extend(handoff_errors)
        if handoff is not None:
            validate_handoff_references(
                errors, handoff=handoff, records_by_kind=records_by_kind, course_id=course_id
            )
    if course_status == "scaffold" and (records or handoff is not None):
        errors.append(f"{pack_dir.name}: scaffold courses cannot contain content records")
    if course_status == "published":
        if target is not None and concept_count != target:
            errors.append(f"{pack_dir.name}: published courses must reach target_core_concepts")
        if not records_by_kind["project"]:
            errors.append(f"{pack_dir.name}: published courses require at least one project")
        practice_concepts = {
            concept_id
            for record in records_by_kind["exercise"].values()
            if record.exercise_type in {"code", "debug"}
            for concept_id in record.concept_refs
        }
        if len(practice_concepts) < 8:
            errors.append(
                f"{pack_dir.name}: published courses require practice for at least 8 concepts"
            )
        if any(record.status != "reviewed" for record in records):
            errors.append(f"{pack_dir.name}: published courses may contain only reviewed records")
        if handoff is None or handoff.status != "reviewed":
            errors.append(f"{pack_dir.name}: published courses require a reviewed handoff.yaml")
    return PackValidation(errors, tuple(records))


def validate_pack(pack_dir: Path) -> list[str]:
    """Validate one course pack, including all cross references."""

    return validate_pack_details(pack_dir).errors


def validate_course_packs(pack_dirs: list[Path]) -> list[str]:
    """Validate packs and enforce repository-wide content ID uniqueness."""

    validations = [(pack_dir, validate_pack_details(pack_dir)) for pack_dir in pack_dirs]
    errors = [error for _, validation in validations for error in validation.errors]
    global_locations: dict[str, list[Path]] = {}
    for _, validation in validations:
        for record in validation.records:
            global_locations.setdefault(record.record_id, []).append(record.path)
    for record_id, paths in sorted(global_locations.items()):
        if len(paths) > 1:
            locations = ", ".join(str(path.relative_to(COURSE_PACKS_ROOT)) for path in paths)
            errors.append(f"duplicate content id {record_id} across course packs: {locations}")
    return errors


def main() -> int:
    pack_dirs = sorted(
        path
        for path in COURSE_PACKS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    )
    errors = validate_course_packs(pack_dirs)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(pack_dirs)} course packs: {', '.join(path.name for path in pack_dirs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
