"""Configuración de la aplicación cargada desde variables de entorno (.env)."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria '{name}'. Revisa tu archivo .env "
            f"(puedes basarte en .env.example)."
        )
    return value


class Config:
    # --- Sesiones Flask (cookies de las páginas HTML) ---
    SECRET_KEY = _required("SECRET_KEY")

    # --- Base de datos MySQL ---
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_USER = _required("DB_USER")
    DB_PASSWORD = _required("DB_PASSWORD")
    DB_NAME = _required("DB_NAME")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # --- API JSON con JWT (independiente de las cookies de sesión) ---
    JWT_SECRET_KEY = _required("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ["headers"]

    # --- Carga de archivos Excel ---
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB, suficiente para excels de ~20k filas
    UPLOAD_EXTENSIONS = {".xlsx", ".xls"}

    # --- Respaldos ---
    BACKUP_DIR = os.environ.get("BACKUP_DIR", "respaldos")
    BACKUP_KEEP = 5
    MYSQLDUMP_PATH = os.environ.get("MYSQLDUMP_PATH", "mysqldump")

    # --- Paginación ---
    ITEMS_PER_PAGE = 10

    # --- CORS (solo aplicado al prefijo /api/) ---
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
