"""Validate the repository-level contracts and required scaffold files."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    Path(".env.example"),
    Path("apps/api/app/main.py"),
    Path("apps/api/tests/test_contracts.py"),
    Path("apps/web/.env.example"),
    Path("apps/web/package-lock.json"),
    Path("contracts/openapi.yaml"),
    Path("contracts/events/learning-event.schema.json"),
    Path("course_packs/c/manifest.yaml"),
    Path("course_packs/python/manifest.yaml"),
    Path("course_packs/data_structures/manifest.yaml"),
    Path("infra/compose.yaml"),
)
REQUIRED_API_PATHS = {"/health", "/api/v1/health", "/api/v1/capabilities"}
REQUIRED_EVENT_FIELDS = {
    "schema_version",
    "event_id",
    "event_type",
    "occurred_at",
    "student_id",
    "course_id",
    "payload",
}
REQUIRED_SERVICES = {"postgres", "redis"}


def require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    return cast(Mapping[str, object], value)


def load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as source_file:
        document: object = yaml.safe_load(source_file)
    return document


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as source_file:
        document: object = json.load(source_file)
    return document


def validate_required_files() -> list[str]:
    return [
        f"required file is missing: {path.as_posix()}"
        for path in REQUIRED_FILES
        if not (REPO_ROOT / path).is_file()
    ]


def validate_openapi() -> list[str]:
    path = REPO_ROOT / "contracts" / "openapi.yaml"
    try:
        document = require_mapping(load_yaml(path), "OpenAPI document")
        paths = require_mapping(document.get("paths"), "OpenAPI paths")
        schemas = require_mapping(
            require_mapping(document.get("components"), "OpenAPI components").get("schemas"),
            "OpenAPI component schemas",
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"cannot parse contracts/openapi.yaml: {exc}"]

    errors: list[str] = []
    if document.get("openapi") != "3.1.0":
        errors.append("contracts/openapi.yaml must declare OpenAPI 3.1.0")
    missing_paths = REQUIRED_API_PATHS - set(paths)
    if missing_paths:
        errors.append(f"OpenAPI paths are missing: {', '.join(sorted(missing_paths))}")
    for schema_name in ("HealthResponse", "CapabilitiesResponse"):
        if schema_name not in schemas:
            errors.append(f"OpenAPI component schema is missing: {schema_name}")
    return errors


def validate_learning_event_schema() -> list[str]:
    path = REPO_ROOT / "contracts" / "events" / "learning-event.schema.json"
    try:
        document = require_mapping(load_json(path), "learning-event schema")
        properties = require_mapping(document.get("properties"), "learning-event properties")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot parse contracts/events/learning-event.schema.json: {exc}"]

    errors: list[str] = []
    required = document.get("required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("learning-event required must be a list of field names")
        required_fields: set[str] = set()
    else:
        required_fields = set(required)
    missing_required = REQUIRED_EVENT_FIELDS - required_fields
    if missing_required:
        errors.append(
            "learning-event required fields are missing: "
            + ", ".join(sorted(missing_required))
        )
    missing_properties = REQUIRED_EVENT_FIELDS - set(properties)
    if missing_properties:
        errors.append(
            "learning-event properties are missing: "
            + ", ".join(sorted(missing_properties))
        )
    return errors


def validate_compose() -> list[str]:
    path = REPO_ROOT / "infra" / "compose.yaml"
    try:
        document = require_mapping(load_yaml(path), "Compose document")
        services = require_mapping(document.get("services"), "Compose services")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"cannot parse infra/compose.yaml: {exc}"]

    missing_services = REQUIRED_SERVICES - set(services)
    if missing_services:
        return [f"Compose services are missing: {', '.join(sorted(missing_services))}"]
    return []


def main() -> int:
    errors = [
        *validate_required_files(),
        *validate_openapi(),
        *validate_learning_event_schema(),
        *validate_compose(),
    ]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Validated repository contracts, Compose scaffold and required files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
