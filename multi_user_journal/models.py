"""Database models."""
from __future__ import annotations

from datetime import datetime

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .security import UserMixin


class User(UserMixin, db.Model):
    """
    User model with secure password storage and password reset functionality.
    
    Uses werkzeug.security for password hashing (PBKDF2).
    Supports email-based password reset with time-limited tokens.
    Includes optional security question for password reset fallback.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    security_question = db.Column(db.String(255), nullable=True)
    security_answer_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    journal_entries = db.relationship(
        "JournalEntry", back_populates="owner", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """
        Hash and set password using werkzeug.security (PBKDF2).
        
        This uses PBKDF2 with SHA-256, which is secure for production deployments.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def set_security_answer(self, answer: str) -> None:
        """
        Hash and set security question answer.
        
        Answers are normalized (lowercase, stripped) before hashing to allow
        case-insensitive matching.
        """
        normalized = answer.strip().lower()
        self.security_answer_hash = generate_password_hash(normalized)

    def verify_security_answer(self, answer: str) -> bool:
        """Verify security question answer (case-insensitive)."""
        if not self.security_answer_hash:
            return False
        normalized = answer.strip().lower()
        return check_password_hash(self.security_answer_hash, normalized)

    def generate_reset_token(self) -> str:
        """
        Generate a time-limited password reset token.
        
        Uses itsdangerous.URLSafeTimedSerializer for secure token generation.
        Token expiration is controlled by PASSWORD_RESET_TOKEN_MAX_AGE config.
        """
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=current_app.config["SECURITY_PASSWORD_SALT"],
        )
        return serializer.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token: str, max_age: int | None = None) -> "User | None":
        """
        Verify and decode a password reset token.
        
        Returns the User if token is valid and not expired, None otherwise.
        
        Args:
            token: The reset token to verify
            max_age: Optional override for token max age (seconds)
        
        Returns:
            User instance if token is valid, None if invalid or expired
        """
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=current_app.config["SECURITY_PASSWORD_SALT"],
        )
        max_age = max_age or current_app.config["PASSWORD_RESET_TOKEN_MAX_AGE"]
        try:
            data = serializer.loads(token, max_age=max_age)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        user_id = data.get("user_id")
        if user_id is None:
            return None
        return User.query.get(user_id)


class JournalEntry(db.Model):
    """
    Journal entry model with user ownership.
    
    Each entry belongs to a single user (one-to-many relationship).
    All queries should filter by user_id to ensure data isolation.
    """
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner = db.relationship("User", back_populates="journal_entries")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Load user by ID for Flask-Login or custom session management."""
    return User.query.get(int(user_id))





