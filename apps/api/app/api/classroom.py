"""Immersive classroom endpoints for the Python learning loop."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

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
    ClassroomSelfProfileRequest,
    ClassroomSelfProfileResponse,
)

router = APIRouter(prefix="/classroom", tags=["classroom"])


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
