import os
from datetime import timedelta

class BaseConfig:
    # Clés & secrets
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://app_user:app_password_strong@localhost:5433/app_db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_TOKEN_LOCATION = ["headers"]        # On reste en header-based
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
    JWT_COOKIE_SECURE = False               # Passera à True si un jour on utilise les cookies en prod

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Limiter (par défaut on ne bride pas, on réglera par route sensible)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", None)  # ex: "100 per minute"

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
    CORS_EXPOSE_HEADERS = os.getenv("CORS_EXPOSE_HEADERS", "Content-Type")

    # Limites de requêtes
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", None)  # ex: "200 per minute" si tu veux un défaut global
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")  # Prod: "redis://localhost:6379/0"

    # Taille max payload (1 Mo par défaut)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "1000000"))

    # SQLAlchemy: connexions plus robustes
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # 30 min
    }

    # HTTPS strict (HSTS) si activé ET connexion sécurisée
    ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False

class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
