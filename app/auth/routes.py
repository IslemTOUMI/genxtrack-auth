from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from sqlalchemy.exc import IntegrityError
import uuid

from app.extensions import db, limiter
from app.users.models import User
from app.auth.models import TokenBlocklist
from app.auth.schemas import RegisterSchema, LoginSchema, TokensOut, MeOut
from app.common.errors import ApiError

bp = Blueprint("auth", __name__)

register_schema = RegisterSchema()
login_schema = LoginSchema()
tokens_out = TokensOut()
me_out = MeOut()


def _issue_tokens(user: User, fresh: bool = True) -> dict:
    """Émet un couple {access, refresh} avec des claims homogènes."""
    identity = str(user.id)
    claims = {"role": user.role, "is_active": user.is_active}
    access_token = create_access_token(identity=identity, additional_claims=claims, fresh=fresh)
    refresh_token = create_refresh_token(identity=identity, additional_claims=claims)
    return {"access_token": access_token, "refresh_token": refresh_token}


def _user_from_identity(identity: str) -> User:
    """Convertit sub->UUID, charge l'utilisateur, vérifie activité.
       Lève ApiError en cas de problème.
    """
    try:
        uid = uuid.UUID(identity)
    except Exception:
        raise ApiError("Invalid token subject.", 422, "token_invalid_sub")

    user = db.session.get(User, uid)
    if not user:
        raise ApiError("User not found.", 404, "not_found")
    if not user.is_active:
        raise ApiError("User not found or inactive.", 403, "user_inactive")
    return user


@bp.post("/register")
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH_REGISTER", "10/hour"))
def register():
    payload = request.get_json(silent=True) or {}
    data = register_schema.load(payload)

    user = User(email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Email already exists.", 409, "conflict", details={"email": user.email})

    toks = _issue_tokens(user, fresh=True)
    return jsonify(tokens_out.dump(toks)), 201


@bp.post("/login")
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH_LOGIN", "5/minute"))
def login():
    payload = request.get_json(silent=True) or {}
    data = login_schema.load(payload)

    from app.auth.service import authenticate_user
    user = authenticate_user(data["email"], data["password"])

    toks = _issue_tokens(user, fresh=True)
    return jsonify(tokens_out.dump(toks)), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH_REFRESH", "30/minute"))
def refresh():
    """Rotation stricte du refresh:
    - révoque le refresh courant (jti),
    - renvoie un NOUVEAU couple {access, refresh}.
    """
    j = get_jwt()
    old_jti = j["jti"]
    identity = j["sub"]

    # charge & vérifie l'utilisateur depuis le sub
    user = _user_from_identity(identity)

    # révoquer l'ancien refresh (idempotent)
    TokenBlocklist.revoke(old_jti, "refresh")

    # renvoyer un nouveau couple
    toks = _issue_tokens(user, fresh=False)
    return jsonify(tokens_out.dump(toks)), 200


@bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = _user_from_identity(identity)

    data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }
    return jsonify(me_out.dump(data)), 200


@bp.post("/logout")
@jwt_required(verify_type=False)  # accepte access ou refresh
def logout():
    j = get_jwt()
    jti = j["jti"]
    ttype = j["type"]  # "access" | "refresh"

    # idempotent
    TokenBlocklist.revoke(jti, ttype)

    return jsonify({"status": "success", "message": f"{ttype} token revoked"}), 200
