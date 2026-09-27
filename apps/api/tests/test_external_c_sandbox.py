"""Execute authored C acceptance fixtures only through the production sandbox."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from app.modules.course_content import CoursePackRepository
from app.modules.practice import CodeTestCase, DeterministicCodeVerifier
from app.modules.practice.docker_runner import DockerSandboxRunner

FIXTURES = Path(__file__).parent / "fixtures" / "external_c"
EXERCISES = ("REVERSE", "LEAP", "RAINDROPS", "HAMMING")


@pytest.fixture(scope="module")
def verifier() -> DeterministicCodeVerifier:
    try:
        for command in (
            ["docker", "info"],
            ["docker", "image", "inspect", "gcc:13.4.0-bookworm"],
        ):
            subprocess.run(command, check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        if os.getenv("CIYUAN_REQUIRE_C_SANDBOX") == "1":
            pytest.fail("C sandbox is mandatory for this acceptance run but is unavailable")
        pytest.skip("Docker engine or fixed C image unavailable; no host execution fallback")
    return DeterministicCodeVerifier(DockerSandboxRunner())


def mutant(name: str, source: str) -> str:
    """One deliberate beginner mistake per task; never an alternative oracle."""
    replacements = {
        "REVERSE": ("text[i - 1]", "text[length - i]"),
        "LEAP": ("year % 400 == 0 || (year % 4 == 0 && year % 100 != 0)", "year % 4 == 0"),
        "RAINDROPS": ("if (number % 5 == 0)", "else if (number % 5 == 0)"),
        "HAMMING": ('if (n != m) { puts("-1"); return 0; }', "if (n > m) n = m;"),
    }
    before, after = replacements[name]
    assert source.count(before) == 1
    return source.replace(before, after)


@pytest.mark.parametrize("name", EXERCISES)
@pytest.mark.parametrize("correct", [True, False], ids=["reference", "mutant"])
def test_external_c_reference_and_mutant(
    verifier: DeterministicCodeVerifier, name: str, correct: bool
) -> None:
    record = CoursePackRepository().get_practice_activity("c", f"C-EXERCISM-{name}")
    source = (FIXTURES / f"{name.lower()}.c").read_text(encoding="utf-8")
    if not correct:
        source = mutant(name, source)
    tests = tuple(CodeTestCase(**case) for case in record.evaluation["tests"])
    runtime = record.evaluation["runtime"]
    limits = {key: runtime[key] for key in ("time_limit_ms", "memory_limit_mb", "output_limit_kb")}
    result = asyncio.run(verifier.verify("c", source, tests, limits))
    assert result.evidence_available, result.diagnostics
    assert result.accepted is correct, result.diagnostics
    assert result.total_tests == len(tests)
    if correct:
        assert result.passed_tests == len(tests)
        assert not result.diagnostics
    else:
        assert result.passed_tests < len(tests)
        assert result.diagnostics
        assert not any("编译" in message or "运行错误" in message for message in result.diagnostics)


@pytest.mark.parametrize("name", EXERCISES)
def test_reference_fixture_has_one_targeted_mutation(name: str) -> None:
    source = (FIXTURES / f"{name.lower()}.c").read_text(encoding="utf-8")
    assert "int main(void)" in source
    assert mutant(name, source) != source
