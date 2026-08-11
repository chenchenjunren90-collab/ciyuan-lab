"""Validate course-pack structure and concept metadata.

The three course packs may remain empty while they are scaffolds. As soon as a
member adds a YAML or JSON concept file, however, the shared course contract is
checked so incomplete or disconnected content cannot silently enter the MVP.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]
COURSE_PACKS_ROOT = REPO_ROOT / "course_packs"
REQUIRED_DIRECTORIES = ("concepts", "exercises", "projects", "sources")
CONTENT_SUFFIXES = {".json", ".yaml", ".yml"}
COURSE_ID_PREFIXES = {
    "c": "C-",
    "python": "PY-",
    "data_structures": "DS-",
}
CONCEPT_SCHEMA_VERSION = "0.1.0"
CONCEPT_STATUSES = {"draft", "reviewed"}


@dataclass(frozen=True)
class ConceptRecord:
    """The graph fields retained after validating a concept file."""

    concept_id: str
    prerequisites: tuple[str, ...]
    path: Path


@dataclass(frozen=True)
class PackValidation:
    """Validation result plus concept IDs used for repository-wide checks."""

    errors: list[str]
    records: tuple[ConceptRecord, ...]


def load_mapping(path: Path, description: str) -> dict[str, Any]:
    """Load a YAML/JSON file and require a mapping at its root."""

    with path.open(encoding="utf-8") as content_file:
        if path.suffix.lower() == ".json":
            data = json.load(content_file)
        else:
            data = yaml.safe_load(content_file)
    if not isinstance(data, dict):
        raise ValueError(f"{description} root must be a mapping")
    return data


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a course manifest."""

    return load_mapping(path, "manifest")


def require_mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_list(
    value: object,
    *,
    field_name: str,
    file_label: str,
    allow_empty: bool,
) -> tuple[list[str], tuple[str, ...]]:
    """Validate a list of non-empty, non-duplicated strings."""

    if not isinstance(value, list):
        return [f"{file_label}: {field_name} must be a list"], ()
    if not value and not allow_empty:
        return [f"{file_label}: {field_name} must not be empty"], ()
    if not all(is_non_empty_string(item) for item in value):
        return [f"{file_label}: {field_name} must contain only non-empty strings"], ()

    values = tuple(str(item).strip() for item in value)
    if len(values) != len(set(values)):
        return [f"{file_label}: {field_name} contains duplicate values"], values
    return [], values


def validate_concept_file(
    path: Path,
    *,
    course_id: str,
    expected_prefix: str,
) -> tuple[list[str], ConceptRecord | None]:
    """Validate one concept document and return its graph fields when usable."""

    file_label = f"{course_id}/concepts/{path.name}"
    try:
        concept = load_mapping(path, "concept")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{file_label}: cannot read concept: {exc}"], None

    errors: list[str] = []
    concept_id_value = concept.get("id")
    concept_id = concept_id_value.strip() if isinstance(concept_id_value, str) else ""
    if not concept_id:
        errors.append(f"{file_label}: id must be a non-empty string")
    elif not concept_id.startswith(expected_prefix) or len(concept_id) == len(expected_prefix):
        errors.append(f"{file_label}: id must start with {expected_prefix} and include a suffix")

    if not is_non_empty_string(concept.get("title")):
        errors.append(f"{file_label}: title must be a non-empty string")
    if concept.get("course") != course_id:
        errors.append(f"{file_label}: course must be {course_id}")
    if concept.get("schema_version") != CONCEPT_SCHEMA_VERSION:
        errors.append(
            f"{file_label}: schema_version must be {CONCEPT_SCHEMA_VERSION}"
        )

    version = concept.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        errors.append(f"{file_label}: version must be a positive integer")
    if not is_non_empty_string(concept.get("difficulty")):
        errors.append(f"{file_label}: difficulty must be a non-empty string")

    estimated_minutes = concept.get("estimated_minutes")
    if (
        isinstance(estimated_minutes, bool)
        or not isinstance(estimated_minutes, int)
        or estimated_minutes < 1
    ):
        errors.append(f"{file_label}: estimated_minutes must be a positive integer")

    prerequisite_errors, prerequisites = validate_string_list(
        concept.get("prerequisites"),
        field_name="prerequisites",
        file_label=file_label,
        allow_empty=True,
    )
    errors.extend(prerequisite_errors)
    for field_name in ("learning_objectives", "concepts", "assessment_ids", "source_refs"):
        field_errors, _ = validate_string_list(
            concept.get(field_name),
            field_name=field_name,
            file_label=file_label,
            allow_empty=False,
        )
        errors.extend(field_errors)

    lesson = concept.get("lesson")
    if not isinstance(lesson, dict) or not is_non_empty_string(lesson.get("summary")):
        errors.append(f"{file_label}: lesson.summary must be a non-empty string")
    if concept.get("status") not in CONCEPT_STATUSES:
        allowed = ", ".join(sorted(CONCEPT_STATUSES))
        errors.append(f"{file_label}: status must be one of: {allowed}")

    record = None
    if concept_id and not prerequisite_errors:
        record = ConceptRecord(concept_id, prerequisites, path)
    return errors, record


