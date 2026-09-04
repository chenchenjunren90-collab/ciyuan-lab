"""Student-safe course catalog and learning-content endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import get_course_repository
from app.modules.course_content import (
    ActivityDetail,
    ActivitySummary,
    CourseRecordNotFoundError,
    CourseSummary,
    KnowledgePointDetail,
    KnowledgePointList,
    SourceDetail,
)
from app.modules.course_content.models import CourseId, LearningStage

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseSummary])
async def list_courses() -> list[CourseSummary]:
    return list(get_course_repository().list_courses())


@router.get("/{course_id}/knowledge-points", response_model=KnowledgePointList)
async def list_knowledge_points(course_id: CourseId) -> KnowledgePointList:
    return KnowledgePointList(
        course_id=course_id,
        items=list(get_course_repository().list_knowledge_points(course_id)),
    )


@router.get(
    "/{course_id}/knowledge-points/{knowledge_point_id}",
    response_model=KnowledgePointDetail,
)
async def get_knowledge_point(course_id: CourseId, knowledge_point_id: str) -> KnowledgePointDetail:
    try:
        return get_course_repository().get_knowledge_point(course_id, knowledge_point_id)
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{course_id}/activities", response_model=list[ActivitySummary])
async def list_activities(
    course_id: CourseId,
    knowledge_point_id: str | None = Query(default=None),
    learning_stage: LearningStage | None = None,
) -> list[ActivitySummary]:
    activities = get_course_repository().list_activities(course_id)
    if knowledge_point_id is not None:
        activities = tuple(
            activity for activity in activities if knowledge_point_id in activity.concept_ids
        )
    if learning_stage is not None:
        activities = tuple(
            activity for activity in activities if activity.learning_stage == learning_stage
        )
    return list(activities)


@router.get("/{course_id}/activities/{activity_id}", response_model=ActivityDetail)
async def get_activity(course_id: CourseId, activity_id: str) -> ActivityDetail:
    try:
        return get_course_repository().get_activity(course_id, activity_id)
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{course_id}/sources", response_model=list[SourceDetail])
async def list_sources(course_id: CourseId) -> list[SourceDetail]:
    return list(get_course_repository().list_sources(course_id))


@router.get("/{course_id}/sources/{source_id}", response_model=SourceDetail)
async def get_source(course_id: CourseId, source_id: str) -> SourceDetail:
    try:
        return get_course_repository().get_source(course_id, source_id)
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
