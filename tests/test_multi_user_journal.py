"""Comprehensive test suite for multi-user journal app."""
from __future__ import annotations

import os
import sys
import time

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from multi_user_journal import create_app
from multi_user_journal.config import TestingConfig
from multi_user_journal.extensions import db
from multi_user_journal.models import JournalEntry, User


@pytest.fixture
def app():
    """Create application instance for testing."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mail_outbox(monkeypatch):
    """Mock Flask-Mail to capture sent messages."""
    sent_messages = []

    def fake_send(message):
        sent_messages.append(message)

    monkeypatch.setattr("multi_user_journal.auth.mail.send", fake_send)
    return sent_messages


@pytest.fixture
def seeded_users(app):
    """Create test users and journal entries."""
    with app.app_context():
        user_a = User(email="alice@example.com", security_question="What is your pet's name?")
        user_a.set_password("alicepass")
        user_a.set_security_answer("fluffy")

        user_b = User(email="bob@example.com", security_question="What is your favorite color?")
        user_b.set_password("bobpass")
        user_b.set_security_answer("blue")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        entry_a1 = JournalEntry(title="A1", content="Entry 1", owner=user_a)
        entry_a2 = JournalEntry(title="A2", content="Entry 2", owner=user_a)
        entry_b1 = JournalEntry(title="B1", content="Entry B", owner=user_b)
        db.session.add_all([entry_a1, entry_a2, entry_b1])
        db.session.commit()

        return {
            "user_a": {"id": user_a.id, "email": user_a.email},
            "user_b": {"id": user_b.id, "email": user_b.email},
            "entry_a1_id": entry_a1.id,
            "entry_a2_id": entry_a2.id,
            "entry_b1_id": entry_b1.id,
        }


def login(client, email, password):
    """Helper function to log in a user."""
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def get_user(app, user_id: int) -> User:
    """Helper function to get a user by ID."""
    with app.app_context():
        return User.query.get(user_id)


def test_user_can_only_see_their_entries(client, seeded_users):
    """Test that user A can only see their own entries."""
    # Login as user A
    resp = login(client, "alice@example.com", "alicepass")
    assert resp.status_code == 200

    # Get entries - should only see user A's entries
    resp = client.get("/journals/")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert len(payload["entries"]) == 2
    assert all(entry["title"].startswith("A") for entry in payload["entries"])

    # Accessing Bob's entry should return 403
    resp = client.get(f"/journals/{seeded_users['entry_b1_id']}")
    assert resp.status_code == 403


def test_user_cannot_update_or_delete_foreign_entries(client, seeded_users):
    """Test that user A cannot update or delete user B's entries."""
    # Login as user A
    login(client, "alice@example.com", "alicepass")
    
    target_id = seeded_users["entry_b1_id"]
    
    # Try to update Bob's entry
    resp = client.put(f"/journals/{target_id}", json={"title": "Hacked"})
    assert resp.status_code == 403
    
    # Try to delete Bob's entry
    resp = client.delete(f"/journals/{target_id}")
    assert resp.status_code == 403


def test_password_reset_token_flow(app, client, seeded_users, mail_outbox):
    """Test password reset via email token."""
    user = get_user(app, seeded_users["user_a"]["id"])
    
    # Request password reset
    resp = client.post("/auth/request-reset", json={"email": user.email})
    assert resp.status_code == 200
    assert len(mail_outbox) == 1
    
    # Generate token and reset password (need app context for token generation)
    with app.app_context():
        token = user.generate_reset_token()
    resp = client.post(f"/auth/reset/{token}", json={"password": "newpassword"})
    assert resp.status_code == 200
    
    # Verify password was changed
    with app.app_context():
        refreshed = User.query.filter_by(email=user.email).first()
        assert refreshed.check_password("newpassword")
        assert not refreshed.check_password("alicepass")


def test_security_question_reset_flow(app, client, seeded_users):
    """Test password reset via security question."""
    user = get_user(app, seeded_users["user_b"]["id"])
    
    # Reset password using security question
    resp = client.post(
        "/auth/reset-with-security",
        json={
            "email": user.email,
            "security_answer": "blue",
            "password": "bobnewpass",
        },
    )
    assert resp.status_code == 200
    
    # Verify password was changed
    with app.app_context():
        refreshed = User.query.filter_by(email=user.email).first()
        assert refreshed.check_password("bobnewpass")
        assert not refreshed.check_password("bobpass")


