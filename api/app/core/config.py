from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///../db/app.db"
    ingest_folder: str = "../data"
    api_port: int = 8000
    web_port: int = 5173

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
