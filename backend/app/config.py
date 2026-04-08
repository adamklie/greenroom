from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings. Override via environment variables or .env file."""

    # Path to the root music directory (parent of greenroom/)
    music_dir: Path = Path(__file__).resolve().parents[3]

    # SQLite database path
    db_path: Path = Path(__file__).resolve().parents[2] / "greenroom.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    model_config = {"env_prefix": "GREENROOM_"}


settings = Settings()
