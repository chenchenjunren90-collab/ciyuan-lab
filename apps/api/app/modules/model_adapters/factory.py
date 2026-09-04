"""Build the active model adapter from runtime settings."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.model_adapters.errors import ModelConfigurationError
from app.modules.model_adapters.mock import MockAdapter
from app.modules.model_adapters.ports import ModelAdapter
from app.modules.model_adapters.tuoling import TuolingScenarioAdapter
from app.modules.model_adapters.xfyun import XfyunSparkAdapter
from app.modules.model_adapters.xfyun_maas import XfyunMaaSAdapter


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


def build_python_tutor_model_adapter(settings: Settings) -> ModelAdapter:
    """Build the explicitly enabled Python LoRA route, or reuse the general model.

    The training model is intentionally inactive until an operator enables it
    and both its served model ID and the MaaS resource ID are present. This
    avoids silently sending classroom traffic to an unfinished or regressing
    model merely because its deployment identifiers exist locally.
    """

    if not settings.xfyun_maas_python_tutor_enabled:
        return build_model_adapter(settings)
    model = settings.xfyun_maas_python_tutor_model.strip()
    lora_id = settings.xfyun_maas_python_tutor_lora_id.strip()
    if not model and not lora_id:
        return build_model_adapter(settings)
    if not model or not lora_id:
        raise ModelConfigurationError(
            "XFYUN_MAAS_PYTHON_TUTOR_MODEL and XFYUN_MAAS_PYTHON_TUTOR_LORA_ID "
            "must be configured together"
        )
    api_key = settings.xfyun_maas_python_tutor_api_key.get_secret_value().strip()
    if not api_key:
        api_key = settings.xfyun_maas_api_key.get_secret_value().strip()
    if not api_key:
        raise ModelConfigurationError(
            "XFYUN_MAAS_PYTHON_TUTOR_API_KEY or XFYUN_MAAS_API_KEY is required "
            "for the Python tutor LoRA route"
        )
    return XfyunMaaSAdapter(
        base_url=settings.xfyun_maas_base_url,
        api_key=api_key,
        model=model,
        lora_id=lora_id,
        timeout_seconds=settings.xfyun_maas_timeout_seconds,
        max_retries=settings.xfyun_maas_max_retries,
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
