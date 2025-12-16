# Multi-User Journal App

A production-ready Flask application with secure multi-user authentication, per-user data isolation, and support for Turso database deployment on Vercel.

## Features

- ✅ **Secure Authentication**: werkzeug.security (PBKDF2) for password hashing
- ✅ **Flask-Login Support**: Automatic fallback to custom session management if Flask-Login is unavailable
- ✅ **Email Password Reset**: Time-limited tokens using itsdangerous.URLSafeTimedSerializer
- ✅ **Security Question Fallback**: Optional password reset via security question
- ✅ **Per-User Data Isolation**: All queries filter by user_id with @owner_required decorator
- ✅ **RESTful API**: Complete CRUD endpoints for journal entries
- ✅ **Rate Limiting Hints**: Failed login tracking (ready for Flask-Limiter integration)
- ✅ **CSRF Protection**: Flask-WTF integration with graceful fallback
- ✅ **Turso Database Support**: Automatic detection and handling of Turso/libSQL connections
- ✅ **Vercel Ready**: Optimized for serverless deployment

## Quick Start

### Local Development

1. **Install dependencies**:

   ```bash
   pip install Flask Flask-SQLAlchemy werkzeug itsdangerous
   # Optional but recommended:
   pip install Flask-Login Flask-Mail Flask-WTF Flask-Migrate
   ```

2. **Set environment variables** (optional for local dev):

   ```bash
   export SECRET_KEY="your-secret-key-here"
   export SECURITY_PASSWORD_SALT="your-salt-here"
   export DATABASE_URL="sqlite:///journal.db"  # or Turso URL
   ```

3. **Run the application**:

   ```bash
   flask --app multi_user_journal:create_app run --debug
   ```

4. **Create database tables**:

   ```bash
   flask --app multi_user_journal:create_app create-db
   ```

   Or use Flask-Migrate:

   ```bash
   flask --app multi_user_journal:create_app db init
   flask --app multi_user_journal:create_app db migrate -m "Initial migration"
   flask --app multi_user_journal:create_app db upgrade
   ```

### Testing

Run the test suite:

```bash
pytest -q
```

Tests use an in-memory SQLite database and mock email sending, so no real emails are sent.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `dev-secret-key-change-me` |
| `SECURITY_PASSWORD_SALT` | Salt for password reset tokens | `change-this-salt-in-production` |
| `DATABASE_URL` | Database connection string | `sqlite:///journal.db` |
| `MAIL_SERVER` | SMTP server hostname | `sandbox.smtp.mailtrap.io` |
| `MAIL_PORT` | SMTP server port | `2525` |
| `MAIL_USE_TLS` | Enable TLS for SMTP | `True` |
| `MAIL_USERNAME` | SMTP username | `mailtrap-user` |
| `MAIL_PASSWORD` | SMTP password | `mailtrap-pass` |
| `MAIL_DEFAULT_SENDER` | Default sender email | `journal@example.com` |
| `RESET_TOKEN_AGE` | Password reset token expiration (seconds) | `3600` (1 hour) |
| `VERCEL` | Vercel environment flag | Auto-detected |

### Turso Database Setup

1. **Create a Turso database**:

   ```bash
   turso db create journal-db
   ```

2. **Get the connection string**:

   ```bash
   turso db show journal-db --url
   ```

3. **Set the DATABASE_URL environment variable**:

   ```bash
   export DATABASE_URL="libsql://your-db-url"
   ```

   Or for Turso:

   ```bash
   export DATABASE_URL="turso://your-db-url"
   ```

The app automatically detects Turso URLs (`libsql://` or `turso://`) and handles them appropriately.

**Note**: For production Turso connections, you may need to install `libsql-client` and configure a custom SQLAlchemy engine. The current implementation converts Turso URLs to SQLite-compatible format for basic compatibility.

### Mail Configuration

#### Mailtrap (Testing)

For testing, use Mailtrap's sandbox SMTP:

```bash
export MAIL_SERVER="sandbox.smtp.mailtrap.io"
export MAIL_PORT=2525
export MAIL_USERNAME="your-mailtrap-username"
export MAIL_PASSWORD="your-mailtrap-password"
```

#### Production SMTP

For production, configure your SMTP provider:

**SendGrid**:
```bash
export MAIL_SERVER="smtp.sendgrid.net"
export MAIL_PORT=587
export MAIL_USERNAME="apikey"
export MAIL_PASSWORD="your-sendgrid-api-key"
```

**AWS SES**:
```bash
export MAIL_SERVER="email-smtp.us-east-1.amazonaws.com"
export MAIL_PORT=587
export MAIL_USERNAME="your-ses-username"
export MAIL_PASSWORD="your-ses-password"
```

