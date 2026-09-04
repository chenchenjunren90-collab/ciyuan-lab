"""Safely deploy the current working tree into Chen Junren's isolated server directory."""

from __future__ import annotations

import argparse
import getpass
import shlex
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

import paramiko  # type: ignore[import-untyped]

HOST = "39.105.104.230"
PORT = 22
USER = "ciyuan"
BOUNDARY = PurePosixPath("/home/ciyuan/chenjunren")
TARGET = BOUNDARY / "etf_agent" / "ciyuan-lab"
REMOTE_STAGING = BOUNDARY / "deploy_staging"
REMOTE_BACKUPS = BOUNDARY / "deploy_backups"
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".runtime",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}


def should_include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    return not any(part == ".env" or part.startswith(".env.") for part in relative.parts)


def create_source_archive(root: Path, destination: Path) -> None:
    with tarfile.open(destination, "w:gz") as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and should_include(path, root):
                archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)


def run_remote(
    client: paramiko.SSHClient,
    command: str,
    *,
    password: str,
    sudo: bool = False,
    timeout: float = 900,
) -> str:
    transport = client.get_transport()
    if transport is None:
        raise RuntimeError("SSH transport is not connected")
    channel = transport.open_session()
    channel.set_combine_stderr(True)
    channel.exec_command(command)
    if sudo:
        channel.send(password + "\n")
    chunks: list[str] = []
    started = time.monotonic()
    while True:
        if channel.recv_ready():
            text = channel.recv(65536).decode("utf-8", errors="replace")
            chunks.append(text)
            print(text, end="", flush=True)
        if channel.exit_status_ready() and not channel.recv_ready():
            break
        if time.monotonic() - started > timeout:
            channel.close()
            raise TimeoutError(f"remote command timed out: {command}")
        time.sleep(0.05)
    status = channel.recv_exit_status()
    output = "".join(chunks)
    if status != 0:
        raise RuntimeError(f"remote command failed ({status}): {command}\n{output}")
    return output


def connect_ssh(password: str, *, attempts: int = 3) -> paramiko.SSHClient:
    """Connect with bounded retries for transient SSH banner delays."""

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                HOST,
                port=PORT,
                username=USER,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=20,
                banner_timeout=60,
                auth_timeout=30,
            )
            return client
        except (OSError, EOFError, paramiko.SSHException) as exc:
            client.close()
            last_error = exc
            if attempt < attempts:
                print(
                    f"SSH connection attempt {attempt}/{attempts} failed; retrying...",
                    flush=True,
                )
                time.sleep(5)
    raise RuntimeError(f"SSH connection failed after {attempts} attempts") from last_error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", help=argparse.SUPPRESS)
    args = parser.parse_args()
    password = args.password or getpass.getpass(f"SSH password for {USER}@{HOST}: ")
    root = Path(__file__).resolve().parents[1]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    remote_archive = REMOTE_STAGING / f"ciyuan-lab-{stamp}.tar.gz"
    backup_archive = REMOTE_BACKUPS / f"ciyuan-lab-before-{stamp}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="ciyuan-deploy-") as temporary:
        local_archive = Path(temporary) / "source.tar.gz"
        print("Creating source archive...")
        create_source_archive(root, local_archive)

        client = connect_ssh(password)
        try:
            quoted_target = shlex.quote(str(TARGET))
            quoted_boundary = shlex.quote(str(BOUNDARY))
            run_remote(
                client,
                (
                    f"case {quoted_target} in {quoted_boundary}/*) ;; *) exit 90 ;; esac; "
                    f"test -d {quoted_target}; "
                    f"mkdir -p {shlex.quote(str(REMOTE_STAGING))} "
                    f"{shlex.quote(str(REMOTE_BACKUPS))}"
                ),
                password=password,
            )
            with client.open_sftp() as sftp:
                sftp.put(str(local_archive), str(remote_archive))

            run_remote(
                client,
                (
                    "sudo -S -p '' tar "
                    "--exclude=.env.production --exclude=.runtime "
                    f"-czf {shlex.quote(str(backup_archive))} -C {quoted_target} ."
                ),
                password=password,
                sudo=True,
            )
            run_remote(
                client,
                (
                    f"tar -xzf {shlex.quote(str(remote_archive))} -C {quoted_target} "
                    f"&& rm -f {shlex.quote(str(remote_archive))}"
                ),
                password=password,
            )

            compose = "--env-file .env.production -f infra/compose.production.yaml"
            deploy_command = f"""sudo -S -p '' bash -lc '
set -eu
cd {quoted_target}
if docker image inspect ciyuan-lab-api:latest >/dev/null 2>&1; then
  docker tag ciyuan-lab-api:latest ciyuan-lab-api:rollback-{stamp}
fi
if docker image inspect ciyuan-lab-web:latest >/dev/null 2>&1; then
  docker tag ciyuan-lab-web:latest ciyuan-lab-web:rollback-{stamp}
fi
DOCKER_BUILDKIT=0 docker build -f infra/api.Dockerfile -t ciyuan-lab-api:latest .
DOCKER_BUILDKIT=0 docker build -f infra/web.Dockerfile -t ciyuan-lab-web:latest .
docker compose {compose} up -d --no-build --force-recreate api web
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 5 http://127.0.0.1:3004/api/v1/health; then exit 0; fi
  sleep 2
done
exit 91
'"""
            try:
                run_remote(
                    client,
                    deploy_command,
                    password=password,
                    sudo=True,
                    timeout=1200,
                )
            except Exception:
                rollback = f"""sudo -S -p '' bash -lc '
set -eu
cd {quoted_target}
if docker image inspect ciyuan-lab-api:rollback-{stamp} >/dev/null 2>&1; then
  docker tag ciyuan-lab-api:rollback-{stamp} ciyuan-lab-api:latest
fi
if docker image inspect ciyuan-lab-web:rollback-{stamp} >/dev/null 2>&1; then
  docker tag ciyuan-lab-web:rollback-{stamp} ciyuan-lab-web:latest
fi
docker compose {compose} up -d --no-build --force-recreate api web
'"""
                run_remote(client, rollback, password=password, sudo=True, timeout=300)
                raise

            run_remote(
                client,
                f"cd {quoted_target} && sudo -S -p '' docker compose {compose} ps",
                password=password,
                sudo=True,
                timeout=60,
            )
            print(f"Deployment complete. Backup: {backup_archive}")
        finally:
            client.close()


if __name__ == "__main__":
    main()
