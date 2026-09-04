"""Post-course project submission endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_project_submission_service
from app.modules.course_content import CourseId, CourseRecordNotFoundError
from app.modules.practice.projects import (
    ProjectSubmissionRequest,
    ProjectSubmissionResponse,
    ProjectSubmissionService,
)

router = APIRouter(tags=["practice"])
CourseIdQuery = Annotated[CourseId, Query()]


@router.post(
    "/projects/{project_id}/submissions",
    response_model=ProjectSubmissionResponse,
)
async def submit_project(
    project_id: str,
    request: ProjectSubmissionRequest,
    course_id: CourseIdQuery,
    service: Annotated[ProjectSubmissionService, Depends(get_project_submission_service)],
) -> ProjectSubmissionResponse:
    try:
        return service.submit(
            student_id=request.student_id,
            course_id=course_id,
            project_id=project_id,
            artifact_summary=request.artifact_summary,
            repository_url=request.repository_url,
            test_evidence=request.test_evidence,
        )
    except CourseRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
