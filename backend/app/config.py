from __future__ import annotations

import json
import logging
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────
    app_name: str = "SignalStack Research API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # ── Database ───────────────────────────────────────────────
    database_url: str

    # ── Clerk ──────────────────────────────────────────────────
    clerk_secret_key: str
    clerk_publishable_key: str
    clerk_webhook_secret: str
    clerk_jwks_url: str

    # ── Security ────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000"]

    # ── Logging ─────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── OpenAI ──────────────────────────────────────────────────
    openai_api_key: str

    # Model identifiers — only models that support structured outputs
    openai_model_planner: str = "gpt-4o-mini-2024-07-18"
    openai_model_synthesizer: str = "gpt-4o-2024-08-06"
    openai_model_sentiment: str = "gpt-4o-mini-2024-07-18"
    openai_model_embedding: str = "text-embedding-3-small"

    # ── Token Budgets ────────────────────────────────────────────
    # Planner call: compact query + tool descriptions → small budget
    max_tokens_planner_input: int = 1_000
    max_tokens_planner_output: int = 500
    # Synthesizer call: all tool results as context → large budget
    max_tokens_synthesis_input: int = 8_000
    max_tokens_synthesis_output: int = 4_000
    # Sentiment call: news article batch → medium budget
    max_tokens_sentiment_input: int = 3_000
    max_tokens_sentiment_output: int = 800

    # ── Tool Limits ──────────────────────────────────────────────
    max_companies_per_query: int = 5
    max_tools_per_plan: int = 5  # 4 primary + sentinel for safety
    max_news_articles_fetched: int = 20
    max_news_articles_to_synthesizer: int = 8
    max_vector_chunks_fetched: int = 10
    max_vector_chunks_to_synthesizer: int = 5
    max_historical_price_points: int = 30  # 30-day chart data

    # ── Timeouts (seconds) ───────────────────────────────────────
    tool_timeout_market_data: float = 8.0
    tool_timeout_news_search: float = 10.0
    tool_timeout_vector_retrieval: float = 3.0
    tool_timeout_sentiment: float = 15.0   # LLM call — longer budget
    tool_timeout_sec_filings: float = 5.0
    orchestration_total_timeout: float = 90.0  # Hard wall for the entire pipeline

    # ── Retry Policy ─────────────────────────────────────────────
    llm_max_retries: int = 2         # Synthesis / planner retries on schema failure
    tool_max_retries: int = 1        # External API retries (network errors)

    # ── External Data API Keys (optional — fall back to mock data) ─
    alpha_vantage_api_key: str | None = None
    news_api_key: str | None = None

    # ── ChromaDB ─────────────────────────────────────────────────
    chroma_persist_directory: str = "./chroma_data"
    chroma_collection_name: str = "financial_docs"

    # ── Embedding / Retrieval ────────────────────────────────────
    # Minimum cosine similarity score to include a vector chunk
    embedding_relevance_threshold: float = 0.65

    # ── Cache TTLs (seconds) ─────────────────────────────────────
    cache_ttl_market_data: int = 3_600     # 1 hour
    cache_ttl_news: int = 21_600           # 6 hours
    cache_ttl_filings: int = 86_400        # 24 hours

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_research_per_hour: int = 10
    rate_limit_research_per_day: int = 100

    # ── Validators ───────────────────────────────────────────────

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the asyncpg driver: "
                "postgresql+asyncpg://user:pass@host:port/db"
            )
        return v

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid = {"development", "staging", "production"}
        if v not in valid:
            raise ValueError(f"ENVIRONMENT must be one of: {valid}")
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        v = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid:
            raise ValueError(f"LOG_LEVEL must be one of: {valid}")
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        """
        Accept three formats:
          1. JSON array string:      '["http://localhost:3000"]'
          2. Comma-separated string: 'http://localhost:3000,http://localhost:3001'
          3. Already a list:         ["http://localhost:3000"]
        """
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        if not (v.startswith("sk-") or v.startswith("sk-proj-")):
            raise ValueError(
                "OPENAI_API_KEY must start with 'sk-' or 'sk-proj-'"
            )
        return v

    @field_validator("embedding_relevance_threshold", mode="before")
    @classmethod
    def validate_relevance_threshold(cls, v: float) -> float:
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError(
                "EMBEDDING_RELEVANCE_THRESHOLD must be between 0.0 and 1.0"
            )
        return float(v)

    @field_validator("max_tokens_synthesis_input", mode="before")
    @classmethod
    def validate_synthesis_input_budget(cls, v: int) -> int:
        limit = 128_000  # GPT-4o context window
        if int(v) > limit:
            raise ValueError(
                f"max_tokens_synthesis_input ({v}) exceeds GPT-4o context limit ({limit})"
            )
        return int(v)

    @field_validator("max_tokens_synthesis_output", mode="before")
    @classmethod
    def validate_synthesis_output_budget(cls, v: int) -> int:
        limit = 16_384  # GPT-4o max output tokens
        if int(v) > limit:
            raise ValueError(
                f"max_tokens_synthesis_output ({v}) exceeds GPT-4o max output ({limit})"
            )
        return int(v)

    @field_validator(
        "tool_timeout_market_data",
        "tool_timeout_news_search",
        "tool_timeout_vector_retrieval",
        "tool_timeout_sentiment",
        "tool_timeout_sec_filings",
        "orchestration_total_timeout",
        mode="before",
    )
    @classmethod
    def validate_positive_timeout(cls, v: float) -> float:
        if float(v) <= 0:
            raise ValueError("All timeout values must be positive floats")
        return float(v)

    @model_validator(mode="after")
    def validate_clerk_secret_format(self) -> "Settings":
        if not (
            self.clerk_secret_key.startswith("sk_live_")
            or self.clerk_secret_key.startswith("sk_test_")
        ):
            raise ValueError("CLERK_SECRET_KEY must start with sk_live_ or sk_test_")
        if not self.clerk_webhook_secret.startswith("whsec_"):
            raise ValueError("CLERK_WEBHOOK_SECRET must start with whsec_")
        return self

    @model_validator(mode="after")
    def validate_orchestration_total_timeout(self) -> "Settings":
        tool_max = max(
            self.tool_timeout_market_data,
            self.tool_timeout_news_search,
            self.tool_timeout_sec_filings,
        )
        if self.orchestration_total_timeout < tool_max + 20:
            raise ValueError(
                f"orchestration_total_timeout ({self.orchestration_total_timeout}s) "
                f"must be at least {tool_max + 20}s to allow tool execution + synthesis"
            )
        return self

    # ── Derived properties ────────────────────────────────────────

    @property
    def numeric_log_level(self) -> int:
        return getattr(logging, self.log_level, logging.INFO)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def has_market_data_api(self) -> bool:
        return self.alpha_vantage_api_key is not None

    @property
    def has_news_api(self) -> bool:
        return self.news_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()