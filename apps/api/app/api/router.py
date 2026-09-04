from fastapi import APIRouter

from app import __version__
from app.api.adaptive import router as adaptive_router
from app.api.classroom import router as classroom_router
from app.api.courses import router as courses_router
from app.api.hints import router as hints_router
from app.api.learning import router as learning_router
from app.api.projects import router as projects_router
from app.api.qa import router as qa_router
from app.api.scenarios import router as scenarios_router
from app.api.schemas import CapabilitiesResponse, HealthResponse
from app.api.submissions import router as submissions_router
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1")
router.include_router(adaptive_router)
router.include_router(classroom_router)
router.include_router(courses_router)
router.include_router(hints_router)
router.include_router(learning_router)
router.include_router(projects_router)
router.include_router(qa_router)
router.include_router(scenarios_router)
router.include_router(submissions_router)


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def api_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version=__version__)


@router.get("/capabilities", response_model=CapabilitiesResponse, tags=["system"])
async def list_capabilities() -> CapabilitiesResponse:
    settings = get_settings()
    return CapabilitiesResponse(
        status="mvp",
        code_execution_enabled=settings.code_execution_enabled,
        tuoling_enabled=settings.tuoling_enabled,
        modules=[
            "orchestration",
            "rag",
            "learner_profile",
            "practice",
            "model_adapters",
        ],
    )
