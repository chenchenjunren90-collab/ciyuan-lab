"""Authorized post-course scenario context endpoint."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_scenario_context_service
from app.modules.course_content import CourseRecordNotFoundError
from app.modules.course_content.models import CourseId
from app.modules.scenarios import ScenarioContext, ScenarioUnavailableError

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
