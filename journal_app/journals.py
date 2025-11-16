"""Journal entry endpoints."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, jsonify, request

from .extensions import db
from .models import JournalEntry
from .security import current_user, login_required


journal_bp = Blueprint("journals", __name__)


def owner_required(func):
    """Ensure the current user owns the target journal entry."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        entry_id = kwargs.get("entry_id")
        if entry_id is None:
            abort(400, description="Entry id required")
        entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first()
        if not entry:
            abort(403, description="Forbidden")
        return func(entry, *args, **kwargs)

    return wrapper


@journal_bp.route("/", methods=["GET"])
@login_required
def list_entries():
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).all()
    return {
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in entries
        ]
    }


@journal_bp.route("/", methods=["POST"])
@login_required
def create_entry():
    payload = request.get_json() or {}
    title = payload.get("title")
    content = payload.get("content")
    if not title or not content:
        abort(400, description="Title and content required")
    entry = JournalEntry(title=title, content=content, owner=current_user)
    db.session.add(entry)
    db.session.commit()
    return {"id": entry.id, "message": "Created"}, 201


@journal_bp.route("/<int:entry_id>", methods=["GET"])
@login_required
@owner_required
def get_entry(entry: JournalEntry, entry_id: int):
    return {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


@journal_bp.route("/<int:entry_id>", methods=["PUT"])
@login_required
@owner_required
def update_entry(entry: JournalEntry, entry_id: int):
    payload = request.get_json() or {}
    title = payload.get("title")
    content = payload.get("content")
    if title:
        entry.title = title
    if content:
        entry.content = content
    db.session.commit()
    return {"message": "Updated"}


@journal_bp.route("/<int:entry_id>", methods=["DELETE"])
@login_required
@owner_required
def delete_entry(entry: JournalEntry, entry_id: int):
    db.session.delete(entry)
    db.session.commit()
    return {"message": "Deleted"}, 204
