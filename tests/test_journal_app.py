from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from journal_app import create_app
from journal_app.config import TestingConfig
from journal_app.extensions import db
from journal_app.models import JournalEntry, User


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mail_outbox(monkeypatch):
    sent_messages = []

    def fake_send(message):
        sent_messages.append(message)

    monkeypatch.setattr("journal_app.auth.mail.send", fake_send)
    return sent_messages


@pytest.fixture
def seeded_users(app):
    with app.app_context():
        user_a = User(email="alice@example.com", security_question="Pet?" )
        user_a.set_password("alicepass")
        user_a.set_security_answer("fluffy")

        user_b = User(email="bob@example.com", security_question="Color?")
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
            "entry_b1_id": entry_b1.id,
        }


def login(client, email, password):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def get_user(app, user_id: int) -> User:
    with app.app_context():
        return User.query.get(user_id)


def test_user_can_only_see_their_entries(client, seeded_users):
    login(client, "alice@example.com", "alicepass")
    resp = client.get("/journals/")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert len(payload["entries"]) == 2
    assert all(entry["title"].startswith("A") for entry in payload["entries"])

    # Accessing Bob's entry should return 403.
    resp = client.get(f"/journals/{seeded_users['entry_b1_id']}")
    assert resp.status_code == 403


def test_user_cannot_update_or_delete_foreign_entries(client, seeded_users):
    login(client, "alice@example.com", "alicepass")
    target_id = seeded_users["entry_b1_id"]
    resp = client.put(f"/journals/{target_id}", json={"title": "Hacked"})
    assert resp.status_code == 403
    resp = client.delete(f"/journals/{target_id}")
    assert resp.status_code == 403


def test_password_reset_token_flow(app, client, seeded_users, mail_outbox):
    user = get_user(app, seeded_users["user_a"]["id"])
    # Trigger email send.
    resp = client.post("/auth/request-reset", json={"email": user.email})
    assert resp.status_code == 200
    assert len(mail_outbox) == 1

    token = user.generate_reset_token()
    resp = client.post(f"/auth/reset/{token}", json={"password": "newpass"})
    assert resp.status_code == 200
    with app.app_context():
        refreshed = User.query.filter_by(email=user.email).first()
        assert refreshed.check_password("newpass")


def test_security_question_reset_flow(app, client, seeded_users):
    user = get_user(app, seeded_users["user_b"]["id"])
    resp = client.post(
        "/auth/reset-with-security",
        json={
            "email": user.email,
            "security_answer": "blue",
            "password": "bobnew",
        },
    )
    assert resp.status_code == 200
    with app.app_context():
        refreshed = User.query.filter_by(email=user.email).first()
        assert refreshed.check_password("bobnew")


def test_rate_limiting_counter_increments(app, client, seeded_users):
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert app.failed_login_tracker.get_attempts("alice@example.com") == 1


def test_reset_token_expiration(client, app, seeded_users):
    app.config["PASSWORD_RESET_TOKEN_MAX_AGE"] = -1
    user = get_user(app, seeded_users["user_a"]["id"])
    token = user.generate_reset_token()
    resp = client.post(f"/auth/reset/{token}", json={"password": "late"})
    assert resp.status_code == 400


def test_security_question_endpoint_hides_nonexistent_user(client):
    resp = client.post("/auth/security-question", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.get_json()["question"] is None
