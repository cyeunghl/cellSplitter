"""
Vercel serverless function entry point for Flask app
"""
import os
import sys

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Vercel environment flag before importing app
# This allows app.py to detect Vercel environment and use /tmp for database
os.environ['VERCEL'] = '1'

# Import app (database configuration happens in app.py based on VERCEL env var)
from app import app

# Vercel Python runtime expects the Flask app to be exported directly
# The app will be called as a WSGI application

