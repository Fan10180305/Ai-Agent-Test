"""Runtime configuration for the Qpon data analysis agent."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bq_project: str = "oppo-gcp-prod-digfood-129869"
    bq_location: str = "asia-southeast2"
    bq_allowed_datasets: str = "qpon_rpt_d,qpon_dws_d,qpon_dwd_d"
    bq_max_bytes_billed: int = 10 * 1024 * 1024 * 1024  # 10 GiB
    bq_max_rows: int = 500
    bq_query_timeout_sec: int = 60

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    feishu_allowlist_open_ids: str = ""

    # HTTP /v1/ask: off by default (Feishu is the production entry)
    enable_http_ask: bool = False
    ask_api_key: str = ""

    log_level: str = "INFO"
    port: int = 8080

    @property
    def allowed_datasets(self) -> frozenset[str]:
        return frozenset(
            d.strip() for d in self.bq_allowed_datasets.split(",") if d.strip()
        )

    @property
    def allowlist_open_ids(self) -> frozenset[str]:
        return frozenset(
            x.strip() for x in self.feishu_allowlist_open_ids.split(",") if x.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
