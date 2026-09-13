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
    provider = settings.model_provider

    if provider == "deepseek":
        ready = bool(settings.deepseek_api_key.get_secret_value().strip())
        model = settings.deepseek_model
    elif provider == "xfyun_spark":
        password_ready = bool(settings.xfyun_spark_api_password.get_secret_value().strip())
        pair_ready = bool(
            settings.xfyun_spark_api_key.get_secret_value().strip()
            and settings.xfyun_spark_api_secret.get_secret_value().strip()
        )
        ready = password_ready or pair_ready
        model = settings.xfyun_spark_model
    else:  # xfyun_maas (default)
        ready = bool(settings.xfyun_maas_api_key.get_secret_value().strip())
        model = settings.xfyun_maas_model

    print(f"model_provider_mode={provider}")
    print(f"model_configured={ready}")
    print(f"model_id={model}")
    if args.live:
        asyncio.run(_live_check(settings))
    else:
        print("live_requests=skipped (pass --live only after confirming quota and authorization)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
