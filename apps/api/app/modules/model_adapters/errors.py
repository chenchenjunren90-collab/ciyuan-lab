"""Unified error structure for model adapters.

All adapters surface failures through this hierarchy so callers
(orchestration, API layer) can map them to one stable error contract.
"""

from __future__ import annotations


class ModelError(Exception):
    """Base error raised by model adapters."""

    code: str = "MODEL_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def as_dict(self) -> dict[str, str]:
        """Stable machine-readable representation for API responses."""
        return {"code": self.code, "message": self.message}


class ModelConfigurationError(ModelError):
    """Missing or invalid provider configuration."""

    code = "MODEL_CONFIGURATION_ERROR"


class ModelTimeoutError(ModelError):
    """Upstream call exceeded the configured timeout."""

    code = "MODEL_TIMEOUT"


class ModelRateLimitError(ModelError):
    """Upstream reported rate limiting (HTTP 429)."""

    code = "MODEL_RATE_LIMITED"


class ModelUpstreamError(ModelError):
    """Upstream returned an unexpected status, network error or invalid payload."""

    code = "MODEL_UPSTREAM_ERROR"
