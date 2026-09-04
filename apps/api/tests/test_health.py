import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


async def request(path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_root_health() -> None:
    response = asyncio.run(request("/health"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "词元研究所",
        "version": "0.1.0",
    }


def test_versioned_health() -> None:
    response = asyncio.run(request("/api/v1/health"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_capabilities_describe_mvp_runtime_switches() -> None:
    response = asyncio.run(request("/api/v1/capabilities"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mvp"
    assert payload["code_execution_enabled"] is False
    assert payload["tuoling_enabled"] is False
    assert set(payload["modules"]) == {
        "orchestration",
        "rag",
        "learner_profile",
        "practice",
        "model_adapters",
    }
