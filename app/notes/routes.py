from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from app.notes.models import Note
from app.notes.schemas import NoteIn, NoteOut
from app.common.errors import ApiError
import uuid

bp = Blueprint("notes", __name__)

note_in = NoteIn()
note_out = NoteOut()
note_out_many = NoteOut(many=True)

def _current_user_id() -> uuid.UUID:
    return uuid.UUID(get_jwt_identity())

def _is_admin() -> bool:
    claims = get_jwt() or {}
    return claims.get("role") == "admin"

def _ensure_can_access(note: Note, user_id: uuid.UUID):
    if _is_admin():
        return
    if note.owner_id != user_id:
        raise ApiError(
            "Forbidden: you do not own this note.",
            status_code=403,
            code="forbidden",
            details={"note_id": str(note.id)}
        )

@bp.post("/")
@jwt_required()
def create_note():
    payload = request.get_json(silent=True) or {}
    data = note_in.load(payload)
    owner_id = _current_user_id()
    note = Note(title=data["title"], content=data["content"], owner_id=owner_id)
    db.session.add(note)
    db.session.commit()
    return jsonify(note_out.dump(note)), 201

@bp.get("/")
@jwt_required()
def list_notes():
    user_id = _current_user_id()
    q = db.session.query(Note)
    if not _is_admin():
        q = q.filter(Note.owner_id == user_id)
    # Pagination simple bornée
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", 10))
        per_page = 1 if per_page < 1 else 100 if per_page > 100 else per_page
    except ValueError:
        raise ApiError("Invalid pagination params.", 400, "validation_error")
    total = q.count()
    items = q.order_by(Note.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return jsonify({
        "status": "success",
        "data": note_out_many.dump(items),
        "meta": {"page": page, "per_page": per_page, "total": total}
    }), 200

@bp.get("/<uuid:note_id>")
@jwt_required()
def get_note(note_id):
    note = db.session.get(Note, note_id)
    if not note:
        raise ApiError("Note not found.", 404, "not_found")
    _ensure_can_access(note, _current_user_id())
    return jsonify(note_out.dump(note)), 200

@bp.patch("/<uuid:note_id>")
@jwt_required()
def update_note(note_id):
    note = db.session.get(Note, note_id)
    if not note:
        raise ApiError("Note not found.", 404, "not_found")
    _ensure_can_access(note, _current_user_id())

    payload = request.get_json(silent=True) or {}
    # Validations partielles (autorise subset des champs)
    data = NoteIn(partial=True).load(payload)

    # S'il n'y a aucun champ valide à mettre à jour
    if not data:
        raise ApiError("No updatable fields provided.", 400, "validation_error")

    if "title" in data:
        note.title = data["title"]
    if "content" in data:
        note.content = data["content"]

    db.session.commit()
    # IMPORTANT: toujours retourner quelque chose
    return jsonify(note_out.dump(note)), 200

@bp.delete("/<uuid:note_id>")
@jwt_required()
def delete_note(note_id):
    note = db.session.get(Note, note_id)
    if not note:
        raise ApiError("Note not found.", 404, "not_found")
    _ensure_can_access(note, _current_user_id())

    db.session.delete(note)
    db.session.commit()
    return ("", 204)
