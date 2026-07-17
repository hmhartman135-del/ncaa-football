from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cfb:cfb@localhost:5436/ncaa_football"
    redis_url: str = "redis://localhost:6383"
    anthropic_api_key: str = ""
    cfbd_api_key: str = ""
    allowed_origins: str = "http://localhost:3004"

    class Config:
        env_file = ".env"


settings = Settings()
