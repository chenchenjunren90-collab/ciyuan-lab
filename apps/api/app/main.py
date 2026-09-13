import hmac
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app import __version__
from app.api.router import router as api_router
from app.api.schemas import HealthResponse
from app.core.config import Settings, get_settings
from app.modules.model_adapters.factory import describe_model_route

logger = logging.getLogger(__name__)

# Health endpoints stay open so container/lb health checks never need the code.
_PUBLIC_PATHS = frozenset({"/health", "/api/v1/health"})
_ACCESS_CODE_HEADER = "X-Access-Code"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Reserve one lifecycle boundary for shared database/model clients."""

    yield


def _warn_unready_model_route(settings: Settings) -> None:
    """Fail loud at startup when the active model route would silently degrade."""
    ready, description = describe_model_route(settings)
    if ready:
        logger.info("model route ready: %s", description)
        return
    logger.warning("model route NOT ready: %s", description)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    access_code = settings.access_code.get_secret_value().strip()

    @application.middleware("http")
    async def access_code_gate(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # CORS preflight must never be challenged: the browser cannot attach
        # custom headers to an OPTIONS request.
        if access_code and request.method != "OPTIONS":
            path = request.url.path
            if path not in _PUBLIC_PATHS:
                provided = request.headers.get(_ACCESS_CODE_HEADER, "")
                if not hmac.compare_digest(provided, access_code):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "access code required"},
                        headers={"Access-Control-Allow-Headers": _ACCESS_CODE_HEADER},
                    )
        return await call_next(request)

    application.include_router(api_router)

    if settings.app_env != "test":
        _warn_unready_model_route(settings)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def root_health() -> HealthResponse:
        return HealthResponse(status="ok", service=settings.app_name, version=__version__)

    if access_code:
        logger.info("ACCESS_CODE gate enabled for all non-health routes")
    return application


app = create_app()
