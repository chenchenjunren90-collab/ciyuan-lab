from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    provider: str
    model: str
    usage: Mapping[str, int]


class ModelAdapter(Protocol):
    """Keep MaaS, legacy Spark and mock providers behind one interface."""

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelResponse: ...
