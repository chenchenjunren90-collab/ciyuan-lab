"""Report model-provider readiness; make paid network calls only with --live."""

from __future__ import annotations

import argparse
import asyncio

from app.core.config import Settings
from app.modules.model_adapters.factory import build_model_adapter
from app.modules.model_adapters.ports import ChatMessage


async def _live_check(settings: Settings) -> None:
    model = build_model_adapter(settings)
    response = await model.complete(
        [ChatMessage(role="user", content='仅回复 JSON：{"status":"ok"}')]
    )
    print(f"model_live=ok provider={response.provider} model={response.model}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="perform real provider requests that may consume quota",
    )
    args = parser.parse_args()
    settings = Settings()
    maas_ready = bool(settings.xfyun_maas_api_key.get_secret_value().strip())
    password_ready = bool(settings.xfyun_spark_api_password.get_secret_value().strip())
    pair_ready = bool(
        settings.xfyun_spark_api_key.get_secret_value().strip()
        and settings.xfyun_spark_api_secret.get_secret_value().strip()
    )
    provider_mode = (
        "xfyun_maas"
        if maas_ready
        else "legacy_spark_password"
        if password_ready
        else "legacy_spark_key_secret"
        if pair_ready
        else "mock"
    )
    print(f"model_configured={maas_ready or password_ready or pair_ready}")
    print(f"model_provider_mode={provider_mode}")
    selected_model = (
        settings.xfyun_maas_model
        if maas_ready or not (password_ready or pair_ready)
        else settings.xfyun_spark_model
    )
    print(f"model_id={selected_model}")
    if args.live:
        asyncio.run(_live_check(settings))
    else:
        print("live_requests=skipped (pass --live only after confirming quota and authorization)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
