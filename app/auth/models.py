# app/auth/models.py
# cette table sera branchée dans les calbacks à l'étapde JWT
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
from app.extensions import db

class TokenBlocklist(db.Model):
    """
    Stocke les JTI des tokens invalidés (logout, rotation, etc.)
    """
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)  # UUID string provenant du JWT
    token_type = db.Column(db.String(16), nullable=False)  # "access" | "refresh"
    revoked_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
