"""Progressive hint endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_progressive_hint_service
from app.modules.course_content import CourseId, CourseRecordNotFoundError
from app.modules.practice.hints import HintRequest, HintResponse, ProgressiveHintService

router = APIRouter(tags=["practice"])
CourseIdQuery = Annotated[CourseId, Query()]


@router.post("/activities/{activity_id}/hint", response_model=HintResponse)
async def create_hint(
    activity_id: str,
    request: HintRequest,
    course_id: CourseIdQuery,
    service: Annotated[ProgressiveHintService, Depends(get_progressive_hint_service)],
) -> HintResponse:
    try:
        return service.create_hint(
            student_id=request.student_id,
            course_id=course_id,
            activity_id=activity_id,
            level=request.level,
        )
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail="activity not found") from exc
