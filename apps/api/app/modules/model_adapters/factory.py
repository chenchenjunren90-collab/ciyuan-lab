"""Build the active model adapter from runtime settings."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.model_adapters.errors import ModelConfigurationError
from app.modules.model_adapters.mock import MockAdapter
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.model_adapters.xfyun import XfyunSparkAdapter


def build_model_adapter(settings: Settings) -> ModelAdapter:
    """Return a configured adapter, falling back to Mock when allowed.

    A real adapter is built only when both the API key and secret are set.
    Otherwise a fixed Mock adapter is returned unless fallback is disabled,
    in which case a configuration error is raised.
    """
    api_key = settings.xfyun_spark_api_key.get_secret_value().strip()
    api_secret = settings.xfyun_spark_api_secret.get_secret_value().strip()

    if api_key and api_secret:
        return XfyunSparkAdapter(
            base_url=settings.xfyun_spark_base_url,
            api_key=api_key,
            api_secret=api_secret,
            model=settings.xfyun_spark_model,
            timeout_seconds=settings.xfyun_spark_timeout_seconds,
            max_retries=settings.xfyun_spark_max_retries,
        )

    if settings.xfyun_spark_mock_fallback:
        return MockAdapter()

    raise ModelConfigurationError(
        "Model adapter is not configured and Mock fallback is disabled"
    )
