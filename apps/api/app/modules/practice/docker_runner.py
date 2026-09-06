"""Docker CLI implementation of the isolated practice sandbox."""

from __future__ import annotations

import asyncio
import tempfile
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from app.modules.practice.sandbox import (
    SandboxOutcome,
    SandboxRequest,
    SandboxUnavailableError,
)

_COMPILE_FAILURE_EXIT_CODE = 120


class DockerSandboxRunner:
    """Execute one test in a short-lived, network-disabled container.

    The source file is mounted read-only. The container has no network, no
    Linux capabilities, a read-only root filesystem, a non-root user, and
    explicit memory/PID limits and a bounded combined output buffer. Submitted
    programs never execute in the FastAPI process or host Python runtime.
    """

    def __init__(
        self,
        *,
        docker_binary: str = "docker",
        python_image: str = "python:3.11.15-alpine3.24",
        c_image: str = "gcc:13.4.0-bookworm",
        work_root: Path | str | None = None,
    ) -> None:
        self._docker_binary = docker_binary
        self._images = {"python": python_image, "c": c_image}
        self._work_root = Path(work_root).resolve() if work_root else None
        if self._work_root is not None:
            self._work_root.mkdir(parents=True, exist_ok=True)

    async def run(self, request: SandboxRequest) -> SandboxOutcome:
        container_name = f"ciyuan-practice-{uuid4().hex}"
        with tempfile.TemporaryDirectory(
            prefix="ciyuan-practice-",
            dir=self._work_root,
        ) as temp_dir:
            source_dir = Path(temp_dir).resolve()
            source_name = "main.py" if request.language == "python" else "main.c"
            source_path = source_dir / source_name
            source_path.write_text(request.source_code, encoding="utf-8")
            # The isolated container deliberately runs as uid/gid 65534. Python's
            # TemporaryDirectory is owner-only by default, so grant that sandbox
            # user traverse/read access while the bind mount remains read-only.
            source_dir.chmod(0o755)
            source_path.chmod(0o644)
            command = self._build_docker_command(
                request=request,
                source_dir=source_dir,
                container_name=container_name,
            )

            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except (FileNotFoundError, OSError) as exc:
                raise SandboxUnavailableError(
                    "Docker CLI is unavailable; isolated code execution cannot start"
                ) from exc

            try:
                stdout_bytes, stderr_bytes, output_limit_exceeded = await asyncio.wait_for(
                    self._capture_bounded(
                        process, request.stdin.encode("utf-8"), request.output_limit_kb * 1024
                    ),
                    timeout=(request.time_limit_ms / 1000) + 5,
                )
            except TimeoutError:
                await self._stop_process(process)
                await self._remove_container(container_name)
                return SandboxOutcome(return_code=-1, timed_out=True)
            except asyncio.CancelledError:
                await self._stop_process(process)
                await self._remove_container(container_name)
                raise
            if output_limit_exceeded:
                await self._remove_container(container_name)

        output_limit_bytes = request.output_limit_kb * 1024
        if process.returncode == 125:
            raise SandboxUnavailableError("Docker could not start the isolated container or image")
        stdout_slice = stdout_bytes[:output_limit_bytes]
        remaining = max(0, output_limit_bytes - len(stdout_slice))
        stderr_slice = stderr_bytes[:remaining]

        return SandboxOutcome(
            return_code=process.returncode or 0,
            stdout=stdout_slice.decode("utf-8", errors="replace"),
            stderr=stderr_slice.decode("utf-8", errors="replace"),
            compilation_failed=process.returncode == _COMPILE_FAILURE_EXIT_CODE,
            output_limit_exceeded=output_limit_exceeded,
        )

    @staticmethod
    async def _capture_bounded(
        process: asyncio.subprocess.Process, stdin: bytes, limit: int
    ) -> tuple[bytes, bytes, bool]:
        """Drain both pipes concurrently while retaining at most limit bytes total."""
        buffers = [bytearray(), bytearray()]
        retained = 0
        exceeded = False

        async def read(stream: asyncio.StreamReader | None, index: int) -> None:
            nonlocal retained, exceeded
            if stream is None:
                return
            while data := await stream.read(4096):
                available = max(0, limit - retained)
                chunk = data[:available]
                buffers[index].extend(chunk)
                retained += len(chunk)
                if len(data) > available and not exceeded:
                    exceeded = True
                    if process.returncode is None:
                        with suppress(ProcessLookupError):
                            process.kill()

        async def write() -> None:
            if process.stdin is None:
                return
            try:
                process.stdin.write(stdin)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()

        tasks = [
            asyncio.create_task(read(process.stdout, 0)),
            asyncio.create_task(read(process.stderr, 1)),
            asyncio.create_task(write()),
            asyncio.create_task(process.wait()),
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        return bytes(buffers[0]), bytes(buffers[1]), exceeded

    @staticmethod
    async def _stop_process(process: asyncio.subprocess.Process) -> None:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()

        async def drain(stream: asyncio.StreamReader | None) -> None:
            if stream is not None:
                while await stream.read(4096):
                    pass

        await asyncio.gather(drain(process.stdout), drain(process.stderr), process.wait())

    def _build_docker_command(
        self,
        *,
        request: SandboxRequest,
        source_dir: Path,
        container_name: str,
    ) -> list[str]:
        script = self._container_script(request.language)
        tmpfs_execute_option = "exec" if request.language == "c" else "noexec"
        return [
            self._docker_binary,
            "run",
            "-i",
            "--rm",
            "--pull",
            "never",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            f"{request.memory_limit_mb}m",
            "--cpus",
            "1",
            "--user",
            "65534:65534",
            "--tmpfs",
            f"/tmp:rw,{tmpfs_execute_option},nosuid,nodev,size=64m",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,src={source_dir},dst=/workspace,readonly",
            self._images[request.language],
            "sh",
            "-c",
            script,
        ]

    @staticmethod
    def _container_script(language: str) -> str:
        if language == "python":
            return (
                "PYTHONPYCACHEPREFIX=/tmp/pycache python -m py_compile /workspace/main.py "
                f"|| exit {_COMPILE_FAILURE_EXIT_CODE}; "
                "exec python -I -B /workspace/main.py"
            )
        return (
            "cc -std=c17 -O2 -Wall -Wextra -pedantic /workspace/main.c "
            f"-o /tmp/program || exit {_COMPILE_FAILURE_EXIT_CODE}; "
            "exec /tmp/program"
        )

    async def _remove_container(self, container_name: str) -> None:
        try:
            cleanup = await asyncio.create_subprocess_exec(
                self._docker_binary,
                "rm",
                "--force",
                container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(cleanup.wait(), timeout=3)
        except (FileNotFoundError, OSError, TimeoutError):
            # The timeout is still the student-facing fact. Cleanup monitoring
            # and adversarial process tests belong to PRACTICE-02.
            return
