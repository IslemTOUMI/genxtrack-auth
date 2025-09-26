from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app.extensions import db, limiter
from app.users.models import User
from app.auth.models import TokenBlocklist
from app.auth.schemas import RegisterSchema, LoginSchema, TokensOut, MeOut
from app.common.errors import ApiError
from datetime import datetime, timezone
import uuid
from app.extensions import db

bp = Blueprint("auth", __name__)

register_schema = RegisterSchema()
login_schema = LoginSchema()
tokens_out = TokensOut()
me_out = MeOut()

def _issue_tokens(user: User, fresh: bool = True) -> dict:
    identity = str(user.id)
    claims = {"role": user.role, "is_active": user.is_active}
    access_token = create_access_token(identity=identity, additional_claims=claims, fresh=fresh)
    refresh_token = create_refresh_token(identity=identity, additional_claims=claims)
    return {"access_token": access_token, "refresh_token": refresh_token}

from sqlalchemy.exc import IntegrityError

@bp.post("/register")
@limiter.limit("10 per hour")
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
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role, "is_active": user.is_active}, fresh=True)
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 201

@bp.post("/login")
@limiter.limit("5 per minute")  # anti brute force
def login():
    payload = request.get_json(silent=True) or {}
    data = login_schema.load(payload)
    from app.auth.service import authenticate_user
    user = authenticate_user(data["email"], data["password"])
    toks = _issue_tokens(user, fresh=True)
    return jsonify(tokens_out.dump(toks)), 200

@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    j = get_jwt()
    identity = j["sub"]
    try:
        uid = uuid.UUID(identity)
    except Exception:
        raise ApiError("Invalid token subject.", 422, "token_invalid_sub")

    user = db.session.get(User, uid)
    if not user or not user.is_active:
        raise ApiError("User not found or inactive.", 403, "user_inactive")

    claims = {"role": user.role, "is_active": user.is_active}
    access_token = create_access_token(identity=identity, additional_claims=claims, fresh=False)
    return jsonify({"access_token": access_token}), 200


@bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    try:
        uid = uuid.UUID(identity)
    except Exception:
        raise ApiError("Invalid token subject.", 422, "token_invalid_sub")

    user = db.session.get(User, uid)
    if not user:
        raise ApiError("User not found.", 404, "not_found")

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
    ttype = j["type"]  # "access" ou "refresh"
    db.session.add(TokenBlocklist(jti=jti, token_type=ttype, revoked_at=datetime.now(timezone.utc)))
    db.session.commit()
    return jsonify({"status": "success", "message": f"{ttype} token revoked"}), 200
