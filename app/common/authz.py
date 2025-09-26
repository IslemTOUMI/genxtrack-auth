from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.common.errors import ApiError

def roles_required(*allowed_roles: str):
    """
    Ex: @roles_required("admin")
        @roles_required("admin", "manager")
    """
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            verify_jwt_in_request()  # lève si non authentifié / token invalide
            claims = get_jwt() or {}
            role = claims.get("role")
            if role not in allowed_roles:
                raise ApiError(
                    "Forbidden: insufficient role.",
                    status_code=403,
                    code="forbidden",
                    details={"required_roles": allowed_roles, "current_role": role}
                )
            return fn(*args, **kwargs)
        return inner
    return wrapper
