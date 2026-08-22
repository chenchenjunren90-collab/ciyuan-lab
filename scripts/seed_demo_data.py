"""Seed deterministic, non-personal demo data after applying migrations."""

from __future__ import annotations

import argparse
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import yaml  # type: ignore[import-untyped]
from alembic import command
from alembic.config import Config

from app.core.config import Settings
from app.core.database import create_database_engine, create_session_factory
from app.modules.learner_profile import (
    CourseVersion,
    LearnerProfileService,
    LearningEvent,
    LearningRepository,
)
from app.modules.learner_profile.records import CourseId

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_STUDENT_ID = "00000000-0000-4000-8000-000000000001"
COURSE_IDS: tuple[CourseId, ...] = ("c", "python", "data_structures")


def _load_course(course_id: CourseId) -> CourseVersion:
    manifest_path = REPO_ROOT / "course_packs" / course_id / "manifest.yaml"
    manifest_bytes = manifest_path.read_bytes()
    manifest = cast(dict[str, Any], yaml.safe_load(manifest_bytes))
    course = cast(dict[str, Any], manifest["course"])
    return CourseVersion(
        course_id=course_id,
        version=str(manifest["schema_version"]),
        title=str(course["title"]),
        status=str(course["status"]),
        manifest_hash=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def seed(database_url: str) -> None:
    alembic_config = Config(str(REPO_ROOT / "alembic.ini"))
    alembic_config.attributes["database_url"] = database_url
    command.upgrade(alembic_config, "head")

    engine = create_database_engine(database_url)
    repository = LearningRepository(create_session_factory(engine))
    profile_service = LearnerProfileService(repository)
    try:
        for course_id in COURSE_IDS:
            repository.register_course_version(_load_course(course_id))

        repository.create_profile(
            student_id=DEMO_STUDENT_ID,
            course_id="python",
            course_version="0.1.0",
        )
        demo_event_id = UUID("00000000-0000-4000-8000-000000000101")
        repository.append_event(
            LearningEvent(
                event_id=demo_event_id,
                schema_version="0.1.0",
                event_type="assessment.completed",
                occurred_at=datetime(2026, 8, 22, tzinfo=UTC),
                student_id=DEMO_STUDENT_ID,
                course_id="python",
                course_version="0.1.0",
                knowledge_point_id="PY-BASE-01",
                trace_id="demo-assessment-001",
                payload={"is_correct": False, "source": "synthetic_demo"},
                evidence_summary="固定合成基线测评事件，不含真实个人信息",
            )
        )
        profile_service.process_event(demo_event_id)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=Settings().database_url)
    args = parser.parse_args()
    seed(cast(str, args.database_url))
    print(f"Seeded demo learner {DEMO_STUDENT_ID} without personal information.")


if __name__ == "__main__":
    main()
