"""Print only the non-secret active provider settings from production."""

from __future__ import annotations

import os
import shlex

from scripts.deploy_server import TARGET, connect_ssh, run_remote


def main() -> None:
    password = os.environ["CIYUAN_SSH_PASSWORD"]
    client = connect_ssh(password)
    try:
        target = shlex.quote(str(TARGET))
        command = (
            f"cd {target} && sudo -S -p '' docker compose "
            "--env-file .env.production -f infra/compose.production.yaml "
            "exec -T api env | grep -E '^(MODEL_PROVIDER|XFYUN_MAAS_MODEL)='"
        )
        run_remote(client, command, password=password, sudo=True, timeout=60)
        probe = (
            "import asyncio; "
            "from app.core.config import get_settings; "
            "from app.modules.model_adapters.factory import build_model_adapter; "
            "from app.modules.model_adapters.ports import ChatMessage; "
            "adapter=build_model_adapter(get_settings()); "
            "response=asyncio.run(adapter.complete(["
            "ChatMessage(role='user', content='仅回答：连接成功')])); "
            "print('LIVE_PROVIDER='+response.provider); "
            "print('LIVE_MODEL='+response.model); "
            "print('LIVE_CONTENT_OK='+str(bool(response.content.strip())))"
        )
        live_command = (
            f"cd {target} && sudo -S -p '' docker compose "
            "--env-file .env.production -f infra/compose.production.yaml "
            f"exec -T api python -c {shlex.quote(probe)}"
        )
        run_remote(client, live_command, password=password, sudo=True, timeout=120)
    finally:
        client.close()


if __name__ == "__main__":
    main()
