from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./inventory.db"
    RESERVATION_EXPIRY_MINUTES: int = 15

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