def find_prerequisite_cycles(records_by_id: dict[str, ConceptRecord]) -> list[str]:
    """Return stable, human-readable cycles in the prerequisite graph."""

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
                cycle = tuple(trail[cycle_start:] + [prerequisite])
                cycles.add(cycle)
        trail.pop()
        state[concept_id] = 2

    for concept_id in sorted(records_by_id):
        if state.get(concept_id, 0) == 0:
            visit(concept_id)
    return [" -> ".join(cycle) for cycle in sorted(cycles)]


def validate_pack_details(pack_dir: Path) -> PackValidation:
    errors: list[str] = []
    manifest_path = pack_dir / "manifest.yaml"
    if not manifest_path.is_file():
        return PackValidation([f"{pack_dir.name}: manifest.yaml is missing"], ())

    try:
        manifest = load_manifest(manifest_path)
        course = require_mapping(manifest.get("course"), "course")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return PackValidation([f"{pack_dir.name}: cannot read manifest: {exc}"], ())

    if manifest.get("schema_version") != CONCEPT_SCHEMA_VERSION:
        errors.append(
            f"{pack_dir.name}: schema_version must be {CONCEPT_SCHEMA_VERSION}"
        )
    if course.get("id") != pack_dir.name:
        errors.append(f"{pack_dir.name}: course.id must match the directory name")
    if course.get("status") not in {"scaffold", "draft", "review", "published"}:
        errors.append(f"{pack_dir.name}: unsupported course.status")

    target = course.get("target_core_concepts")
    implemented = course.get("implemented_core_concepts")
    if isinstance(target, bool) or not isinstance(target, int) or not 30 <= target <= 50:
        errors.append(f"{pack_dir.name}: target_core_concepts must be between 30 and 50")
    if isinstance(implemented, bool) or not isinstance(implemented, int) or implemented < 0:
        errors.append(f"{pack_dir.name}: implemented_core_concepts must be a non-negative integer")
    if isinstance(target, int) and isinstance(implemented, int) and implemented > target:
        errors.append(f"{pack_dir.name}: implemented_core_concepts exceeds target")

    for directory in REQUIRED_DIRECTORIES:
        if not (pack_dir / directory).is_dir():
            errors.append(f"{pack_dir.name}: missing {directory}/")

    concepts_dir = pack_dir / "concepts"
    concept_paths = (
        sorted(
            path
            for path in concepts_dir.iterdir()
            if path.is_file() and path.suffix.lower() in CONTENT_SUFFIXES
        )
        if concepts_dir.is_dir()
        else []
    )
    if isinstance(implemented, int) and implemented != len(concept_paths):
        errors.append(
            f"{pack_dir.name}: implemented_core_concepts={implemented}, "
            f"but {len(concept_paths)} concept files exist"
        )

    expected_prefix = COURSE_ID_PREFIXES.get(pack_dir.name)
    if expected_prefix is None and concept_paths:
        errors.append(f"{pack_dir.name}: no concept ID prefix is registered")
        return PackValidation(errors, ())

    records: list[ConceptRecord] = []
    if expected_prefix is not None:
        for concept_path in concept_paths:
            concept_errors, record = validate_concept_file(
                concept_path,
                course_id=pack_dir.name,
                expected_prefix=expected_prefix,
            )
            errors.extend(concept_errors)
            if record is not None:
                records.append(record)

    records_by_id: dict[str, list[ConceptRecord]] = {}
    for record in records:
        records_by_id.setdefault(record.concept_id, []).append(record)
    duplicate_ids = {
        concept_id: concept_records
        for concept_id, concept_records in records_by_id.items()
        if len(concept_records) > 1
    }
    for concept_id, concept_records in sorted(duplicate_ids.items()):
        names = ", ".join(record.path.name for record in concept_records)
        errors.append(f"{pack_dir.name}: duplicate concept id {concept_id} in {names}")

    unique_records = {
        concept_id: concept_records[0]
        for concept_id, concept_records in records_by_id.items()
        if len(concept_records) == 1
    }
    all_ids = set(records_by_id)
    for record in records:
        for prerequisite in record.prerequisites:
            if prerequisite not in all_ids:
                errors.append(
                    f"{pack_dir.name}/concepts/{record.path.name}: "
                    f"prerequisite {prerequisite} does not exist"
                )
    for cycle in find_prerequisite_cycles(unique_records):
        errors.append(f"{pack_dir.name}: prerequisite cycle detected: {cycle}")

    return PackValidation(errors, tuple(records))


def validate_pack(pack_dir: Path) -> list[str]:
    """Validate one course pack, including concept relationships."""

    return validate_pack_details(pack_dir).errors


def validate_course_packs(pack_dirs: list[Path]) -> list[str]:
    """Validate packs and enforce concept ID uniqueness across the repository."""

    validations = [(pack_dir, validate_pack_details(pack_dir)) for pack_dir in pack_dirs]
    errors = [error for _, validation in validations for error in validation.errors]
    global_locations: dict[str, list[Path]] = {}
    for _, validation in validations:
        for record in validation.records:
            global_locations.setdefault(record.concept_id, []).append(record.path)
    for concept_id, paths in sorted(global_locations.items()):
        if len(paths) > 1:
            locations = ", ".join(str(path.relative_to(COURSE_PACKS_ROOT)) for path in paths)
            errors.append(f"duplicate concept id {concept_id} across course packs: {locations}")
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
    print(f"Validated {len(pack_dirs)} course packs: {', '.join(p.name for p in pack_dirs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
