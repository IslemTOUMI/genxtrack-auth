import os
from datetime import timedelta
from sqlalchemy.pool import StaticPool

class BaseConfig:
    # --- Secrets
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    RATELIMIT_AUTH_REGISTER = os.getenv("RATELIMIT_AUTH_REGISTER", "10/hour")

    # --- Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://app_user:app_password_strong@localhost:5433/app_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connexions SQLAlchemy robustes
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # --- JWT
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", "7"))
    )
    JWT_COOKIE_SECURE = False  # passera à True si un jour on utilise des cookies en prod

    # --- CORS (strings CSV -> découpées dans __init__)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
    CORS_EXPOSE_HEADERS = os.getenv("CORS_EXPOSE_HEADERS", "Content-Type")

    # --- Rate limit
    # Pas de limite globale par défaut (évite les 429 surprises)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", None)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")  # prod: redis://redis:6379/0
    RATELIMIT_AUTH_LOGIN = os.getenv("RATELIMIT_AUTH_LOGIN", "5/minute")
    RATELIMIT_AUTH_REFRESH = os.getenv("RATELIMIT_AUTH_REFRESH", "30/minute")

    # --- Sécurité HTTP
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "1000000"))  # ~1 Mo
    ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    # IMPORTANT: pool adapté à SQLite en mémoire
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
