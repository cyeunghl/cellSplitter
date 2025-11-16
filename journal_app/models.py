"""Database models."""
from __future__ import annotations

from datetime import datetime

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .security import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    security_question = db.Column(db.String(255), nullable=False)
    security_answer_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    journal_entries = db.relationship("JournalEntry", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def set_security_answer(self, answer: str) -> None:
        self.security_answer_hash = generate_password_hash(answer.strip().lower())

    def verify_security_answer(self, answer: str) -> bool:
        normalized = answer.strip().lower()
        return check_password_hash(self.security_answer_hash, normalized)

    def generate_reset_token(self) -> str:
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=current_app.config["SECURITY_PASSWORD_SALT"],
        )
        return serializer.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token: str, max_age: int | None = None) -> "User | None":
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
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", back_populates="journal_entries")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return User.query.get(int(user_id))
