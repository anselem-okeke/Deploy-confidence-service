from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "deploy-confidence-service"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "deploy_confidence"
    postgres_user: str = "deploy_confidence"
    postgres_password: str = "change_me"
    database_url: str = (
        "postgresql+psycopg://deploy_confidence:change_me@localhost:5432/deploy_confidence"
    )

    prometheus_url: str = "http://localhost:9090"

    check_interval_seconds: int = 120
    deploy_threshold: int = 70

    kubernetes_in_cluster: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