def test_rate_limiting_counter_increments(app, client, seeded_users):
    """Test that failed login attempts increment the rate limiting counter."""
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert app.failed_login_tracker.get_attempts("alice@example.com") == 1


def test_reset_token_expiration(client, app, seeded_users):
    """Test that expired tokens are rejected."""
    # Set very short token expiration
    app.config["PASSWORD_RESET_TOKEN_MAX_AGE"] = -1
    
    user = get_user(app, seeded_users["user_a"]["id"])
    with app.app_context():
        token = user.generate_reset_token()
    
    # Try to use expired token
    resp = client.post(f"/auth/reset/{token}", json={"password": "late"})
    assert resp.status_code == 400


def test_security_question_endpoint_hides_nonexistent_user(client):
    """Test that security question endpoint doesn't leak user existence."""
    resp = client.post("/auth/security-question", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.get_json()["question"] is None


def test_signup_creates_user(client):
    """Test user signup."""
    resp = client.post(
        "/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "security_question": "Test question?",
            "security_answer": "test answer",
        },
    )
    assert resp.status_code == 201


def test_signup_rejects_duplicate_email(client, seeded_users):
    """Test that signup rejects duplicate emails."""
    resp = client.post(
        "/auth/signup",
        json={
            "email": "alice@example.com",
            "password": "password123",
            "security_question": "Test question?",
            "security_answer": "test answer",
        },
    )
    assert resp.status_code == 400


def test_login_requires_authentication(client):
    """Test that journal endpoints require authentication."""
    resp = client.get("/journals/")
    assert resp.status_code == 401


def test_create_entry_associates_with_user(client, seeded_users):
    """Test that created entries are associated with the current user."""
    login(client, "alice@example.com", "alicepass")
    
    resp = client.post(
        "/journals/",
        json={"title": "New Entry", "content": "New content"},
    )
    assert resp.status_code == 201
    
    # Verify entry belongs to user A
    resp = client.get("/journals/")
    payload = resp.get_json()
    assert len(payload["entries"]) == 3
    assert any(entry["title"] == "New Entry" for entry in payload["entries"])


def test_update_entry(client, seeded_users):
    """Test updating a journal entry."""
    login(client, "alice@example.com", "alicepass")
    
    entry_id = seeded_users["entry_a1_id"]
    resp = client.put(
        f"/journals/{entry_id}",
        json={"title": "Updated Title", "content": "Updated Content"},
    )
    assert resp.status_code == 200
    
    # Verify update
    resp = client.get(f"/journals/{entry_id}")
    payload = resp.get_json()
    assert payload["title"] == "Updated Title"
    assert payload["content"] == "Updated Content"


def test_delete_entry(client, seeded_users):
    """Test deleting a journal entry."""
    login(client, "alice@example.com", "alicepass")
    
    entry_id = seeded_users["entry_a1_id"]
    resp = client.delete(f"/journals/{entry_id}")
    assert resp.status_code == 204
    
    # Verify deletion
    resp = client.get(f"/journals/{entry_id}")
    assert resp.status_code == 403


def test_reset_token_validation(client, app, seeded_users):
    """Test that reset token validation endpoint works."""
    user = get_user(app, seeded_users["user_a"]["id"])
    with app.app_context():
        token = user.generate_reset_token()
    
    # Validate token
    resp = client.get(f"/auth/reset/{token}")
    assert resp.status_code == 200
    assert "valid" in resp.get_json()["message"].lower()


def test_security_question_case_insensitive(app, client, seeded_users):
    """Test that security question answers are case-insensitive."""
    user = get_user(app, seeded_users["user_b"]["id"])
    
    # Try with different case
    resp = client.post(
        "/auth/reset-with-security",
        json={
            "email": "bob@example.com",
            "security_answer": "BLUE",  # uppercase
            "password": "bobnewpass2",
        },
    )
    assert resp.status_code == 200


def test_password_minimum_length(client):
    """Test that passwords must be at least 8 characters."""
    resp = client.post(
        "/auth/signup",
        json={
            "email": "shortpass@example.com",
            "password": "short",  # too short
            "security_question": "Test?",
            "security_answer": "answer",
        },
    )
    assert resp.status_code == 400

