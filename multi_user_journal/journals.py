"""Journal entry endpoints with per-user data isolation."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, jsonify, request

from .extensions import db
from .models import JournalEntry
from .security import current_user, login_required


journal_bp = Blueprint("journals", __name__)


def owner_required(func):
    """
    Decorator to ensure the current user owns the target journal entry.
    
    This decorator:
    1. Extracts entry_id from route parameters
    2. Queries the entry filtered by both id and current_user.id
    3. Returns 403 if entry doesn't exist or user doesn't own it
    4. Passes the entry object to the decorated function
    
    Usage:
        @journal_bp.route("/<int:entry_id>", methods=["GET"])
        @login_required
        @owner_required
        def get_entry(entry: JournalEntry, entry_id: int):
            # entry is guaranteed to belong to current_user
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        entry_id = kwargs.get("entry_id")
        if entry_id is None:
            abort(400, description="Entry id required")
        
        # Critical: Filter by both entry_id AND current_user.id for data isolation
        entry = JournalEntry.query.filter_by(
            id=entry_id, user_id=current_user.id
        ).first()
        
        if not entry:
            abort(403, description="Forbidden")
        
        # Replace entry_id with entry object in kwargs
        kwargs["entry"] = entry
        return func(*args, **kwargs)

    return wrapper


@journal_bp.route("/", methods=["GET"])
@login_required
def list_entries():
    """
    List all journal entries for the current user.
    
    Returns entries ordered by creation date (newest first).
    Only entries owned by the current user are returned.
    """
    # Critical: Always filter by current_user.id for data isolation
    entries = (
        JournalEntry.query.filter_by(user_id=current_user.id)
        .order_by(JournalEntry.created_at.desc())
        .all()
    )
    return jsonify({
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
    })


@journal_bp.route("/", methods=["POST"])
@login_required
def create_entry():
    """
    Create a new journal entry.
    
    Required fields:
    - title: Entry title
    - content: Entry content
    
    The entry is automatically associated with the current user.
    Returns 201 with the created entry ID.
    """
    payload = request.get_json() or {}
    title = payload.get("title")
    content = payload.get("content")
    
    if not title or not content:
        abort(400, description="Title and content required")
    
    # Critical: Associate entry with current_user.id
    entry = JournalEntry(title=title, content=content, owner=current_user)
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({"id": entry.id, "message": "Created"}), 201


@journal_bp.route("/<int:entry_id>", methods=["GET"])
@login_required
@owner_required
def get_entry(entry: JournalEntry, entry_id: int):
    """
    Get a single journal entry by ID.
    
    Returns 200 with entry data if user owns the entry, 403 otherwise.
    The @owner_required decorator ensures only the owner can access the entry.
    """
    return jsonify({
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    })


@journal_bp.route("/<int:entry_id>", methods=["PUT"])
@login_required
@owner_required
def update_entry(entry: JournalEntry, entry_id: int):
    """
    Update a journal entry.
    
    Optional fields:
    - title: New title (if provided)
    - content: New content (if provided)
    
    Returns 200 on success, 403 if user doesn't own the entry.
    The @owner_required decorator ensures only the owner can update the entry.
    """
    payload = request.get_json() or {}
    title = payload.get("title")
    content = payload.get("content")
    
    if title:
        entry.title = title
    if content:
        entry.content = content
    
    db.session.commit()
    return jsonify({"message": "Updated"})


@journal_bp.route("/<int:entry_id>", methods=["DELETE"])
@login_required
@owner_required
def delete_entry(entry: JournalEntry, entry_id: int):
    """
    Delete a journal entry.
    
    Returns 204 on success, 403 if user doesn't own the entry.
    The @owner_required decorator ensures only the owner can delete the entry.
    """
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 204





