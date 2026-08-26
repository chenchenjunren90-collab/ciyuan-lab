"""Course catalog: the real, file-backed activity directory for one course.

AGENT-01 must never invent knowledge points, exercises or projects. This module
loads the actual course pack from ``course_packs/<course_id>/`` so that every
planned activity id can be verified against content that really exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

CONCEPT = "concept"
OBJECTIVE = "objective"
SHORT_ANSWER = "short_answer"
CODE = "code"
DEBUG = "debug"
PROJECT = "project"

ACTIVITY_TYPES: frozenset[str] = frozenset({CONCEPT, OBJECTIVE, SHORT_ANSWER, CODE, DEBUG, PROJECT})

EXERCISE_TYPE_PREFERENCE: tuple[str, ...] = (CODE, DEBUG, OBJECTIVE, SHORT_ANSWER)

_COURSE_PACK_DIRECTORY = "course_packs"


class CourseCatalogError(Exception):
    """Raised when a course catalog cannot be loaded or queried."""


class CourseNotFoundError(CourseCatalogError):
    """Raised when the requested course pack does not exist."""


@dataclass(frozen=True, slots=True)
class CourseKnowledgePoint:
    knowledge_point_id: str
    prerequisites: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CourseActivity:
    activity_id: str
    activity_type: str
    title: str
    concept_ids: tuple[str, ...]
    prerequisites: tuple[str, ...]

    @property
    def knowledge_point_id(self) -> str | None:
        """Primary knowledge point for concept/exercise activities."""
        if self.activity_type == CONCEPT:
            return self.activity_id
        if self.concept_ids:
            return self.concept_ids[0]
        return None


@dataclass(frozen=True, slots=True)
class CourseCatalog:
    course_id: str
    activities: tuple[CourseActivity, ...]
    knowledge_points: tuple[CourseKnowledgePoint, ...]

    def activity(self, activity_id: str) -> CourseActivity | None:
        for item in self.activities:
            if item.activity_id == activity_id:
                return item
        return None

    def activities_for_kp(self, knowledge_point_id: str) -> tuple[CourseActivity, ...]:
        return tuple(
            item
            for item in self.activities
            if (item.activity_type == CONCEPT and item.activity_id == knowledge_point_id)
            or knowledge_point_id in item.concept_ids
        )

    def concept(self, knowledge_point_id: str) -> CourseActivity | None:
        return self.activity(knowledge_point_id)

    def exercises_for_kp(
        self, knowledge_point_id: str, *, order: tuple[str, ...] = EXERCISE_TYPE_PREFERENCE
    ) -> tuple[CourseActivity, ...]:
        """Exercises for one knowledge point, most preferred type first."""
        preference = {activity_type: index for index, activity_type in enumerate(order)}
        exercises = [
            item
            for item in self.activities_for_kp(knowledge_point_id)
            if item.activity_type in preference
        ]
        return tuple(
            sorted(
                exercises,
                key=lambda item: (preference[item.activity_type], item.activity_id),
            )
        )


def default_packs_root() -> Path:
    """Repository root relative to this source file: apps/api/app/modules/orchestration."""
    return Path(__file__).resolve().parents[5] / _COURSE_PACK_DIRECTORY


def load_course_catalog(course_id: str, *, packs_root: Path | str | None = None) -> CourseCatalog:
    """Load one course pack into an in-memory, immutable activity directory."""
    root = Path(packs_root) if packs_root else default_packs_root()
    pack_dir = root / course_id
    if not pack_dir.is_dir():
        raise CourseNotFoundError(f"course pack not found: {course_id}")
    manifest_path = pack_dir / "manifest.yaml"
    if not manifest_path.is_file():
        raise CourseNotFoundError(f"course pack has no manifest.yaml: {course_id}")

    manifest = _load_mapping(manifest_path)
    content = manifest.get("content")
    if not isinstance(content, dict):
        raise CourseCatalogError(f"{course_id}: manifest content must be a mapping")
    concepts_dir = str(content.get("concepts_dir") or "concepts")
    exercises_dir = str(content.get("exercises_dir") or "exercises")
    projects_dir = str(content.get("projects_dir") or "projects")

    knowledge_points: list[CourseKnowledgePoint] = []
    activities: list[CourseActivity] = []

    for path in _yaml_files(pack_dir / concepts_dir):
        document = _load_mapping(path)
        kp_id = _require_id(document, path)
        knowledge_points.append(
            CourseKnowledgePoint(
                knowledge_point_id=kp_id,
                prerequisites=_string_tuple(document.get("prerequisites")),
            )
        )
        activities.append(
            CourseActivity(
                activity_id=kp_id,
                activity_type=CONCEPT,
                title=_title(document, kp_id),
                concept_ids=(kp_id,),
                prerequisites=_string_tuple(document.get("prerequisites")),
            )
        )

    prerequisites_by_kp = {item.knowledge_point_id: item.prerequisites for item in knowledge_points}

    for path in _yaml_files(pack_dir / exercises_dir):
        document = _load_mapping(path)
        exercise_id = _require_id(document, path)
        exercise_type = document.get("type")
        if not isinstance(exercise_type, str) or exercise_type not in ACTIVITY_TYPES:
            raise CourseCatalogError(
                f"{course_id}/exercises/{path.name}: unsupported type {exercise_type!r}"
            )
        concept_ids = _string_tuple(document.get("concept_ids"))
        _validate_concept_ids(
            course_id=course_id,
            record_id=exercise_id,
            concept_ids=concept_ids,
            prerequisites_by_kp=prerequisites_by_kp,
        )
        activities.append(
            CourseActivity(
                activity_id=exercise_id,
                activity_type=exercise_type,
                title=_title(document, exercise_id),
                concept_ids=concept_ids,
                prerequisites=_combined_prerequisites(concept_ids, prerequisites_by_kp),
            )
        )

    for path in _yaml_files(pack_dir / projects_dir):
        document = _load_mapping(path)
        project_id = _require_id(document, path)
        concept_ids = _string_tuple(document.get("concept_ids"))
        _validate_concept_ids(
            course_id=course_id,
            record_id=project_id,
            concept_ids=concept_ids,
            prerequisites_by_kp=prerequisites_by_kp,
        )
        activities.append(
            CourseActivity(
                activity_id=project_id,
                activity_type=PROJECT,
                title=_title(document, project_id),
                concept_ids=concept_ids,
                prerequisites=(),
            )
        )

    return CourseCatalog(
        course_id=course_id,
        activities=tuple(activities),
        knowledge_points=tuple(knowledge_points),
    )


def _yaml_files(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
        )
    )


def _load_mapping(path: Path) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as content_file:
            data = yaml.safe_load(content_file)
    except (OSError, yaml.YAMLError) as exc:
        raise CourseCatalogError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise CourseCatalogError(f"{path.name} root must be a mapping")
    return data


def _require_id(document: dict[str, object], path: Path) -> str:
    record_id = document.get("id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise CourseCatalogError(f"{path.name}: id must be a non-empty string")
    return record_id


def _title(document: dict[str, object], record_id: str) -> str:
    title = document.get("title")
    return title if isinstance(title, str) and title.strip() else record_id


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _validate_concept_ids(
    *,
    course_id: str,
    record_id: str,
    concept_ids: tuple[str, ...],
    prerequisites_by_kp: dict[str, tuple[str, ...]],
) -> None:
    if not concept_ids:
        raise CourseCatalogError(f"{course_id}/{record_id}: concept_ids must not be empty")
    unknown = sorted(set(concept_ids) - set(prerequisites_by_kp))
    if unknown:
        raise CourseCatalogError(f"{course_id}/{record_id}: unknown concept_ids: {unknown}")


def _combined_prerequisites(
    concept_ids: tuple[str, ...],
    prerequisites_by_kp: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Prerequisites required before practising any linked concept."""

    return tuple(
        sorted(
            {
                prerequisite
                for concept_id in concept_ids
                for prerequisite in prerequisites_by_kp[concept_id]
            }
        )
    )
