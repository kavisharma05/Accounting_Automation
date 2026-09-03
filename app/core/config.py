from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Accounting Automation"
    debug: bool = False
    secret_key: str = "change-me"
    database_url: str = "postgresql+psycopg2://accounting:accounting@localhost:5432/accounting"
    redis_url: str = "redis://localhost:6379/0"

    messaging_provider: str = "mock"
    document_provider: str = "mock"
    storage_provider: str = "local"
    email_provider: str = "mock"
    gsp_provider: str = "mock"

    local_storage_path: str = "./data/documents"
    s3_bucket: str = ""
    s3_endpoint_url: str | None = None
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    anthropic_api_key: str = ""
    whatsapp_verify_token: str = "dev-verify-token"
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    auto_post_confidence_threshold: float = 0.0  # 0 = always require confirmation (IMP-DEFAULT)
    job_max_retries: int = 3


settings = Settings()
