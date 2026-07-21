from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Arya Noble Chatbot API"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/arya_noble"
    SECRET_KEY: str = "supersecretkey" # Replace in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CIS_BASE_URL: str = "http://localhost:8001" # Default fallback
    CIS_API_TOKEN: str = "default_cis_token"
    UPLOAD_DIR: str = "data/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
