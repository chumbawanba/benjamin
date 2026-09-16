from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@db:5432/benjamin"
    jwt_secret: str = "change-me"
    jwt_expires_hours: int = 24
    allow_registration: bool = False
    # Chave partilhada para os endpoints /admin/* (ver security.py::require_admin).
    # Vazia por omissao => os endpoints ficam sempre a devolver 401 (fail-closed).
    admin_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Endereço que aparece no "De:" dos emails - separado de smtp_user porque
    # em serviços como o Brevo o utilizador de autenticação SMTP não é
    # necessariamente um endereço verificado no domínio (ex: pode ser o email
    # de login da conta, não noreply@appbenjamin.com). Sem isto, o "De:"
    # herdava sempre o smtp_user, o que falha ou fica com mau aspeto consoante
    # o provedor. Vazio = mantém o comportamento antigo (usa smtp_user).
    smtp_from_email: str = ""
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
