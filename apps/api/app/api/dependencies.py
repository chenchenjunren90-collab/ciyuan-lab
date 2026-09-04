"""Lazy dependencies; importing the app never opens a database connection."""

from functools import lru_cache

from app.core.config import get_settings
from app.core.database import create_database_engine, create_session_factory
from app.modules.adaptive_practice import AdaptiveProblemService
from app.modules.course_content import CoursePackRepository
from app.modules.learner_profile.repository import LearningRepository
from app.modules.learning_flow import LearningFlowService
from app.modules.learning_flow.diagnostics import DiagnosticService
from app.modules.model_adapters.factory import (
    build_model_adapter,
    build_python_tutor_model_adapter,
)
from app.modules.model_adapters.limited import ConcurrencyLimitedModelAdapter
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.orchestration import CourseTutor, QualitySupervisor
from app.modules.orchestration.classroom import (
    ClassroomDialogueService,
    ClassroomLessonService,
)
from app.modules.practice import (
    DeterministicCodeVerifier,
    DisabledSandboxRunner,
    DockerSandboxRunner,
    PracticeSubmissionService,
)
from app.modules.practice.hints import ProgressiveHintService
from app.modules.practice.projects import ProjectSubmissionService
from app.modules.rag.pgvector_retriever import PgVectorKnowledgeRetriever
from app.modules.rag.ports import KnowledgeRetriever
from app.modules.rag.python_docs import PythonOfficialDocsRetriever
from app.modules.rag.retriever import LexicalKnowledgeRetriever
from app.modules.rag.service import RagQaService
from app.modules.scenarios import ScenarioContextService, ScenarioProjectGenerator


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
    settings = get_settings()
    return ConcurrencyLimitedModelAdapter(
        build_model_adapter(settings),
        max_concurrency=settings.model_max_concurrency,
        queue_timeout_seconds=settings.model_queue_timeout_seconds,
    )


@lru_cache
def get_python_tutor_model_adapter() -> ModelAdapter:
    """Dedicated route for the reviewed Python SFT/LoRA model when enabled."""

    settings = get_settings()
    return ConcurrencyLimitedModelAdapter(
        build_python_tutor_model_adapter(settings),
        max_concurrency=settings.model_max_concurrency,
        queue_timeout_seconds=settings.model_queue_timeout_seconds,
    )


@lru_cache
def get_rag_qa_service() -> RagQaService:
    settings = get_settings()
    retriever: KnowledgeRetriever
    if settings.rag_backend == "pgvector":
        retriever = PgVectorKnowledgeRetriever(
            create_database_engine(settings.database_url),
            min_score=settings.rag_min_score,
            vector_weight=settings.rag_vector_weight,
        )
    else:
        retriever = LexicalKnowledgeRetriever.from_repository(get_course_repository())
    return RagQaService(
        retriever,
        CourseTutor(
            get_model_adapter(),
            python_model_adapter=get_python_tutor_model_adapter(),
        ),
        QualitySupervisor(get_model_adapter()),
        top_k=settings.rag_top_k,
    )


@lru_cache
def get_classroom_lesson_service() -> ClassroomLessonService:
    return ClassroomLessonService(
        get_course_repository(),
        learning_context=get_learning_flow_service(),
    )


@lru_cache
def get_classroom_dialogue_service() -> ClassroomDialogueService:
    settings = get_settings()
    retriever: KnowledgeRetriever
    if settings.rag_backend == "pgvector":
        retriever = PgVectorKnowledgeRetriever(
            create_database_engine(settings.database_url),
            min_score=settings.rag_min_score,
            vector_weight=settings.rag_vector_weight,
        )
    else:
        retriever = LexicalKnowledgeRetriever.from_repository(get_course_repository())
    return ClassroomDialogueService(
        courses=get_course_repository(),
        retriever=retriever,
        online_retriever=PythonOfficialDocsRetriever(
            enabled=settings.python_online_search_enabled and settings.app_env != "test",
            base_url=settings.python_docs_base_url,
            timeout_seconds=settings.python_online_search_timeout_seconds,
            max_pages=settings.python_online_search_max_pages,
        ),
        tutor=CourseTutor(
            get_model_adapter(),
            python_model_adapter=get_python_tutor_model_adapter(),
        ),
        supervisor=QualitySupervisor(get_model_adapter()),
        top_k=settings.rag_top_k,
    )


@lru_cache
def get_learning_flow_service() -> LearningFlowService:
    return LearningFlowService(
        repository=get_learning_repository(),
        courses=get_course_repository(),
        model_adapter=get_model_adapter(),
    )


@lru_cache
def get_diagnostic_service() -> DiagnosticService:
    return DiagnosticService(
        courses=get_course_repository(),
        learning_flow=get_learning_flow_service(),
    )


@lru_cache
def get_practice_submission_service() -> PracticeSubmissionService:
    settings = get_settings()
    runner = (
        DockerSandboxRunner(
            work_root=settings.sandbox_work_root or None,
            python_image=settings.sandbox_python_image,
            c_image=settings.sandbox_c_image,
        )
        if settings.code_execution_enabled
        else DisabledSandboxRunner()
    )
    return PracticeSubmissionService(
        repository=get_learning_repository(),
        courses=get_course_repository(),
        verifier=DeterministicCodeVerifier(runner),
        learning_flow=get_learning_flow_service(),
    )


@lru_cache
def get_adaptive_problem_service() -> AdaptiveProblemService:
    settings = get_settings()
    runner = (
        DockerSandboxRunner(
            work_root=settings.sandbox_work_root or None,
            python_image=settings.sandbox_python_image,
            c_image=settings.sandbox_c_image,
        )
        if settings.code_execution_enabled
        else DisabledSandboxRunner()
    )
    return AdaptiveProblemService(
        repository=get_learning_repository(),
        verifier=DeterministicCodeVerifier(runner),
    )


@lru_cache
def get_progressive_hint_service() -> ProgressiveHintService:
    return ProgressiveHintService(
        courses=get_course_repository(), repository=get_learning_repository()
    )


@lru_cache
def get_project_submission_service() -> ProjectSubmissionService:
    return ProjectSubmissionService(
        courses=get_course_repository(), repository=get_learning_repository()
    )


@lru_cache
def get_scenario_context_service() -> ScenarioContextService:
    return ScenarioContextService(
        courses=get_course_repository(),
        tuoling=None,
    )


@lru_cache
def get_scenario_project_generator() -> ScenarioProjectGenerator:
    return ScenarioProjectGenerator(
        courses=get_course_repository(),
        model=get_model_adapter(),
    )
