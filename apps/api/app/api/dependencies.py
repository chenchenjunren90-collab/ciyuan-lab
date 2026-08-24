"""Lazy dependencies; importing the app never opens a database connection."""

from functools import lru_cache

from app.core.config import get_settings
from app.core.database import create_database_engine, create_session_factory
from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.repository import LearningRepository
from app.modules.learning_flow import LearningFlowService
from app.modules.model_adapters.factory import build_model_adapter
from app.modules.model_adapters.ports import ModelAdapter


@lru_cache
def get_course_repository() -> CoursePackRepository:
    return CoursePackRepository()


@lru_cache
def get_learning_repository() -> LearningRepository:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    return LearningRepository(create_session_factory(engine))


@lru_cache
def get_model_adapter() -> ModelAdapter:
    return build_model_adapter(get_settings())


@lru_cache
def get_learning_flow_service() -> LearningFlowService:
    return LearningFlowService(
        repository=get_learning_repository(),
        courses=get_course_repository(),
        model_adapter=get_model_adapter(),
    )
