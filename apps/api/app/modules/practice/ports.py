from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

SupportedLanguage = Literal["c", "python"]
TestVisibility = Literal["public", "hidden"]


@dataclass(frozen=True, slots=True)
class CodeTestCase:
    id: str
    visibility: TestVisibility
    input: str
    expected_output: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    accepted: bool
    passed_tests: int
    total_tests: int
    diagnostics: Sequence[str]
    # An unavailable runner is not evidence about the learner's code.
    evidence_available: bool = True


class CodeVerifier(Protocol):
    """Verifies code through an isolated runner; never executes it in the API process."""

    async def verify(
        self,
        language: SupportedLanguage,
        source_code: str,
        tests: Sequence[CodeTestCase],
        limits: Mapping[str, int],
    ) -> VerificationResult: ...
