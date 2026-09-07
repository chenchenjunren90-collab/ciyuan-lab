"""Build the active model adapter from runtime settings."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.model_adapters.deepseek import DeepSeekAdapter
from app.modules.model_adapters.errors import ModelConfigurationError
from app.modules.model_adapters.mock import MockAdapter
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.model_adapters.tuoling import TuolingScenarioAdapter
from app.modules.model_adapters.xfyun import XfyunSparkAdapter
from app.modules.model_adapters.xfyun_maas import XfyunMaaSAdapter
from app.modules.model_adapters.xfyun_maas_reranker import DocumentReranker, XfyunMaaSReranker


def build_model_adapter(settings: Settings) -> ModelAdapter:
    """Return the adapter for the active ``MODEL_PROVIDER`` route.

    ``xfyun_maas`` (default) keeps the hosted MaaS route with the legacy Spark
    fallback chain. ``deepseek`` uses the official DeepSeek OpenAI-compatible
    API. ``xfyun_spark`` forces the legacy Spark route. An unconfigured active
    route falls back to Mock when allowed, otherwise raises.
    """
    if settings.model_provider == "deepseek":
        return _build_deepseek_adapter(settings)

    if settings.model_provider == "xfyun_spark":
        return _build_spark_adapter(settings)

    maas_api_key = settings.xfyun_maas_api_key.get_secret_value().strip()
    if maas_api_key:
        return XfyunMaaSAdapter(
            base_url=settings.xfyun_maas_base_url,
            api_key=maas_api_key,
            model=settings.xfyun_maas_model,
            timeout_seconds=settings.xfyun_maas_timeout_seconds,
            max_retries=settings.xfyun_maas_max_retries,
        )
    return _build_spark_adapter(settings)


def _build_deepseek_adapter(settings: Settings) -> ModelAdapter:
    api_key = settings.deepseek_api_key.get_secret_value().strip()
    if api_key:
        return DeepSeekAdapter(
            base_url=settings.deepseek_base_url,
            api_key=api_key,
            model=settings.deepseek_model,
            timeout_seconds=settings.deepseek_timeout_seconds,
            max_retries=settings.deepseek_max_retries,
        )
    if settings.xfyun_maas_mock_fallback and settings.xfyun_spark_mock_fallback:
        return MockAdapter()
    raise ModelConfigurationError("DEEPSEEK_API_KEY is not configured")


def _build_spark_adapter(settings: Settings) -> ModelAdapter:
    api_password = settings.xfyun_spark_api_password.get_secret_value().strip()
    api_key = settings.xfyun_spark_api_key.get_secret_value().strip()
    api_secret = settings.xfyun_spark_api_secret.get_secret_value().strip()

    if api_password or (api_key and api_secret):
        return XfyunSparkAdapter(
            base_url=settings.xfyun_spark_base_url,
            api_password=api_password,
            api_key=api_key,
            api_secret=api_secret,
            model=settings.xfyun_spark_model,
            timeout_seconds=settings.xfyun_spark_timeout_seconds,
            max_retries=settings.xfyun_spark_max_retries,
        )

    if settings.xfyun_maas_mock_fallback and settings.xfyun_spark_mock_fallback:
        return MockAdapter()

    raise ModelConfigurationError("Model adapter is not configured and Mock fallback is disabled")


def describe_model_route(settings: Settings) -> tuple[bool, str]:
    """Validate the active model route without making any network call.

    Returns ``(ready, description)``. A route is ready when it resolves to a
    real provider adapter; a Mock fallback or a configuration error means the
    deployment would silently degrade every model-backed flow.
    """
    try:
        adapter = build_model_adapter(settings)
    except ModelConfigurationError as exc:
        return False, str(exc)
    if isinstance(adapter, MockAdapter):
        return False, f"MODEL_PROVIDER={settings.model_provider} resolves to MockAdapter"
    return True, f"MODEL_PROVIDER={settings.model_provider} -> {type(adapter).__name__}"


def build_reranker(settings: Settings) -> DocumentReranker | None:
    """Use MaaS relevance scoring only when its published service is configured."""
    if not settings.xfyun_maas_reranker_enabled:
        return None
    api_key = settings.xfyun_maas_reranker_api_key.get_secret_value().strip()
    if not api_key:
        api_key = settings.xfyun_maas_api_key.get_secret_value().strip()
    return XfyunMaaSReranker(
        base_url=settings.xfyun_maas_base_url,
        api_key=api_key,
        model=settings.xfyun_maas_reranker_model,
        candidate_limit=settings.xfyun_maas_reranker_candidate_limit,
        timeout_seconds=settings.xfyun_maas_reranker_timeout_seconds,
        max_retries=settings.xfyun_maas_reranker_max_retries,
    )


def build_tuoling_scenario_adapter(
    settings: Settings,
) -> TuolingScenarioAdapter | None:
    """Build the restricted scenario adapter only when explicitly enabled."""

    if not settings.tuoling_enabled:
        return None
    return TuolingScenarioAdapter(
        base_url=settings.tuoling_base_url,
        api_key=settings.tuoling_api_key.get_secret_value(),
        context_path=settings.tuoling_context_path,
        timeout_seconds=settings.tuoling_timeout_seconds,
        max_retries=settings.tuoling_max_retries,
    )
