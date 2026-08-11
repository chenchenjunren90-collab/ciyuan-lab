from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VerificationResult:
    accepted: bool
    passed_tests: int
    total_tests: int
    diagnostics: Sequence[str]


class CodeVerifier(Protocol):
    """Verifies code through an isolated runner; never executes it in the API process."""

    async def verify(
        self,
        language: str,
        source_code: str,
        limits: Mapping[str, int],
    ) -> VerificationResult: ...
