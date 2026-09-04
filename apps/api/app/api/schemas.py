from typing import Literal

from pydantic import BaseModel, ConfigDict


class NextActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    activity_type: Literal["concept", "objective", "short_answer", "code", "debug", "project"]
    reason: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["mvp"]
    code_execution_enabled: bool
    tuoling_enabled: bool
    modules: list[
        Literal[
            "orchestration",
            "rag",
            "learner_profile",
            "practice",
            "model_adapters",
        ]
    ]
