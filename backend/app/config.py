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
    scheduler_enabled: bool = True
    # Usado para montar o link de cancelar subscrição nos emails (ver
    # app/services/email_service.py) - sem barra final.
    app_base_url: str = "https://beta.appbenjamin.com"
    finnhub_api_key: str = ""
    twelvedata_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
