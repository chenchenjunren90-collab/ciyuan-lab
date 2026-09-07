"""ACCESS_CODE gate behavior for shared deployments."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import app, create_app


def gated_client(code: str = "site-secret") -> TestClient:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        access_code=SecretStr(code),
        xfyun_maas_api_key=SecretStr(""),
        xfyun_spark_api_password=SecretStr(""),
        xfyun_spark_api_key=SecretStr(""),
        xfyun_spark_api_secret=SecretStr(""),
    )
    return TestClient(create_app(settings))


def test_access_code_requires_header_when_enabled() -> None:
    response = gated_client().get("/api/v1/courses")

    assert response.status_code == 403
    assert response.json()["detail"] == "access code required"


def test_access_code_rejects_wrong_code() -> None:
    response = gated_client().get("/api/v1/courses", headers={"X-Access-Code": "wrong"})

    assert response.status_code == 403


def test_access_code_accepts_correct_code() -> None:
    response = gated_client().get("/api/v1/courses", headers={"X-Access-Code": "site-secret"})

    assert response.status_code == 200


def test_health_endpoints_bypass_access_code() -> None:
    client = gated_client()

    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_cors_preflight_bypasses_access_code() -> None:
    client = gated_client()
    response = client.options(
        "/api/v1/courses",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Access-Code",
        },
    )

    assert response.status_code != 403


def test_access_code_disabled_by_default() -> None:
    async def scenario() -> int:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return (await client.get("/api/v1/courses")).status_code

    assert asyncio.run(scenario()) == 200
