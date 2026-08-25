"""Report model-provider readiness; make paid network calls only with --live."""

from __future__ import annotations

import argparse
import asyncio

from app.core.config import Settings
from app.modules.course_content import CoursePackRepository
from app.modules.model_adapters.factory import (
    build_model_adapter,
    build_tuoling_scenario_adapter,
)
from app.modules.model_adapters.ports import ChatMessage
from app.modules.scenarios import ScenarioContextService


async def _live_check(settings: Settings) -> None:
    model = build_model_adapter(settings)
    response = await model.complete(
        [ChatMessage(role="user", content='仅回复 JSON：{"status":"ok"}')]
    )
    print(f"spark_live=ok provider={response.provider} model={response.model}")

    tuoling = build_tuoling_scenario_adapter(settings)
    if tuoling is None:
        print("tuoling_live=skipped reason=disabled")
        return
    courses = CoursePackRepository()
    project = next(
        activity
        for activity in courses.list_activities("python")
        if activity.type == "project" and activity.scenario_provider == "tuoling"
    )
    context = await ScenarioContextService(courses=courses, tuoling=tuoling).get_context(
        "python", project.id
    )
    print(f"tuoling_live={context.provider_status} mode={context.mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="perform real provider requests that may consume quota",
    )
    args = parser.parse_args()
    settings = Settings()
    password_ready = bool(settings.xfyun_spark_api_password.get_secret_value().strip())
    pair_ready = bool(
        settings.xfyun_spark_api_key.get_secret_value().strip()
        and settings.xfyun_spark_api_secret.get_secret_value().strip()
    )
    tuoling_ready = bool(
        settings.tuoling_enabled
        and settings.tuoling_base_url.strip()
        and settings.tuoling_api_key.get_secret_value().strip()
    )
    auth_mode = "api_password" if password_ready else "key_secret" if pair_ready else "mock"
    print(f"spark_configured={password_ready or pair_ready}")
    print(f"spark_auth_mode={auth_mode}")
    print(f"tuoling_configured={tuoling_ready}")
    print(f"tuoling_enabled={settings.tuoling_enabled}")
    if args.live:
        asyncio.run(_live_check(settings))
    else:
        print("live_requests=skipped (pass --live only after confirming quota and authorization)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
