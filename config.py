import os
from pathlib import Path


class Config:
    SECRET_KEY = os.environ.get("sb_publishable_9oqX4bnEkJqi6xy3Nx4B8Q_40ngCsEo")
    SQLALCHEMY_DATABASE_URI = os.environ.get("https://yzvhijvhatcpvnvmlnve.supabase.co")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", str(Path(__file__).resolve().parent / "uploads")
    )
