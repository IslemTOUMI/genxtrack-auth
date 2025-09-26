from flask import Blueprint, request, jsonify
from app.extensions import db
from app.users.models import User
from app.users.schemas import UserOut
from app.common.authz import roles_required

bp = Blueprint("users", __name__)
user_out = UserOut()

@bp.get("/")
@roles_required("admin")
def list_users():
    # simple listing (pas de pagination pour la démo)
    users = User.query.order_by(User.created_at.desc()).all()
    data = [user_out.dump({
        "id": u.id, "email": u.email, "role": u.role,
        "is_active": u.is_active, "created_at": u.created_at, "updated_at": u.updated_at
    }) for u in users]
    return jsonify({"status": "success", "data": data}), 200
