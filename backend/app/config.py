from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@db:5432/benjamin"
    jwt_secret: str = "change-me"
    jwt_expires_hours: int = 24
    allow_registration: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    summary_email_to: str = ""
    scheduler_enabled: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
