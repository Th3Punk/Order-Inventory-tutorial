from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    kafka_bootstrap_servers: str
    outbox_topic: str = "orders.events"
    outbox_dlq_topic: str = "orders.events.dlq"
    poll_batch_size: int = 50
    outbox_poll_interval_seconds: int = 10
    outbox_publish_timeout_seconds: float = 5.0
    outbox_retry_delay_seconds: float = 2.0
    outbox_max_retries: int = 5


settings = Settings()  # type: ignore[call-args]
