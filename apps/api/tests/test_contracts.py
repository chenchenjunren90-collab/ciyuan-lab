from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_CONTRACT = REPO_ROOT / "contracts" / "openapi.yaml"


def load_contract() -> dict[str, Any]:
    with OPENAPI_CONTRACT.open(encoding="utf-8") as contract_file:
        document: object = yaml.safe_load(contract_file)
    assert isinstance(document, dict)
    return cast(dict[str, Any], document)


def test_runtime_paths_match_public_contract() -> None:
    contract = load_contract()
    runtime = app.openapi()

    # 契约先行：运行时暴露的路径必须是契约的子集，不得出现契约之外的路径。
    assert set(runtime["paths"]) <= set(contract["paths"])


def test_runtime_response_constraints_match_public_contract() -> None:
    contract_schemas = load_contract()["components"]["schemas"]
    runtime_schemas = app.openapi()["components"]["schemas"]

    # 运行时暴露的 Schema 必须是契约的子集，且字段约束与契约一致。
    assert set(runtime_schemas) <= set(contract_schemas)
    for schema_name, runtime_schema in runtime_schemas.items():
        contract_schema = contract_schemas[schema_name]
        assert set(runtime_schema.get("required", [])) == set(contract_schema["required"])
        assert runtime_schema.get("additionalProperties") is contract_schema[
            "additionalProperties"
        ]
