"""Real-container regression tests for the deterministic practice runner."""

from __future__ import annotations

import asyncio
import shutil
import subprocess

import pytest

from app.modules.practice import (
    CodeTestCase,
    DeterministicCodeVerifier,
    SupportedLanguage,
)
from app.modules.practice.docker_runner import DockerSandboxRunner

_REQUIRED_IMAGES = (
    "python:3.11.15-alpine3.24",
    "gcc:13.4.0-bookworm",
)


def _docker_environment_ready() -> bool:
    docker_binary = shutil.which("docker")
    if docker_binary is None:
        return False
    try:
        subprocess.run(
            [docker_binary, "info"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            [docker_binary, "image", "inspect", *_REQUIRED_IMAGES],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_environment_ready(),
    reason="Docker engine or fixed practice images are unavailable",
)


def _verify_real_container(
    *,
    language: SupportedLanguage,
    source_code: str,
    stdin: str,
    expected_output: str,
) -> None:
    verifier = DeterministicCodeVerifier(DockerSandboxRunner())
    result = asyncio.run(
        verifier.verify(
            language,
            source_code,
            (
                CodeTestCase(
                    id=f"real-{language}",
                    visibility="public",
                    input=stdin,
                    expected_output=expected_output,
                ),
            ),
            {},
        )
    )

    assert result.accepted is True
    assert result.passed_tests == 1
    assert result.total_tests == 1
    assert result.diagnostics == ()


def test_real_python_container_receives_test_stdin() -> None:
    _verify_real_container(
        language="python",
        source_code="number = int(input())\nprint(number * number)\n",
        stdin="7\n",
        expected_output="49\n",
    )


def test_real_c_container_executes_compiled_binary() -> None:
    _verify_real_container(
        language="c",
        source_code=(
            "#include <stdio.h>\n"
            "int main(void) {\n"
            "    int number;\n"
            '    if (scanf("%d", &number) != 1) return 1;\n'
            '    printf("%d\\n", number * number);\n'
            "    return 0;\n"
            "}\n"
        ),
        stdin="8\n",
        expected_output="64\n",
    )
