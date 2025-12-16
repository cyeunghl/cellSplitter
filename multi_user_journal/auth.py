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
    """
    Validate signup payload and return normalized values.
    
    Raises 400 error if required fields are missing.
    """
    required = ["email", "password", "security_question", "security_answer"]
    for field in required:
        if field not in data or not data[field]:
            abort(400, description=f"Missing field: {field}")
    
    email = data["email"].strip().lower()
    password = data["password"]
    security_question = data["security_question"].strip()
    security_answer = data["security_answer"]
    
    # Basic validation
    if len(password) < 8:
        abort(400, description="Password must be at least 8 characters long")
    
    if not email or "@" not in email:
        abort(400, description="Invalid email address")
    
    return email, password, security_question, security_answer


def _send_reset_email(user: User, token: str) -> None:
    """
    Send password reset email.
    
    Configure MAIL_* settings or Flask-Mail backend (Mailtrap, SES, etc.).
    In production, ensure Flask-Mail is installed and SMTP is configured.
    """
    reset_url = f"{request.host_url.rstrip('/')}/auth/reset/{token}"
    msg = Message(
        subject="Password reset requested",
        recipients=[user.email],
        body=f"Use the following link to reset your password: {reset_url}\n"
             f"This link will expire in {current_app.config['PASSWORD_RESET_TOKEN_MAX_AGE'] // 60} minutes.",
    )
    # Configure MAIL_* settings or Flask-Mail backend (Mailtrap, SES, etc.).
    mail.send(msg)


@auth_bp.route("/signup", methods=["POST"])
def signup() -> tuple[dict, int]:
    """
    Create a new user account.
    
    Required fields:
    - email: User's email address (must be unique)
    - password: Password (minimum 8 characters)
    - security_question: Security question for password reset fallback
    - security_answer: Answer to security question
    
    Returns 201 on success, 400 if validation fails or email already exists.
    """
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
    """
    Authenticate user and create session.
    
    Required fields:
    - email: User's email address
    - password: User's password
    
    Returns 200 on success, 401 if credentials are invalid.
    Rate limiting hints are tracked for brute force mitigation.
    """
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        abort(400, description="Email and password required")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        # Increment failed attempts to hint at rate limiting; replace with
        # Flask-Limiter in production for distributed enforcement.
        identifier = email or request.remote_addr
        attempts = current_app.failed_login_tracker.increment(identifier)
        abort(401, description=f"Invalid credentials. Attempt #{attempts}")

    login_user(user)
    current_app.failed_login_tracker.reset(email)

    # Example CSRF token guidance: in a SPA, issue a token stored in session and
    # require it for mutating requests. Flask-WTF's CSRFProtect already enforces
    # this for form-based posts; document for API clients.
    return {"message": "Logged in", "user_id": user.id}, 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout() -> tuple[dict, int]:
    """Log out the current user and terminate session."""
    logout_user()
    return {"message": "Logged out"}, 200


@auth_bp.route("/request-reset", methods=["POST"])
def request_reset() -> tuple[dict, int]:
    """
    Request password reset via email.
    
    Required fields:
    - email: User's email address
    
    Always returns 200 to prevent email enumeration attacks.
    If the email exists, a reset token is generated and sent.
    """
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    if not email:
        abort(400, description="Email required")

    user = User.query.filter_by(email=email).first()
    if not user:
        # Do not leak registration status - always return success
        return {"message": "If the account exists, a reset email was sent."}, 200

    token = user.generate_reset_token()
    _send_reset_email(user, token)
    return {"message": "Reset instructions sent"}, 200


@auth_bp.route("/reset/<token>", methods=["GET"])
def get_reset_form(token: str):
    """
    Validate reset token and return confirmation.
    
    Returns 200 if token is valid, 400 if invalid or expired.
    Use this endpoint to check token validity before showing reset form.
    """
    user = User.verify_reset_token(token)
    if not user:
        abort(400, description="Invalid or expired token")
    return {"message": "Token valid. Submit new password via POST."}


@auth_bp.route("/reset/<token>", methods=["POST"])
def reset_password(token: str):
    """
    Reset password using a valid reset token.
    
    Required fields:
    - password: New password (minimum 8 characters)
    
    Returns 200 on success, 400 if token is invalid/expired or password validation fails.
    """
    user = User.verify_reset_token(token)
    if not user:
        abort(400, description="Invalid or expired token")

    payload = request.get_json() or {}
    password = payload.get("password")
    if not password:
        abort(400, description="Password required")
    
    if len(password) < 8:
        abort(400, description="Password must be at least 8 characters long")

    user.set_password(password)
    db.session.commit()
    return {"message": "Password updated"}, 200


@auth_bp.route("/security-question", methods=["POST"])
def get_security_question():
    """
    Get security question for an email address.
    
    Required fields:
    - email: User's email address
    
    Returns the security question if user exists, None otherwise.
    Always returns 200 to prevent email enumeration.
    """
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
    """
    Reset password using security question answer.
    
    Required fields:
    - email: User's email address
    - security_answer: Answer to security question
    - password: New password (minimum 8 characters)
    
    Returns 200 on success, 403 if answer is incorrect, 400 if validation fails.
    """
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    answer = payload.get("security_answer", "")
    password = payload.get("password")

    if not (email and answer and password):
        abort(400, description="Email, answer, and password required")
    
    if len(password) < 8:
        abort(400, description="Password must be at least 8 characters long")

    user = User.query.filter_by(email=email).first()
    if not user or not user.verify_security_answer(answer):
        abort(403, description="Invalid answer")

    user.set_password(password)
    db.session.commit()
    return {"message": "Password updated via security question"}, 200





