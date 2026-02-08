from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str | None = None
    jwt_secret: str
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 1209600
    cors_origins: list[str] = ["http://localhost:5173"]
    env: str = "production"
    kafka_bootstrap_servers: str


settings = Settings()  # type: ignore[call-arg]
