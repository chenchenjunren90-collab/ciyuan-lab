"""Immersive classroom endpoints for the Python learning loop."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import (
    get_classroom_dialogue_service,
    get_classroom_lesson_service,
)
from app.modules.orchestration.classroom import (
    ClassroomCheckpointRequest,
    ClassroomCheckpointResult,
    ClassroomDialogueRequest,
    ClassroomDialogueResponse,
    ClassroomDialogueService,
    ClassroomLesson,
    ClassroomLessonService,
    ClassroomPreference,
    ClassroomSelfProfileRequest,
    ClassroomSelfProfileResponse,
    SelfProfileLevel,
)

router = APIRouter(prefix="/classroom", tags=["classroom"])


@router.get("/sessions/next", response_model=ClassroomLesson)
async def get_next_classroom_session(
    service: Annotated[ClassroomLessonService, Depends(get_classroom_lesson_service)],
    student_id: Annotated[str, Query(min_length=1, max_length=128)],
    daily_minutes: Annotated[int, Query(ge=20, le=120)] = 30,
    preferred_mode: ClassroomPreference = "step_by_step",
    self_profile_level: SelfProfileLevel | None = None,
) -> ClassroomLesson:
    try:
        return await service.next_session(
            student_id=student_id,
            daily_minutes=daily_minutes,
            preferred_mode=preferred_mode,
            self_profile_level=self_profile_level,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/lessons/{lesson_id}", response_model=ClassroomLesson)
async def get_classroom_lesson(
    lesson_id: str,
    service: Annotated[ClassroomLessonService, Depends(get_classroom_lesson_service)],
) -> ClassroomLesson:
    try:
        return service.get_lesson(lesson_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/checkpoints", response_model=ClassroomCheckpointResult)
async def evaluate_classroom_checkpoint(
    request: ClassroomCheckpointRequest,
    service: Annotated[ClassroomLessonService, Depends(get_classroom_lesson_service)],
) -> ClassroomCheckpointResult:
    try:
        return service.evaluate_checkpoint(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dialogue", response_model=ClassroomDialogueResponse)
async def classroom_dialogue(
    request: ClassroomDialogueRequest,
    service: Annotated[ClassroomDialogueService, Depends(get_classroom_dialogue_service)],
) -> ClassroomDialogueResponse:
    try:
        return await service.answer(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/self-profile", response_model=ClassroomSelfProfileResponse)
async def assess_classroom_self_profile(
    request: ClassroomSelfProfileRequest,
    service: Annotated[ClassroomDialogueService, Depends(get_classroom_dialogue_service)],
) -> ClassroomSelfProfileResponse:
    try:
        return await service.assess_self_profile(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
