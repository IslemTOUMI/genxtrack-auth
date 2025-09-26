import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
from passlib.hash import bcrypt
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # roles simples: "user" | "admin"
    role = db.Column(db.String(32), nullable=False, default="user", index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relation vers Note
    notes = db.relationship("Note", back_populates="owner", lazy="selectin")

    # helpers mot de passe
    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.verify(raw_password, self.password_hash)
