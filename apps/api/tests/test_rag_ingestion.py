from app.modules.course_content import CoursePackRepository
from app.modules.rag.ingestion import build_ingestion_plan


def test_ingestion_plan_separates_reviewed_sources_from_draft_concepts() -> None:
    plan = build_ingestion_plan(CoursePackRepository())

    source_chunks = [
        item for item in plan.candidates if item.record_type == "reviewed_source_chunk"
    ]
    concept_previews = [item for item in plan.candidates if item.record_type == "concept_preview"]
    assert len(concept_previews) == 122
    assert source_chunks
    assert all(item.eligible and item.blocked_reason is None for item in source_chunks)
    assert all(not item.eligible for item in concept_previews)
    assert {item.blocked_reason for item in concept_previews} == {"concept_not_human_reviewed"}
    assert plan.eligible_count == len(source_chunks)
    assert plan.blocked_count == 122


def test_ingestion_plan_is_deterministic_and_course_isolated() -> None:
    repository = CoursePackRepository()
    first = build_ingestion_plan(repository)
    second = build_ingestion_plan(repository)

    assert first.snapshot_hash == second.snapshot_hash
    assert first.to_json() == second.to_json()
    assert all(
        item.record_id.startswith(("C-", "SRC-C-"))
        for item in first.candidates
        if item.course_id == "c"
    )
