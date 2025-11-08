# test_user_isolation.py
"""
Test script to verify that each user has their own isolated database.
Run this script to create 10 users and verify database isolation.
"""

import requests
import json
import re
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"

def create_user(email, password, security_question, security_answer):
    """Create a new user account"""
    session = requests.Session()
    
    # Sign up
    signup_data = {
        "email": email,
        "password": password,
        "password_confirm": password,
        "security_question": security_question,
        "security_answer": security_answer
    }
    
    response = session.post(f"{BASE_URL}/signup", data=signup_data, allow_redirects=False)
    print(f"Signup for {email}: {response.status_code}")
    
    # Login
    login_data = {
        "email": email,
        "password": password
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"Login for {email}: {response.status_code}")
    
    return session

def create_culture(session, name, cell_line_id):
    """Create a culture for a user"""
    culture_data = {
        "name": name,
        "cell_line_id": str(cell_line_id),
        "start_date": "2024-01-15"
    }
    
    response = session.post(f"{BASE_URL}/culture", data=culture_data, allow_redirects=False)
    print(f"  Created culture '{name}': {response.status_code}")
    return response.status_code == 302

def test_user_isolation():
    """Test that 10 users each have isolated databases"""
    
    security_questions = [
        "What was the name of your first pet?",
        "In what city were you born?",
        "What is the name of your favorite teacher?",
        "What was the model of your first car?"
    ]
    
    users = []
    for i in range(1, 11):
        email = f"user{i}@test.com"
        password = f"password{i}"
        security_q = security_questions[i % 4]
        security_a = f"answer{i}"
        
        print(f"\n=== Creating User {i}: {email} ===")
        session = create_user(email, password, security_q, security_a)
        users.append((email, session))
        
        # Create a culture for this user
        culture_name = f"Culture-User{i}"
        create_culture(session, culture_name, 1)  # Assuming cell_line_id 1 exists
    
    # Verify isolation: Check that each user only sees their own culture
    print("\n=== Verifying User Isolation ===")
    for email, session in users:
        response = session.get(f"{BASE_URL}/")
        if response.status_code == 200:
            content = response.text
            user_num = email.split("@")[0].replace("user", "")
            expected_culture = f"Culture-User{user_num}"

            # Collect all distinct culture names shown on the page.
            visible_cultures = set(re.findall(r"Culture-User\d+", content))

            if expected_culture in visible_cultures:
                print(f"✓ {email} sees their own culture: {expected_culture}")
            else:
                print(f"✗ {email} does NOT see their own culture!")

            # Remove the expected culture and check for any remaining matches.
            visible_cultures.discard(expected_culture)
            if visible_cultures:
                print(f"✗ {email} sees other users' cultures: {sorted(visible_cultures)}")
            else:
                print(f"✓ {email} does NOT see other users' cultures")
        else:
            print(f"✗ {email} failed to access index: {response.status_code}")
    
    # Check database files
    print("\n=== Checking Database Files ===")
    app_root = Path(__file__).parent
    for i in range(1, 11):
        db_file = app_root / f"user_{i}.db"
        if db_file.exists():
            size = db_file.stat().st_size
            print(f"✓ user_{i}.db exists ({size} bytes)")
        else:
            print(f"✗ user_{i}.db does NOT exist!")

if __name__ == "__main__":
    print("Starting user isolation test...")
    print("Make sure your Flask server is running on http://127.0.0.1:5000")
    input("Press Enter to continue...")
    test_user_isolation()
    print("\n=== Test Complete ===")