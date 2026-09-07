import os
from pathlib import Path

from dotenv import load_dotenv


# backend/app/config.py → backend folder → .env file
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


class Settings:
    app_name = os.getenv("APP_NAME", "SIH Intelligent Progress Tracker API")
    database_url = os.getenv("DATABASE_URL", "")

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()