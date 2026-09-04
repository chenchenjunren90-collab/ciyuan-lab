"""Deterministic practice verification tests for PRACTICE-01."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from app.modules.practice import (
    CodeTestCase,
    DeterministicCodeVerifier,
    DisabledSandboxRunner,
    SupportedLanguage,
    VerificationResult,
)
from app.modules.practice.docker_runner import DockerSandboxRunner
from app.modules.practice.sandbox import (
    SandboxOutcome,
    SandboxRequest,
    SandboxUnavailableError,
)


class FakeSandboxRunner:
    def __init__(
        self,
        outcomes: Sequence[SandboxOutcome | SandboxUnavailableError],
    ) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[SandboxRequest] = []

    async def run(self, request: SandboxRequest) -> SandboxOutcome:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, SandboxUnavailableError):
            raise outcome
        return outcome


PUBLIC_TEST = CodeTestCase(
    id="public-1",
    visibility="public",
    input="2\n",
    expected_output="4\n",
)
HIDDEN_TEST = CodeTestCase(
    id="hidden-1",
    visibility="hidden",
    input="secret-input\n",
    expected_output="secret-output\n",
)


def test_disabled_runner_fails_closed_without_executing_code() -> None:
    verifier = DeterministicCodeVerifier(DisabledSandboxRunner())
    result = asyncio.run(verifier.verify("python", "print(4)", (PUBLIC_TEST,), {}))

    assert result.accepted is False
    assert result.passed_tests == 0
    assert result.diagnostics == ("验证服务暂不可用：隔离运行环境未就绪",)


def _verify(
    runner: FakeSandboxRunner,
    *,
    language: str = "python",
    tests: Sequence[CodeTestCase] = (PUBLIC_TEST,),
    limits: dict[str, int] | None = None,
) -> VerificationResult:
    verifier = DeterministicCodeVerifier(runner)
    return asyncio.run(
        verifier.verify(
            cast(SupportedLanguage, language),
            "print(4)",
            tests,
            limits or {},
        )
    )


def test_correct_python_submission_is_accepted() -> None:
    runner = FakeSandboxRunner([SandboxOutcome(return_code=0, stdout="4\r\n")])

    result = _verify(runner)

    assert result.accepted is True
    assert result.passed_tests == 1
    assert result.total_tests == 1
    assert result.diagnostics == ()
    assert runner.requests[0].language == "python"
    assert runner.requests[0].time_limit_ms == 2000


def test_correct_c_submission_uses_same_result_contract() -> None:
    runner = FakeSandboxRunner([SandboxOutcome(return_code=0, stdout="4\n")])

    result = _verify(runner, language="c")

    assert result.accepted is True
    assert result.passed_tests == 1
    assert result.total_tests == 1


def test_public_wrong_answer_reports_bounded_expected_and_actual() -> None:
    runner = FakeSandboxRunner([SandboxOutcome(return_code=0, stdout="5\n")])

    result = _verify(runner)

    assert result.accepted is False
    assert result.passed_tests == 0
    assert "public-1" in result.diagnostics[0]
    assert "'4'" in result.diagnostics[0]
    assert "'5'" in result.diagnostics[0]


def test_hidden_wrong_answer_does_not_leak_input_or_expected_output() -> None:
    runner = FakeSandboxRunner([SandboxOutcome(return_code=0, stdout="wrong")])

    result = _verify(runner, tests=(HIDDEN_TEST,))

    diagnostic = result.diagnostics[0]
    assert "隐藏测试未通过" in diagnostic
    assert "secret-input" not in diagnostic
    assert "secret-output" not in diagnostic
    assert "wrong" not in diagnostic


def test_hidden_runtime_error_does_not_leak_stderr() -> None:
    runner = FakeSandboxRunner(
        [SandboxOutcome(return_code=1, stderr="secret-input from traceback")]
    )

    result = _verify(runner, tests=(HIDDEN_TEST,))

    assert result.diagnostics == ("隐藏测试运行错误（详细信息已隐藏）",)
    assert "secret-input" not in result.diagnostics[0]


@pytest.mark.parametrize(
    ("outcome", "expected_diagnostic"),
    [
        (
            SandboxOutcome(
                return_code=120,
                stderr="main.c: compiler detail",
                compilation_failed=True,
            ),
            "编译检查失败",
        ),
        (SandboxOutcome(return_code=1, stderr="Traceback"), "运行错误"),
        (SandboxOutcome(return_code=-1, timed_out=True), "运行超时"),
        (SandboxOutcome(return_code=0, output_limit_exceeded=True), "输出超限"),
    ],
)
def test_failure_classes_are_deterministic(
    outcome: SandboxOutcome, expected_diagnostic: str
) -> None:
    result = _verify(FakeSandboxRunner([outcome]))

    assert result.accepted is False
    assert expected_diagnostic in result.diagnostics[0]


def test_unavailable_sandbox_returns_controlled_failure() -> None:
    runner = FakeSandboxRunner([SandboxUnavailableError("docker missing")])

    result = _verify(runner)

    assert result.accepted is False
    assert result.diagnostics == ("验证服务暂不可用：隔离运行环境未就绪",)


@pytest.mark.parametrize(
    ("language", "source_code", "tests", "limits", "message"),
    [
        ("java", "code", (PUBLIC_TEST,), {}, "language"),
        ("python", "  ", (PUBLIC_TEST,), {}, "source_code"),
        ("python", "code", (), {}, "tests"),
        ("python", "code", (PUBLIC_TEST,), {"time_limit_ms": 0}, "time_limit_ms"),
    ],
)
def test_invalid_request_is_rejected_before_sandbox(
    language: str,
    source_code: str,
    tests: Sequence[CodeTestCase],
    limits: dict[str, int],
    message: str,
) -> None:
    verifier = DeterministicCodeVerifier(FakeSandboxRunner([]))
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            verifier.verify(
                cast(SupportedLanguage, language),
                source_code,
                tests,
                limits,
            )
        )


def test_docker_command_declares_minimum_isolation_controls(tmp_path: Path) -> None:
    runner = DockerSandboxRunner()
    request = SandboxRequest(
        language="python",
        source_code="print(4)",
        stdin="2\n",
        time_limit_ms=2000,
        memory_limit_mb=128,
        output_limit_kb=64,
    )

    command = runner._build_docker_command(
        request=request,
        source_dir=tmp_path,
        container_name="ciyuan-test",
    )

    joined = " ".join(str(part) for part in command)
    assert "-i" in command
    assert "--network none" in joined
    assert "--pull never" in joined
    assert "--read-only" in command
    assert "--cap-drop ALL" in joined
    assert "--security-opt no-new-privileges" in joined
    assert "--memory 128m" in joined
    assert "--user 65534:65534" in joined
    assert "/tmp:rw,noexec,nosuid,nodev,size=64m" in command
    assert "python:3.11.15-alpine3.24" in command
    assert "python -I -B /workspace/main.py" in command[-1]


def test_c_docker_command_compiles_as_c17(tmp_path: Path) -> None:
    runner = DockerSandboxRunner()
    request = SandboxRequest(
        language="c",
        source_code="int main(void) { return 0; }",
        stdin="",
        time_limit_ms=2000,
        memory_limit_mb=128,
        output_limit_kb=64,
    )

    command = runner._build_docker_command(
        request=request,
        source_dir=tmp_path,
        container_name="ciyuan-test",
    )

    assert "gcc:13.4.0-bookworm" in command
    assert "/tmp:rw,exec,nosuid,nodev,size=64m" in command
    assert "cc -std=c17" in command[-1]
