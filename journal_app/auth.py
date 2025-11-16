"""Authentication blueprint."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, request
try:  # pragma: no cover - prefer real Flask-Mail
    from flask_mail import Message  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from .stubs.mail import Message

from .extensions import db, mail
from .models import User
from .security import current_user, login_required, login_user, logout_user


auth_bp = Blueprint("auth", __name__)


def _validate_signup_payload(data: dict) -> tuple[str, str, str, str]:
    required = ["email", "password", "security_question", "security_answer"]
    for field in required:
        if field not in data or not data[field]:
            abort(400, description=f"Missing field: {field}")
    return (
        data["email"].strip().lower(),
        data["password"],
        data["security_question"].strip(),
        data["security_answer"],
    )


def _send_reset_email(user: User, token: str) -> None:
    reset_url = f"{request.host_url.rstrip('/')}/auth/reset/{token}"
    msg = Message(
        subject="Password reset requested",
        recipients=[user.email],
        body=f"Use the following link to reset your password: {reset_url}\n",
    )
    # Configure MAIL_* settings or Flask-Mail backend (Mailtrap, SES, etc.).
    mail.send(msg)


@auth_bp.route("/signup", methods=["POST"])
def signup() -> tuple[dict, int]:
    payload = request.get_json() or {}
    email, password, question, answer = _validate_signup_payload(payload)

    if User.query.filter_by(email=email).first():
        abort(400, description="Email already registered")

    user = User(email=email, security_question=question)
    user.set_password(password)
    user.set_security_answer(answer)

    db.session.add(user)
    db.session.commit()

    return {"message": "Account created"}, 201


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple[dict, int]:
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        # Increment failed attempts to hint at rate limiting; replace with
        # Flask-Limiter in production for distributed enforcement.
        attempts = current_app.failed_login_tracker.increment(email or request.remote_addr)
        abort(401, description=f"Invalid credentials. Attempt #{attempts}")

    login_user(user)
    current_app.failed_login_tracker.reset(email)

    # Example CSRF token guidance: in a SPA, issue a token stored in session and
    # require it for mutating requests. Flask-WTF's CSRFProtect already enforces
    # this for form-based posts; document for API clients.
    return {"message": "Logged in"}, 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout() -> tuple[dict, int]:
    logout_user()
    return {"message": "Logged out"}, 200


@auth_bp.route("/request-reset", methods=["POST"])
def request_reset() -> tuple[dict, int]:
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    if not email:
        abort(400, description="Email required")

    user = User.query.filter_by(email=email).first()
    if not user:
        # Do not leak registration status.
        return {"message": "If the account exists, a reset email was sent."}, 200

    token = user.generate_reset_token()
    _send_reset_email(user, token)
    return {"message": "Reset instructions sent"}, 200


@auth_bp.route("/reset/<token>", methods=["GET"])
def get_reset_form(token: str):
    user = User.verify_reset_token(token)
    if not user:
        abort(400, description="Invalid or expired token")
    return {"message": "Token valid. Submit new password via POST."}


@auth_bp.route("/reset/<token>", methods=["POST"])
def reset_password(token: str):
    user = User.verify_reset_token(token)
    if not user:
        abort(400, description="Invalid or expired token")

    payload = request.get_json() or {}
    password = payload.get("password")
    if not password:
        abort(400, description="Password required")

    user.set_password(password)
    db.session.commit()
    return {"message": "Password updated"}


@auth_bp.route("/security-question", methods=["POST"])
def get_security_question():
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    if not email:
        abort(400, description="Email required")

    user = User.query.filter_by(email=email).first()
    if not user:
        return {"question": None}, 200
    return {"question": user.security_question}, 200


@auth_bp.route("/reset-with-security", methods=["POST"])
def reset_with_security_answer():
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    answer = payload.get("security_answer", "")
    password = payload.get("password")

    if not (email and answer and password):
        abort(400, description="Email, answer, and password required")

    user = User.query.filter_by(email=email).first()
    if not user or not user.verify_security_answer(answer):
        abort(403, description="Invalid answer")

    user.set_password(password)
    db.session.commit()
    return {"message": "Password updated via security question"}, 200
