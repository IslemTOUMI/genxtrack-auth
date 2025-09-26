import os
from flask import Flask, jsonify, request
from flask_limiter import RateLimitExceeded
from dotenv import load_dotenv
from sqlalchemy import text

from .config import DevConfig, ProdConfig, TestConfig
from .extensions import db, migrate, jwt, cors, limiter
from .common.errors import register_error_handlers
from .common.logging import setup_json_logging, register_request_logging


def create_app():
    # Charge .env si présent (dev)
    load_dotenv()

    app = Flask(__name__)

    # Choix config selon env
    env = os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")
    if env in ("test", "testing"):
        app.config.from_object(TestConfig)
    elif env == "production":
        app.config.from_object(ProdConfig)
    else:
        app.config.from_object(DevConfig)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    setup_json_logging(app)
    register_request_logging(app)

    # --- Helpers ---
    def _csv(value, default_if_empty):
        """Convertit une chaîne CSV en liste, sinon retourne la valeur telle quelle ou un défaut."""
        if value is None:
            return default_if_empty
        if isinstance(value, str) and "," in value:
            items = [x.strip() for x in value.split(",") if x.strip()]
            return items if items else default_if_empty
        return value

    # --- CORS: whitelist + headers ---
    origins = _csv(app.config.get("CORS_ORIGINS", "*"), "*")
    allow_headers = _csv(app.config.get("CORS_ALLOW_HEADERS"), ["Authorization", "Content-Type"])
    expose_headers = _csv(app.config.get("CORS_EXPOSE_HEADERS"), ["Content-Type"])

    cors.init_app(app, resources={
        r"/api/*": {
            "origins": origins,
            "allow_headers": allow_headers,
            "expose_headers": expose_headers,
            "supports_credentials": False,
        }
    })

    # --- Limiter: storage & défaut configurable ---
    limiter.init_app(app)   # PAS d'arguments ici ; Limiter lit RATELIMIT_* depuis app.config

    # Importer les modèles pour que Flask-Migrate/Alembic voie les tables
    from .users import models as users_models  # noqa: F401
    from .notes import models as notes_models  # noqa: F401
    from .auth import models as auth_models    # noqa: F401

    # Handlers d'erreurs JSON uniformes
    register_error_handlers(app)

    # --- Callbacks JWT (revocation & erreurs standardisées) ---
    from flask import jsonify
    from .auth.models import TokenBlocklist

    @jwt.token_in_blocklist_loader
    def is_token_revoked(jwt_header, jwt_payload: dict) -> bool:
        jti = jwt_payload["jti"]
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": {"code": "token_revoked", "message": "Token has been revoked", "details": {}}}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": {"code": "token_expired", "message": "Token has expired", "details": {}}}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(err_msg):
        return jsonify({"error": {"code": "token_invalid", "message": err_msg, "details": {}}}), 422

    @jwt.unauthorized_loader
    def unauthorized_callback(err_msg):
        return jsonify({"error": {"code": "authorization_required", "message": err_msg, "details": {}}}), 401

    # --- Security headers (UN SEUL after_request) ---
    @app.after_request
    def set_security_headers(resp):
        path = request.path or ""

        if path.startswith("/docs"):
            # Docs: assets locaux + léger assouplissement
            resp.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "connect-src 'self'; "
                "img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; "
                "font-src 'self' data:"
            )
            resp.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            # API JSON: CSP très restrictif (pas d'HTML attendu)
            resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            resp.headers["X-Frame-Options"] = "DENY"

        # Headers communs
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"

        # HSTS uniquement si HTTPS (prod / reverse-proxy)
        if (env == "production" or app.config.get("ENFORCE_HTTPS")) and (
            request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
        ):
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return resp

    # --- 429 Rate limit JSON ---
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        return jsonify({"error": {"code": "rate_limited", "message": "Rate limit exceeded.", "details": {}}}), 429

    # --- Blueprints ---
    from .auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")

    from .users.routes import bp as users_bp
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")

    from .notes.routes import bp as notes_bp
    app.register_blueprint(notes_bp, url_prefix="/api/v1/notes")

    from .docs.routes import bp as docs_bp
    app.register_blueprint(docs_bp)

    # Appliquer un rate limit par défaut sur tout le blueprint Notes (ex: 60/min)
    from .notes.routes import bp as notes_bp_ref
    limiter.limit("60/minute")(notes_bp_ref)

    # Liveness probe (ping DB simple)
    @app.get("/healthz")
    def healthz():
        db_status = "up"
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            db_status = "down"
        return jsonify({
            "status": "ok",
            "env": env,
            "db": db_status
        })

    # Readiness probe (DB + Redis si configuré)
    @app.get("/readyz")
    def readyz():
        status = {"db": "down", "redis": "n/a"}
        ok = True

        # DB
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["db"] = "up"
        except Exception:
            ok = False
            status["db"] = "down"

        # Redis (uniquement si RATELIMIT_STORAGE_URI utilise redis)
        try:
            uri = app.config.get("RATELIMIT_STORAGE_URI", "memory://")
            if uri.startswith(("redis://", "rediss://")):
                import redis  # import tardif
                r = redis.from_url(uri)
                r.ping()
                status["redis"] = "up"
            else:
                status["redis"] = "n/a"
        except Exception:
            ok = False
            status["redis"] = "down"

        status["status"] = "ok" if ok else "error"
        return jsonify(status), (200 if ok else 503)

    # --- Route Factice de validation (pour tests Étape 5) ---
    from .auth.schemas import RegisterSchema
    _register_schema = RegisterSchema()

    @app.post("/api/v1/_test/validate")
    def test_validate():
        payload = request.get_json(silent=True) or {}
        data = _register_schema.load(payload)
        return jsonify({"validated": data})

    return app
