"""Authorized post-course scenario context endpoint."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_scenario_context_service, get_scenario_project_generator
from app.modules.course_content import CourseRecordNotFoundError
from app.modules.course_content.models import CourseId
from app.modules.scenarios import (
    GeneratedScenarioProject,
    ScenarioContext,
    ScenarioProjectNeed,
    ScenarioUnavailableError,
)

router = APIRouter(prefix="/courses", tags=["scenarios"])


@router.get(
    "/{course_id}/projects/{project_id}/scenario",
    response_model=ScenarioContext,
)
async def get_project_scenario(course_id: CourseId, project_id: str) -> ScenarioContext:
    try:
        return await get_scenario_context_service().get_context(course_id, project_id)
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ScenarioUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{course_id}/scenario-projects/generate",
    response_model=GeneratedScenarioProject,
)
async def generate_scenario_project(
    course_id: CourseId,
    request: ScenarioProjectNeed,
) -> GeneratedScenarioProject:
    if request.course_id != course_id:
        raise HTTPException(status_code=422, detail="course_id must match the request path")
    try:
        return await get_scenario_project_generator().generate(request)
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
