"""External model-provider boundary."""

from app.modules.model_adapters.errors import (
    ModelConfigurationError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUpstreamError,
)
from app.modules.model_adapters.factory import (
    build_model_adapter,
    build_python_tutor_model_adapter,
    build_tuoling_scenario_adapter,
)
from app.modules.model_adapters.limited import ConcurrencyLimitedModelAdapter
from app.modules.model_adapters.mock import MockAdapter
from app.modules.model_adapters.ports import ChatMessage, ModelAdapter, ModelResponse
from app.modules.model_adapters.tuoling import (
    TuolingScenarioAdapter,
    TuolingScenarioRequest,
    TuolingScenarioResponse,
)
from app.modules.model_adapters.xfyun import XfyunSparkAdapter
from app.modules.model_adapters.xfyun_maas import XfyunMaaSAdapter

__all__ = [
    "ChatMessage",
    "ConcurrencyLimitedModelAdapter",
    "MockAdapter",
    "ModelAdapter",
    "ModelConfigurationError",
    "ModelError",
    "ModelRateLimitError",
    "ModelResponse",
    "ModelTimeoutError",
    "ModelUpstreamError",
    "XfyunSparkAdapter",
    "XfyunMaaSAdapter",
    "TuolingScenarioAdapter",
    "TuolingScenarioRequest",
    "TuolingScenarioResponse",
    "build_model_adapter",
    "build_python_tutor_model_adapter",
    "build_tuoling_scenario_adapter",
]
