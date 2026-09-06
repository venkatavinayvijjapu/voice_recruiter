from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    explabs_api_key: str
    explabs_base_url: str = "https://api.experientiallabs.ai/v1"
    explabs_model: str = "gpt-6-astra"
    hunar_api_key: str
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    hunar_agent_id: str
    app_cors_origins: str = "http://localhost:3000"
    jwt_secret: str
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore"
    )

settings = Settings()
