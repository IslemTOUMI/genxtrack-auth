from sqlalchemy.dialects.postgresql import UUID  # (laisse si tu l'utilises ailleurs)
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

    # --- Helpers (aucun impact schéma) ---
    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None

    @classmethod
    def revoke(cls, jti: str, token_type: str):
        if not cls.is_revoked(jti):
            db.session.add(cls(jti=jti, token_type=token_type))
            db.session.commit()
