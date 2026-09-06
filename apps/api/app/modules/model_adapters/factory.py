"""Build the active model adapter from runtime settings."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.model_adapters.errors import ModelConfigurationError
from app.modules.model_adapters.mock import MockAdapter
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.model_adapters.tuoling import TuolingScenarioAdapter
from app.modules.model_adapters.xfyun import XfyunSparkAdapter
from app.modules.model_adapters.xfyun_maas import XfyunMaaSAdapter
from app.modules.model_adapters.xfyun_maas_reranker import DocumentReranker, XfyunMaaSReranker


def build_model_adapter(settings: Settings) -> ModelAdapter:
    """Return a configured adapter, falling back to Mock when allowed.

    Xfyun MaaS is preferred when its API key is configured. Legacy Spark
    credentials remain supported for older local environments. Otherwise a
    fixed Mock adapter is returned unless fallback is disabled.
    """
    maas_api_key = settings.xfyun_maas_api_key.get_secret_value().strip()
    if maas_api_key:
        return XfyunMaaSAdapter(
            base_url=settings.xfyun_maas_base_url,
            api_key=maas_api_key,
            model=settings.xfyun_maas_model,
            timeout_seconds=settings.xfyun_maas_timeout_seconds,
            max_retries=settings.xfyun_maas_max_retries,
        )

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
