from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Chat"
    DEBUG: bool = True


settings = Settings()
