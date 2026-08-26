"""Internal sandbox contract used by deterministic code verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.practice.ports import SupportedLanguage


class SandboxUnavailableError(RuntimeError):
    """The configured isolated runner cannot be started."""


@dataclass(frozen=True, slots=True)
class SandboxRequest:
    language: SupportedLanguage
    source_code: str
    stdin: str
    time_limit_ms: int
    memory_limit_mb: int
    output_limit_kb: int


@dataclass(frozen=True, slots=True)
class SandboxOutcome:
    return_code: int
    stdout: str = ""
    stderr: str = ""
    compilation_failed: bool = False
    timed_out: bool = False
    output_limit_exceeded: bool = False


class SandboxRunner(Protocol):
    """Runs untrusted code outside the API process and host language runtime."""

    async def run(self, request: SandboxRequest) -> SandboxOutcome: ...


class DisabledSandboxRunner:
    """Fail closed when isolated execution has not been explicitly enabled."""

    async def run(self, request: SandboxRequest) -> SandboxOutcome:
        del request
        raise SandboxUnavailableError(
            "isolated code execution is disabled by runtime configuration"
        )
