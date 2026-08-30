"""Read validated course packs without exposing answer keys or hidden tests."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from app.modules.course_content.models import (
    ActivityDetail,
    ActivityExample,
    ActivitySummary,
    CourseId,
    CourseSummary,
    CourseVersionMetadata,
    KnowledgePointDetail,
    KnowledgePointSummary,
    LearningStage,
    PracticeActivityRecord,
    RagSourceRecord,
    SourceDetail,
)

COURSE_IDS: tuple[CourseId, ...] = ("c", "python", "data_structures")


class CourseContentError(Exception):
    """Base error for invalid or unreadable course content."""


class CourseRecordNotFoundError(CourseContentError):
    """Requested course record does not exist."""


def default_packs_root() -> Path:
    return Path(__file__).resolve().parents[5] / "course_packs"


class CoursePackRepository:
    """Immutable-at-runtime view over the version-controlled course packs."""

    def __init__(self, packs_root: Path | str | None = None) -> None:
        self._root = (Path(packs_root) if packs_root else default_packs_root()).resolve()

    def list_courses(self) -> tuple[CourseSummary, ...]:
        return tuple(self.get_course(course_id) for course_id in COURSE_IDS)

    @lru_cache(maxsize=3)  # noqa: B019 - repository instance has process lifetime
    def get_course(self, course_id: CourseId) -> CourseSummary:
        document = self._load_record(course_id, "manifest.yaml")
        course = self._mapping(document.get("course"), "manifest.course")
        features = self._mapping(document.get("features"), "manifest.features")
        return CourseSummary(
            id=course_id,
            title=self._required_string(course, "title"),
            status=self._required_string(course, "status"),
            target_core_concepts=self._required_int(course, "target_core_concepts"),
            implemented_core_concepts=self._required_int(course, "implemented_core_concepts"),
            features={str(key): str(value) for key, value in features.items()},
        )

    @lru_cache(maxsize=3)  # noqa: B019 - repository instance has process lifetime
    def get_version_metadata(self, course_id: CourseId) -> CourseVersionMetadata:
        path = self._course_dir(course_id) / "manifest.yaml"
        try:
            manifest_bytes = path.read_bytes()
        except OSError as exc:
            raise CourseContentError(f"cannot read manifest for {course_id}: {exc}") from exc
        document = self._load_path(path)
        course = self._mapping(document.get("course"), "manifest.course")
        version = document.get("schema_version")
        if not isinstance(version, (str, int, float)) or isinstance(version, bool):
            raise CourseContentError("manifest.schema_version must be a scalar")
        return CourseVersionMetadata(
            course_id=course_id,
            version=str(version),
            title=self._required_string(course, "title"),
            status=self._required_string(course, "status"),
            manifest_hash=hashlib.sha256(manifest_bytes).hexdigest(),
        )

    def list_knowledge_points(self, course_id: CourseId) -> tuple[KnowledgePointSummary, ...]:
        return tuple(
            self._knowledge_point_summary(self._knowledge_point(course_id, self._load_path(path)))
            for path in self._record_paths(course_id, "concepts")
        )

    def get_knowledge_point(
        self, course_id: CourseId, knowledge_point_id: str
    ) -> KnowledgePointDetail:
        return self._knowledge_point(
            course_id,
            self._load_named_record(course_id, "concepts", knowledge_point_id),
        )

    def list_activities(self, course_id: CourseId) -> tuple[ActivitySummary, ...]:
        activities: list[ActivitySummary] = []
        for directory, activity_type in (("exercises", None), ("projects", "project")):
            for path in self._record_paths(course_id, directory):
                document = self._load_path(path)
                activities.append(self._activity_summary(course_id, document, activity_type))
        return tuple(activities)

    def get_activity(self, course_id: CourseId, activity_id: str) -> ActivityDetail:
        for directory, forced_type in (("exercises", None), ("projects", "project")):
            path = self._record_path(course_id, directory, activity_id)
            if path.is_file():
                return self._activity_detail(course_id, self._load_path(path), forced_type)
        raise CourseRecordNotFoundError(f"activity not found in course {course_id}: {activity_id}")

    def get_practice_activity(
        self, course_id: CourseId, activity_id: str
    ) -> PracticeActivityRecord:
        document = self._load_named_record(course_id, "exercises", activity_id)
        return PracticeActivityRecord(
            id=self._required_string(document, "id"),
            course=course_id,
            type=cast(Any, self._required_string(document, "type")),
            concept_ids=tuple(self._string_list(document.get("concept_ids"))),
            prompt=self._required_string(document, "prompt"),
            source_refs=tuple(self._string_list(document.get("source_refs"))),
            evaluation=dict(self._mapping(document.get("evaluation"), "evaluation")),
        )

    def list_sources(self, course_id: CourseId) -> tuple[SourceDetail, ...]:
        return tuple(
            self._source(course_id, self._load_path(path))
            for path in self._record_paths(course_id, "sources")
        )

    def get_source(self, course_id: CourseId, source_id: str) -> SourceDetail:
        return self._source(
            course_id,
            self._load_named_record(course_id, "sources", source_id),
        )

    def list_rag_source_records(self, course_id: CourseId) -> tuple[RagSourceRecord, ...]:
        """Load only reviewed, explicitly eligible bodies for server-side retrieval."""

        records: list[RagSourceRecord] = []
        for path in self._record_paths(course_id, "sources"):
            document = self._load_path(path)
            rag = self._mapping(document.get("rag"), "rag")
            if document.get("status") != "reviewed" or rag.get("eligible") is not True:
                continue
            content = self._mapping(rag.get("content"), "rag.content")
            text = self._rag_text(course_id, content)
            if not text.strip():
                continue
            records.append(
                RagSourceRecord(
                    id=self._required_string(document, "id"),
                    title=self._required_string(document, "title"),
                    course=course_id,
                    citation=dict(self._mapping(document.get("citation"), "citation")),
                    text=text,
                )
            )
        return tuple(records)

    def _knowledge_point(
        self, course_id: CourseId, document: dict[str, Any]
    ) -> KnowledgePointDetail:
        return KnowledgePointDetail(
            id=self._required_string(document, "id"),
            title=self._required_string(document, "title"),
            course=course_id,
            difficulty=cast(Any, self._required_string(document, "difficulty")),
            estimated_minutes=self._required_int(document, "estimated_minutes"),
            prerequisites=self._string_list(document.get("prerequisites")),
            learning_objectives=self._string_list(document.get("learning_objectives")),
            concepts=self._string_list(document.get("concepts")),
            lesson=dict(self._mapping(document.get("lesson"), "lesson")),
            assessment_ids=self._string_list(document.get("assessment_ids")),
            source_refs=self._string_list(document.get("source_refs")),
            status=self._required_string(document, "status"),
        )

    @staticmethod
    def _knowledge_point_summary(
        detail: KnowledgePointDetail,
    ) -> KnowledgePointSummary:
        return KnowledgePointSummary(
            id=detail.id,
            title=detail.title,
            difficulty=detail.difficulty,
            prerequisites=detail.prerequisites,
            concepts=detail.concepts,
            source_refs=detail.source_refs,
        )

    def _activity_summary(
        self,
        course_id: CourseId,
        document: dict[str, Any],
        forced_type: str | None,
    ) -> ActivitySummary:
        extensions = self._optional_mapping(document.get("extensions"))
        learning_stage = self._optional_string(extensions.get("learning_stage"))
        return ActivitySummary(
            id=self._required_string(document, "id"),
            title=self._required_string(document, "title"),
            course=course_id,
            type=cast(
                Any,
                forced_type or self._required_string(document, "type"),
            ),
            difficulty=cast(Any, self._required_string(document, "difficulty")),
            estimated_minutes=self._required_int(document, "estimated_minutes"),
            concept_ids=self._string_list(document.get("concept_ids")),
            source_refs=self._string_list(document.get("source_refs")),
            learning_stage=cast(LearningStage | None, learning_stage),
        )

    def _activity_detail(
        self,
        course_id: CourseId,
        document: dict[str, Any],
        forced_type: str | None,
    ) -> ActivityDetail:
        summary = self._activity_summary(course_id, document, forced_type)
        evaluation = self._student_evaluation(
            self._mapping(document.get("evaluation"), "evaluation")
        )
        fallback_value = document.get("fallback")
        fallback = fallback_value if isinstance(fallback_value, dict) else {}
        extensions = self._optional_mapping(document.get("extensions"))
        examples = extensions.get("public_examples")
        public_examples = (
            [ActivityExample.model_validate(item) for item in examples if isinstance(item, dict)]
            if isinstance(examples, list)
            else []
        )
        source_adaptation = self._optional_mapping(extensions.get("source_adaptation"))
        return ActivityDetail(
            **summary.model_dump(),
            prompt=self._optional_string(document.get("prompt")),
            summary=self._optional_string(document.get("summary")),
            requirements=self._string_list(document.get("requirements")),
            deliverables=self._string_list(document.get("deliverables")),
            evaluation=evaluation,
            scenario_scope=self._optional_string(document.get("scenario_scope")),
            scenario_provider=self._optional_string(document.get("scenario_provider")),
            data_classification=self._optional_string(document.get("data_classification")),
            computer_science_objectives=self._string_list(
                document.get("computer_science_objectives")
            ),
            business_context_objectives=self._string_list(
                document.get("business_context_objectives")
            ),
            fallback_source_refs=self._string_list(fallback.get("source_refs")),
            audience=self._optional_string(extensions.get("audience")),
            scaffolding=self._string_list(extensions.get("scaffolding")),
            input_format=self._optional_string(extensions.get("input_format")),
            output_format=self._optional_string(extensions.get("output_format")),
            constraints=self._string_list(extensions.get("constraints")),
            public_examples=public_examples,
            reflection_prompt=self._optional_string(extensions.get("reflection_prompt")),
            source_adaptation={
                str(key): str(value)
                for key, value in source_adaptation.items()
                if isinstance(value, (str, int, float, bool))
            },
            status=self._required_string(document, "status"),
        )

    def _source(self, course_id: CourseId, document: dict[str, Any]) -> SourceDetail:
        rag = self._mapping(document.get("rag"), "rag")
        return SourceDetail(
            id=self._required_string(document, "id"),
            title=self._required_string(document, "title"),
            course=course_id,
            source_type=self._required_string(document, "source_type"),
            citation=dict(self._mapping(document.get("citation"), "citation")),
            rights=dict(self._mapping(document.get("rights"), "rights")),
            data_classification=self._required_string(document, "data_classification"),
            rag_eligible=rag.get("eligible") is True,
            status=self._required_string(document, "status"),
        )

    def _rag_text(self, course_id: CourseId, content: dict[str, Any]) -> str:
        mode = content.get("mode")
        if mode == "inline":
            return self._required_string(content, "text")
        if mode == "file":
            relative = self._required_string(content, "path")
            candidate = (self._course_dir(course_id) / "sources" / relative).resolve()
            sources_root = (self._course_dir(course_id) / "sources").resolve()
            if not candidate.is_relative_to(sources_root) or candidate.suffix not in {
                ".md",
                ".txt",
            }:
                raise CourseContentError("rag source path must stay inside sources")
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError as exc:
                raise CourseContentError(f"cannot read RAG source body: {exc}") from exc
        raise CourseContentError("eligible RAG source must provide inline or file content")

    @staticmethod
    def _student_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
        """Return only information safe to show before a submission."""

        public = {
            key: value
            for key, value in evaluation.items()
            if key not in {"accepted_answers", "reference_answer"}
        }
        tests = evaluation.get("tests")
        if isinstance(tests, list):
            public["tests"] = [
                dict(test)
                for test in tests
                if isinstance(test, dict) and test.get("visibility") == "public"
            ]
        return public

    def _load_named_record(
        self, course_id: CourseId, directory: str, record_id: str
    ) -> dict[str, Any]:
        path = self._record_path(course_id, directory, record_id)
        if not path.is_file():
            raise CourseRecordNotFoundError(
                f"{directory} record not found in course {course_id}: {record_id}"
            )
        return self._load_path(path)

    def _record_path(self, course_id: CourseId, directory: str, record_id: str) -> Path:
        if not record_id or any(character in record_id for character in ("/", "\\", "..")):
            raise CourseRecordNotFoundError("record id contains invalid path characters")
        return self._course_dir(course_id) / directory / f"{record_id}.yaml"

    def _record_paths(self, course_id: CourseId, directory: str) -> tuple[Path, ...]:
        path = self._course_dir(course_id) / directory
        if not path.is_dir():
            return ()
        return tuple(sorted(path.glob("*.yaml")))

    def _load_record(self, course_id: CourseId, name: str) -> dict[str, Any]:
        path = self._course_dir(course_id) / name
        if not path.is_file():
            raise CourseRecordNotFoundError(f"course record not found: {course_id}/{name}")
        return self._load_path(path)

    def _course_dir(self, course_id: CourseId) -> Path:
        if course_id not in COURSE_IDS:
            raise CourseRecordNotFoundError(f"unsupported course: {course_id}")
        return self._root / course_id

    @staticmethod
    def _load_path(path: Path) -> dict[str, Any]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise CourseContentError(f"cannot read {path.name}: {exc}") from exc
        if not isinstance(value, dict):
            raise CourseContentError(f"{path.name} must contain a mapping")
        return cast(dict[str, Any], value)

    @staticmethod
    def _mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise CourseContentError(f"{label} must be a mapping")
        return cast(dict[str, Any], value)

    @staticmethod
    def _optional_mapping(value: object) -> dict[str, Any]:
        return cast(dict[str, Any], value) if isinstance(value, dict) else {}

    @staticmethod
    def _required_string(value: dict[str, Any], key: str) -> str:
        result = value.get(key)
        if not isinstance(result, str) or not result.strip():
            raise CourseContentError(f"{key} must be a non-empty string")
        return result

    @staticmethod
    def _required_int(value: dict[str, Any], key: str) -> int:
        result = value.get(key)
        if isinstance(result, bool) or not isinstance(result, int):
            raise CourseContentError(f"{key} must be an integer")
        return result

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) and value.strip() else None
