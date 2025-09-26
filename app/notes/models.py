import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, ForeignKey
from app.extensions import db

class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    owner_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = db.relationship("User", back_populates="notes", lazy="joined")

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
