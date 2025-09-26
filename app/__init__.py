import os
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager
from flask_limiter import RateLimitExceeded
from .auth.models import TokenBlocklist
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

    # --- CORS: autoriser Authorization header ---
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config.get("CORS_ORIGINS"),
            "allow_headers": app.config.get("CORS_ALLOW_HEADERS"),
            "expose_headers": app.config.get("CORS_EXPOSE_HEADERS"),
            "supports_credentials": False,
        }
    })

    # --- Limiter: storage configurable ---
    limiter.init_app(app)
    limiter._storage_uri = app.config.get("RATELIMIT_STORAGE_URI")  # petit hack sûr pour pointer vers Redis en prod


    # Importer les modèles pour que Flask-Migrate/Alembic voie les tables
    # (Ces imports n’exécutent rien, ils assurent juste que db.Model.metadata contient tout)
    from .users import models as users_models  # noqa: F401
    from .notes import models as notes_models  # noqa: F401
    from .auth import models as auth_models    # noqa: F401

    # Enregistrer les handlers d'erreurs JSON uniformes (ValidationError, ApiError, HTTPException, Exception)
    register_error_handlers(app)


     # --- Callbacks JWT (revocation & erreurs standardisées) ---
    from flask_jwt_extended import verify_jwt_in_request
    from flask_jwt_extended import get_jwt
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


     # --- 429 Rate limit JSON ---
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        return jsonify({"error":{"code":"rate_limited","message":"Rate limit exceeded.","details":{}}}), 429
    
    
    # --- Blueprints ---
    from .auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")

    from .users.routes import bp as users_bp
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")

    from .notes.routes import bp as notes_bp
    app.register_blueprint(notes_bp, url_prefix="/api/v1/notes")
    

    # Appliquer un rate limit par défaut sur tout le blueprint Notes (ex: 60/min)
    from .notes.routes import bp as notes_bp_ref
    limiter.limit("60/minute")(notes_bp_ref)

    # Healthcheck simple + ping DB
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

    # --- Route Factice de validation (pour tests Étape 5) ---
    from .auth.schemas import RegisterSchema
    _register_schema = RegisterSchema()

    @app.post("/api/v1/_test/validate")
    def test_validate():
        payload = request.get_json(silent=True) or {}
        data = _register_schema.load(payload)    # -> lève ValidationError si invalide
        return jsonify({"validated": data})      # renvoie email; password est load_only, donc pas retourné


    # --- Security headers ---
    @app.after_request
    def set_security_headers(resp):
        # API JSON: durcir un minimum
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        # CSP très restrictif (API JSON, pas d'HTML attendu)
        resp.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        # HSTS uniquement si HTTPS et activé
        if app.config.get("ENFORCE_HTTPS") and (request.is_secure or request.headers.get("X-Forwarded-Proto","") == "https"):
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        return resp


    return app
