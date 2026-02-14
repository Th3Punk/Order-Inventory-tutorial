from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    kafka_bootstrap_servers: str
    kafka_topic: str = "orders.sku-stats"
    kafka_audit_topic: str = "orders.events"
    kafka_group_id: str = "mongo-writer-v1"

    mongo_url: str
    mongo_db: str = "app"
    mongo_collection: str = "sku_stats"
    mongo_audit_collection: str = "order_events"

    poll_timeout_seconds: float = 1.0


settings = Settings()  # type: ignore[call-arg]
