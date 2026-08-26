"""Deterministic, non-identifying data fixtures for finance practice projects."""

from __future__ import annotations

import hashlib
import json
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

SyntheticValue: TypeAlias = str | int | float | bool | None


class SyntheticScenarioDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    columns: list[str] = Field(min_length=1, max_length=20)
    rows: list[dict[str, SyntheticValue]] = Field(min_length=1, max_length=50)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


_ROWS: dict[str, list[dict[str, SyntheticValue]]] = {
    "PY-PROJ-FINANCE-DATA-01": [
        {
            "customer_id": "SYN-C001",
            "period": "2026-01",
            "due": 1200,
            "paid": 1200,
            "status": "on_time",
        },
        {
            "customer_id": "SYN-C002",
            "period": "2026-01",
            "due": 800,
            "paid": None,
            "status": "missing",
        },
        {
            "customer_id": "SYN-C003",
            "period": "2026-01",
            "due": -50,
            "paid": 0,
            "status": "invalid",
        },
        {
            "customer_id": "SYN-C001",
            "period": "2026-01",
            "due": 1200,
            "paid": 1200,
            "status": "duplicate",
        },
    ],
    "PY-PROJ-BANK-MARKETING-01": [
        {
            "record_id": "SYN-M001",
            "segment": "starter",
            "channel": "web",
            "campaign": "A",
            "response": "yes",
        },
        {
            "record_id": "SYN-M002",
            "segment": "starter",
            "channel": "phone",
            "campaign": "A",
            "response": "no",
        },
        {
            "record_id": "SYN-M003",
            "segment": "growth",
            "channel": "web",
            "campaign": "B",
            "response": "yes",
        },
        {
            "record_id": "SYN-M003",
            "segment": "growth",
            "channel": "web",
            "campaign": "B",
            "response": "duplicate",
        },
    ],
    "PY-PROJ-COMPLAINT-STATS-01": [
        {
            "case_id": "SYN-P001",
            "product": "deposit",
            "issue": "transfer_delay",
            "received_date": "2026-01-03",
            "status": "closed",
            "timely": True,
        },
        {
            "case_id": "SYN-P002",
            "product": "consumer_loan",
            "issue": "statement_error",
            "received_date": "2026-01-04",
            "status": "open",
            "timely": False,
        },
        {
            "case_id": "SYN-P003",
            "product": "unknown",
            "issue": "other",
            "received_date": "bad-date",
            "status": "pending",
            "timely": False,
        },
    ],
    "DS-PROJ-TRANSACTION-GRAPH-01": [
        {
            "edge_id": "SYN-E001",
            "source": "SYN-A01",
            "target": "SYN-A02",
            "amount": 300,
            "timestamp": "2026-01-01T09:00:00Z",
        },
        {
            "edge_id": "SYN-E002",
            "source": "SYN-A02",
            "target": "SYN-A03",
            "amount": 280,
            "timestamp": "2026-01-01T09:05:00Z",
        },
        {
            "edge_id": "SYN-E003",
            "source": "SYN-A03",
            "target": "SYN-A01",
            "amount": 260,
            "timestamp": "2026-01-01T09:10:00Z",
        },
        {
            "edge_id": "SYN-E004",
            "source": "SYN-A04",
            "target": "SYN-A05",
            "amount": 40,
            "timestamp": "2026-01-01T10:00:00Z",
        },
    ],
}


def build_synthetic_dataset(project_id: str) -> SyntheticScenarioDataset:
    rows = _ROWS.get(
        project_id,
        [
            {"record_id": "SYN-001", "value": 10, "status": "valid"},
            {"record_id": "SYN-002", "value": None, "status": "missing"},
        ],
    )
    columns = list(rows[0])
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return SyntheticScenarioDataset(
        filename=f"{project_id.lower()}-synthetic.json",
        columns=columns,
        rows=rows,
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