**Gmail** (not recommended for production):
```bash
export MAIL_SERVER="smtp.gmail.com"
export MAIL_PORT=587
export MAIL_USERNAME="your-email@gmail.com"
export MAIL_PASSWORD="your-app-password"
```

## API Endpoints

### Authentication

- `POST /auth/signup` - Create new user account
- `POST /auth/login` - Authenticate and create session
- `POST /auth/logout` - Terminate session
- `POST /auth/request-reset` - Request password reset email
- `GET /auth/reset/<token>` - Validate reset token
- `POST /auth/reset/<token>` - Reset password with token
- `POST /auth/security-question` - Get security question for email
- `POST /auth/reset-with-security` - Reset password via security question

### Journal Entries

- `GET /journals` - List current user's entries
- `POST /journals` - Create new entry
- `GET /journals/<id>` - Get single entry (must be owner)
- `PUT /journals/<id>` - Update entry (must be owner)
- `DELETE /journals/<id>` - Delete entry (must be owner)

All journal endpoints require authentication and automatically filter by the current user's ID.

## Security Features

### Password Hashing

Uses `werkzeug.security.generate_password_hash()` which implements PBKDF2 with SHA-256. This is secure for production deployments.

### Password Reset Tokens

- Generated using `itsdangerous.URLSafeTimedSerializer`
- Time-limited (default: 1 hour, configurable via `RESET_TOKEN_AGE`)
- Uses separate salt (`SECURITY_PASSWORD_SALT`) from session secret
- Tokens are URL-safe and can be embedded in email links

### Data Isolation

- All journal entry queries filter by `user_id = current_user.id`
- `@owner_required` decorator ensures users can only access their own entries
- Returns 403 Forbidden if user tries to access another user's data

### Rate Limiting

The app includes a simple in-memory `FailedLoginTracker` for development. For production, integrate Flask-Limiter:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    # ... login logic
```

### CSRF Protection

Flask-WTF's CSRFProtect is integrated with graceful fallback. For form-based applications, CSRF tokens are automatically handled. For API-only applications, consider implementing token-based CSRF protection.

## Vercel Deployment

1. **Create `vercel.json`**:

   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "wsgi.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "wsgi.py"
       }
     ],
     "env": {
       "SECRET_KEY": "@secret-key",
       "SECURITY_PASSWORD_SALT": "@security-salt",
       "DATABASE_URL": "@database-url"
     }
   }
   ```

2. **Create `wsgi.py`**:

   ```python
   from multi_user_journal import create_app
   app = create_app()
   ```

3. **Set environment variables in Vercel dashboard**:
   - `SECRET_KEY`: Strong random secret
   - `SECURITY_PASSWORD_SALT`: Strong random salt
   - `DATABASE_URL`: Your Turso connection string
   - `MAIL_*`: Your SMTP configuration

4. **Deploy**:

   ```bash
   vercel deploy
   ```

## Database Migrations

### Using Flask-Migrate (Recommended)

```bash
# Initialize migrations
flask --app multi_user_journal:create_app db init

# Create migration
flask --app multi_user_journal:create_app db migrate -m "Description"

# Apply migration
flask --app multi_user_journal:create_app db upgrade
```

### Using SQLAlchemy create_all (Quick Testing)

```bash
flask --app multi_user_journal:create_app create-db
```

## Testing

The test suite includes:

- User isolation tests (users can only see their own entries)
- Ownership enforcement tests (403 errors for unauthorized access)
- Password reset flow tests (token generation, email sending, password change)
- Security question reset tests
- Rate limiting counter tests
- Token expiration tests

All tests use:
- In-memory SQLite database (fast, isolated)
- Mocked email sending (no real emails sent)
- Deterministic fixtures

Run tests:

```bash
pytest -q
```

## Dependencies

### Required

- Flask
- Flask-SQLAlchemy
- werkzeug (for password hashing)
- itsdangerous (for reset tokens)

### Optional (Recommended)

- Flask-Login (preferred, with automatic fallback)
- Flask-Mail (for email sending)
- Flask-WTF (for CSRF protection)
- Flask-Migrate (for database migrations)
- libsql-client (for Turso remote connections)

### Testing

- pytest

## License

This project is provided as-is. Modify as needed for your use case.

## Security Best Practices

1. **Always set strong SECRET_KEY and SECURITY_PASSWORD_SALT in production**
2. **Use HTTPS in production** (Vercel provides this automatically)
3. **Configure proper SMTP** for password reset emails
4. **Implement rate limiting** in production (Flask-Limiter recommended)
5. **Regularly update dependencies** for security patches
6. **Use environment variables** for all sensitive configuration
7. **Enable CSRF protection** for form-based endpoints
8. **Monitor failed login attempts** and implement account lockout if needed
9. **Use strong passwords** (enforce minimum length and complexity)
10. **Keep security question answers private** (they're hashed but still sensitive)





