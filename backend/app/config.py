from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./voice_khata.db"
    JWT_SECRET: str = "dev-secret-change-me"
    GNANI_API_KEY: str = ""
    GNANI_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    class Config:
        env_file = ".env"

settings = Settings()
