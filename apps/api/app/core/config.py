from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "词元研究所"
    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = (
        "postgresql+psycopg://ciyuan:replace-before-use@127.0.0.1:5432/ciyuan?connect_timeout=3"
    )
    redis_url: str = "redis://localhost:6379/0"

    xfyun_maas_base_url: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
    xfyun_maas_api_key: SecretStr = SecretStr("")
    xfyun_maas_model: str = "xopdeepseekv4flash0731"
    xfyun_maas_timeout_seconds: float = Field(default=45.0, gt=0, le=120)
    xfyun_maas_max_retries: int = Field(default=2, ge=0, le=5)
    xfyun_maas_mock_fallback: bool = True
    xfyun_maas_reranker_enabled: bool = False
    xfyun_maas_reranker_model: str = ""
    xfyun_maas_reranker_api_key: SecretStr = SecretStr("")
    xfyun_maas_reranker_candidate_limit: int = Field(default=12, ge=1, le=20)
    xfyun_maas_reranker_timeout_seconds: float = Field(default=8.0, gt=0, le=60)
    xfyun_maas_reranker_max_retries: int = Field(default=1, ge=0, le=5)
    model_max_concurrency: int = Field(default=4, ge=1, le=32)
    model_queue_timeout_seconds: float = Field(default=15.0, gt=0, le=60)

    # Legacy Spark settings remain available for older local environments.
    xfyun_spark_base_url: str = "https://spark-api-open.xf-yun.com/agent/v1"
    xfyun_spark_app_id: SecretStr = SecretStr("")
    xfyun_spark_api_password: SecretStr = SecretStr("")
    xfyun_spark_api_key: SecretStr = SecretStr("")
    xfyun_spark_api_secret: SecretStr = SecretStr("")
    tuoling_base_url: str = ""
    tuoling_api_key: SecretStr = SecretStr("")
    tuoling_context_path: str = "/v1/scenarios/context"
    tuoling_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    tuoling_max_retries: int = Field(default=1, ge=0, le=3)
    tuoling_enabled: bool = False

    # Xfyun adapter tuning (no secrets; used by model_adapters / AI-01)
    xfyun_spark_model: str = "spark-x"
    xfyun_spark_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    xfyun_spark_max_retries: int = Field(default=2, ge=0, le=5)
    xfyun_spark_mock_fallback: bool = True

    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_backend: Literal["lexical", "pgvector"] = "lexical"
    rag_min_score: float = Field(default=0.10, ge=0, le=1)
    rag_vector_weight: float = Field(default=0.65, ge=0, le=1)
    python_online_search_enabled: bool = True
    python_docs_base_url: str = "https://docs.python.org/zh-cn/3.11/"
    python_online_search_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    python_online_search_max_pages: int = Field(default=2, ge=1, le=3)
    code_execution_enabled: bool = False
    sandbox_work_root: str = ""
    sandbox_python_image: str = "python:3.11.15-alpine3.24"
    sandbox_c_image: str = "gcc:13.4.0-bookworm"


@lru_cache
def get_settings() -> Settings:
    return Settings()
