"""Language-independent deterministic code verification orchestration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.modules.practice.ports import (
    CodeTestCase,
    CodeVerifier,
    SupportedLanguage,
    VerificationResult,
)
from app.modules.practice.sandbox import (
    SandboxRequest,
    SandboxRunner,
    SandboxUnavailableError,
)

_DEFAULT_LIMITS = {
    "time_limit_ms": 2000,
    "memory_limit_mb": 128,
    "output_limit_kb": 64,
}
_LIMIT_RANGES = {
    "time_limit_ms": (100, 10_000),
    "memory_limit_mb": (16, 512),
    "output_limit_kb": (1, 1024),
}
_MAX_DIAGNOSTIC_CHARS = 500
_MAX_SOURCE_BYTES = 256 * 1024


class DeterministicCodeVerifier(CodeVerifier):
    """Compare isolated execution output with fixed test expectations."""

    def __init__(self, runner: SandboxRunner) -> None:
        self._runner = runner

    async def verify(
        self,
        language: SupportedLanguage,
        source_code: str,
        tests: Sequence[CodeTestCase],
        limits: Mapping[str, int],
    ) -> VerificationResult:
        normalized_limits = self._validate_inputs(language, source_code, tests, limits)
        passed_tests = 0
        diagnostics: list[str] = []

        for test in tests:
            try:
                outcome = await self._runner.run(
                    SandboxRequest(
                        language=language,
                        source_code=source_code,
                        stdin=test.input,
                        **normalized_limits,
                    )
                )
            except SandboxUnavailableError:
                return VerificationResult(
                    accepted=False,
                    passed_tests=passed_tests,
                    total_tests=len(tests),
                    diagnostics=("验证服务暂不可用：隔离运行环境未就绪",),
                    evidence_available=False,
                )

            if outcome.compilation_failed:
                diagnostics.append(
                    "编译检查失败（隐藏测试详细信息已隐藏）"
                    if test.visibility == "hidden"
                    else f"编译检查失败{self._safe_detail(outcome.stderr)}"
                )
                break
            if outcome.timed_out:
                diagnostics.append("运行超时：程序未在限定时间内结束")
                break
            if outcome.output_limit_exceeded:
                diagnostics.append("输出超限：程序输出超过题目限制")
                break
            if outcome.return_code != 0:
                if test.visibility == "hidden":
                    diagnostics.append("隐藏测试运行错误（详细信息已隐藏）")
                else:
                    diagnostics.append(f"运行错误{self._safe_detail(outcome.stderr)}")
                continue

            if self._normalize_output(outcome.stdout) == self._normalize_output(
                test.expected_output
            ):
                passed_tests += 1
                continue

            diagnostics.append(self._wrong_answer_diagnostic(test, outcome.stdout))

        total_tests = len(tests)
        return VerificationResult(
            accepted=passed_tests == total_tests and not diagnostics,
            passed_tests=passed_tests,
            total_tests=total_tests,
            diagnostics=tuple(diagnostics),
        )

    @staticmethod
    def _validate_inputs(
        language: str,
        source_code: str,
        tests: Sequence[CodeTestCase],
        limits: Mapping[str, int],
    ) -> dict[str, int]:
        if language not in {"c", "python"}:
            raise ValueError("language must be c or python")
        if not source_code.strip():
            raise ValueError("source_code must not be empty")
        if len(source_code.encode("utf-8")) > _MAX_SOURCE_BYTES:
            raise ValueError("source_code must not exceed 256 KiB")
        if not tests:
            raise ValueError("tests must not be empty")
        test_ids = [test.id for test in tests]
        if any(not test_id.strip() for test_id in test_ids) or len(set(test_ids)) != len(test_ids):
            raise ValueError("test ids must be non-empty and unique")

        normalized: dict[str, int] = {}
        for name, default in _DEFAULT_LIMITS.items():
            value = limits.get(name, default)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            minimum, maximum = _LIMIT_RANGES[name]
            if not minimum <= value <= maximum:
                raise ValueError(f"{name} must be between {minimum} and {maximum}")
            normalized[name] = value
        return normalized

    @staticmethod
    def _normalize_output(value: str) -> str:
        return value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")

    @staticmethod
    def _safe_detail(stderr: str) -> str:
        compact = " ".join(stderr.split())
        if not compact:
            return ""
        return f"：{compact[:_MAX_DIAGNOSTIC_CHARS]}"

    @classmethod
    def _wrong_answer_diagnostic(cls, test: CodeTestCase, actual_output: str) -> str:
        if test.visibility == "hidden":
            return "隐藏测试未通过（输入与期望输出已隐藏）"
        expected = cls._normalize_output(test.expected_output)[:120]
        actual = cls._normalize_output(actual_output)[:120]
        return f"公开测试 {test.id} 未通过：期望 {expected!r}，实际 {actual!r}"
