"""Restricted Tuoling adapter for post-course finance practice context only."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.modules.model_adapters.errors import (
    ModelConfigurationError,
    ModelTimeoutError,
    ModelUpstreamError,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class TuolingScenarioRequest:
    project_id: str
    course_id: str
    scenario_scope: str
    data_classification: str
    computer_science_objectives: Sequence[str]
    business_context_objectives: Sequence[str]


@dataclass(frozen=True, slots=True)
class TuolingScenarioResponse:
    context: str
    constraints: tuple[str, ...]
    source_refs: tuple[str, ...]


class TuolingScenarioAdapter:
    """Call an authorized Tuoling scenario endpoint with a minimal payload.

    The adapter intentionally sends neither learner identity nor submitted code.
    Its endpoint contract is isolated here so it can be aligned with the school's
    final API documentation without changing course, orchestration or UI code.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        context_path: str = "/v1/scenarios/context",
        timeout_seconds: float = 15.0,
        max_retries: int = 1,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        parsed_url = urlsplit(normalized_base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ModelConfigurationError("TUOLING_BASE_URL must be an HTTP(S) URL")
        if not api_key.strip():
            raise ModelConfigurationError("TUOLING_API_KEY is not configured")
        if not context_path.startswith("/") or ".." in context_path:
            raise ModelConfigurationError("TUOLING_CONTEXT_PATH must be an absolute path")
        if timeout_seconds <= 0:
            raise ModelConfigurationError("timeout_seconds must be greater than zero")
        if max_retries < 0:
            raise ModelConfigurationError("max_retries must not be negative")

        self._base_url = normalized_base_url
        self._api_key = api_key.strip()
        self._context_path = context_path
        self._timeout_seconds = timeout_seconds
        self._max_retries = int(max_retries)
        self._client = client

    async def fetch_context(self, request: TuolingScenarioRequest) -> TuolingScenarioResponse:
        if request.scenario_scope != "post_course_finance_practice":
            raise ModelConfigurationError("Tuoling is restricted to finance practice")
        if request.data_classification not in {
            "public",
            "synthetic",
            "authorized_desensitized",
        }:
            raise ModelConfigurationError("Tuoling request data is not authorized")

        payload = {
            "project_id": request.project_id,
            "course_id": request.course_id,
            "scenario_scope": request.scenario_scope,
            "data_classification": request.data_classification,
            "computer_science_objectives": list(request.computer_science_objectives),
            "business_context_objectives": list(request.business_context_objectives),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}{self._context_path}"

        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._post(url, headers=headers, payload=payload)
            except httpx.TimeoutException:
                if attempt == attempts:
                    raise ModelTimeoutError("Tuoling request timed out") from None
                logger.warning("tuoling request timed out (attempt %d/%d)", attempt, attempts)
                continue
            except httpx.RequestError:
                if attempt == attempts:
                    raise ModelUpstreamError("Tuoling network request failed") from None
                logger.warning("tuoling network request failed (attempt %d/%d)", attempt, attempts)
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES:
                if attempt == attempts:
                    raise ModelUpstreamError(f"Tuoling returned HTTP {response.status_code}")
                continue
            if response.status_code != 200:
                raise ModelUpstreamError(f"Tuoling returned HTTP {response.status_code}")
            return self._parse_response(response)

        raise ModelUpstreamError("Tuoling request failed")  # pragma: no cover

    async def _post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(url, headers=headers, json=payload)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(url, headers=headers, json=payload)

    @staticmethod
    def _parse_response(response: httpx.Response) -> TuolingScenarioResponse:
        try:
            body = response.json()
        except ValueError as exc:
            raise ModelUpstreamError("Tuoling returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ModelUpstreamError("Tuoling returned unexpected payload shape")
        data = body.get("data", body)
        if not isinstance(data, dict):
            raise ModelUpstreamError("Tuoling response data must be an object")
        context = data.get("context")
        if not isinstance(context, str) or not context.strip():
            raise ModelUpstreamError("Tuoling response is missing scenario context")
        if len(context) > 8_000:
            raise ModelUpstreamError("Tuoling scenario context exceeds the size limit")
        constraints = TuolingScenarioAdapter._string_tuple(data.get("constraints"))
        source_refs = TuolingScenarioAdapter._string_tuple(data.get("source_refs"))
        if len(constraints) > 20 or any(len(item) > 500 for item in constraints):
            raise ModelUpstreamError("Tuoling constraints exceed the size limit")
        if len(source_refs) > 50 or any(len(item) > 120 for item in source_refs):
            raise ModelUpstreamError("Tuoling source references exceed the size limit")
        return TuolingScenarioResponse(
            context=context.strip(),
            constraints=constraints,
            source_refs=source_refs,
        )

    @staticmethod
    def _string_tuple(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
