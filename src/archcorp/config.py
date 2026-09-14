from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./archcorp.db"
    rabbitmq_url: str | None = None
    contract_adapter_available: bool = True
    retry_limit: int = 3


settings = Settings()
