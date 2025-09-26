from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.users.models import User
from app.common.errors import ApiError

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def create_user(email: str, password: str, role: str = "user") -> User:
    email_n = normalize_email(email)
    if not email_n or not password:
        raise ApiError("Email & password required.", 400, "validation_error")

    user = User(email=email_n, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Email already registered.", 409, "conflict")
    return user

def authenticate_user(email: str, password: str) -> User:
    email_n = normalize_email(email)
    user: User | None = User.query.filter_by(email=email_n).first()
    if not user or not user.check_password(password):
        raise ApiError("Invalid credentials.", 401, "invalid_credentials")
    if not user.is_active:
        raise ApiError("User is deactivated.", 403, "user_inactive")
    return user
