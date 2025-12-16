#!/usr/bin/env python3
"""
Automated regression script to exercise multi-user isolation in the cellSplitter app.

The script provisions two fresh user accounts per run, creates cultures for the first
user, and checks whether the second user can see or access those cultures.  It uses
the public HTTP interface of a running server, so point `--base-url` at whichever
environment you want to probe (local dev, staging, etc.).

Requirements:
  pip install requests beautifulsoup4

Typical use:
  python multi_user_isolation_tester.py --base-url http://127.0.0.1:5000 --iterations 5
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup  # type: ignore


SECURITY_QUESTION = "What is your favorite color?"
SECURITY_ANSWER = "blue"


@dataclass
class UserContext:
    session: requests.Session
    email: str
    password: str
    cultures: list[tuple[str, Optional[int]]]


def signup(base_url: str, user: UserContext) -> None:
    resp = user.session.get(f"{base_url}/signup")
    resp.raise_for_status()

    payload = {
        "email": user.email,
        "password": user.password,
        "password_confirm": user.password,
        "security_question": SECURITY_QUESTION,
        "security_answer": SECURITY_ANSWER,
    }
    resp = user.session.post(f"{base_url}/signup", data=payload, allow_redirects=True)
    if resp.status_code not in {200, 302}:
        raise RuntimeError(f"Signup failed for {user.email}: status {resp.status_code}")


def login(base_url: str, user: UserContext) -> None:
    resp = user.session.get(f"{base_url}/login")
    resp.raise_for_status()

    payload = {
        "email": user.email,
        "password": user.password,
    }
    resp = user.session.post(f"{base_url}/login", data=payload, allow_redirects=True)
    if "Invalid email or password" in resp.text:
        raise RuntimeError(f"Login failed for {user.email}")


def fetch_default_cell_line_id(base_url: str, user: UserContext) -> int:
    resp = user.session.get(f"{base_url}/api/doubling-times")
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError("No cell lines available to seed cultures.")
    return int(data[0]["id"])


def create_culture(
    base_url: str,
    user: UserContext,
    culture_name: str,
    cell_line_id: int,
) -> int:
    payload = {
        "name": culture_name,
        "cell_line_id": str(cell_line_id),
        "start_date": date.today().isoformat(),
        "initial_passage_number": "1",
        "initial_media": "DMEM + 10% FBS",
        "initial_notes": "Automated test culture",
    }
    resp = user.session.post(
        f"{base_url}/culture", data=payload, allow_redirects=True
    )
    if resp.status_code not in {200, 302}:
        raise RuntimeError(
            f"Failed to create culture '{culture_name}' for {user.email}: "
            f"status {resp.status_code}"
        )

    # After following redirects we should be on /culture/<id>
    culture_id = extract_culture_id(resp.url)
    user.cultures.append((culture_name, culture_id))
    return culture_id


def extract_culture_id(url: str) -> int:
    match = re.search(r"/culture/(\d+)", url)
    if not match:
        raise RuntimeError(f"Could not extract culture id from URL: {url!r}")
    return int(match.group(1))


def fetch_dashboard_html(base_url: str, user: UserContext) -> str:
    resp = user.session.get(f"{base_url}/", allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def culture_visible(html: str, culture_name: str) -> bool:
    return culture_name in html


def can_access_culture_detail(
    base_url: str, user: UserContext, culture_id: int
) -> bool:
    resp = user.session.get(f"{base_url}/culture/{culture_id}")
    # Depending on auth, we may get redirect to login (302 -> /login) or 404.
    if resp.status_code == 404:
        return False
    if resp.status_code in {302, 401}:
        return False
    if "Please log in" in resp.text and resp.url.endswith("/login"):
        return False
    return True


def summarize(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    for strong in soup.select("table.cultures-table strong"):
        names.append(strong.text.strip())
    return names


def run_iteration(base_url: str, iteration: int) -> bool:
    user1 = UserContext(
        session=requests.Session(),
        email=f"user{iteration}_one_{uuid.uuid4().hex[:8]}@example.com",
        password="Automation123!",
        cultures=[],
    )
    user2 = UserContext(
        session=requests.Session(),
        email=f"user{iteration}_two_{uuid.uuid4().hex[:8]}@example.com",
        password="Automation123!",
        cultures=[],
    )

    signup(base_url, user1)
    signup(base_url, user2)
    login(base_url, user1)
    login(base_url, user2)

    cell_line_id = fetch_default_cell_line_id(base_url, user1)
    culture_name = f"AutomationCulture_{iteration}"
    culture_id = create_culture(base_url, user1, culture_name, cell_line_id)

    user1_dashboard = fetch_dashboard_html(base_url, user1)
    if not culture_visible(user1_dashboard, culture_name):
        print(f"[FAIL] User1 could not see their own culture {culture_name}", file=sys.stderr)
        return False

    user2_dashboard = fetch_dashboard_html(base_url, user2)
    if culture_visible(user2_dashboard, culture_name):
        print(
            f"[FAIL] User2 dashboard exposes User1 culture '{culture_name}'.",
            file=sys.stderr,
        )
        print("        Visible cultures for User2:", summarize(user2_dashboard))
        return False

    if can_access_culture_detail(base_url, user2, culture_id):
        print(
            f"[FAIL] User2 could open detail page for User1 culture ID {culture_id}.",
            file=sys.stderr,
        )
        return False

    print(f"[PASS] Iteration {iteration}: isolation checks passed.")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exercise multi-user isolation behaviours in cellSplitter."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Root URL of a running cellSplitter instance (e.g. http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="How many independent user pairs to spin up (default: 1).",
    )
    parser.add_argument(
        "--stop-on-fail",
        action="store_true",
        help="Abort after the first failing iteration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    failures = 0
    for i in range(1, args.iterations + 1):
        ok = run_iteration(base_url, i)
        if not ok:
            failures += 1
            if args.stop_on_fail:
                break
    if failures:
        print(f"\nCompleted with {failures} failing iteration(s).", file=sys.stderr)
        return 1
    print(f"\nAll {args.iterations} iteration(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

