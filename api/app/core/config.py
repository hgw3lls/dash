from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///../db/app.db"
    ingest_folder: str = "../data"
    api_port: int = 8000
    web_port: int = 5173

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        api_dir = Path(__file__).resolve().parents[2]

        if self.database_url.startswith("sqlite:///") and not self.database_url.startswith(
            "sqlite:////"
        ):
            db_path = (api_dir / self.database_url.removeprefix("sqlite:///")).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite:///{db_path}"

        if not Path(self.ingest_folder).is_absolute():
            self.ingest_folder = str((api_dir / self.ingest_folder).resolve())

        return self


settings = Settings()
