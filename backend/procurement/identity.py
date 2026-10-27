import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException

COOKIE = "harbor_session"
SEEDED_USERS = [
    ("aina", "Aina", "requester"),
    ("ben", "Ben", "approver"),
    ("chloe", "Chloe", "buyer"),
    ("dinesh", "Dinesh", "receiver"),
    ("eva", "Eva", "invoice_reviewer"),
]
DEMO_PASSWORD = "harbor-demo"


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 600_000
    ).hex()
    return f"{salt}${digest}"


def verify_password(password, encoded):
    salt, expected = encoded.split("$", 1)
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 600_000
    ).hex()
    return hmac.compare_digest(actual, expected)


def seed_users(db):
    with db.connect() as connection:
        for id, name, role in SEEDED_USERS:
            if not connection.execute(
                "SELECT id FROM users WHERE id=%s", (id,)
            ).fetchone():
                connection.execute(
                    "INSERT INTO users (id,name,role,password_hash) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    (id, name, role, password_hash(DEMO_PASSWORD)),
                )


def login(db, settings, username, password):
    with db.connect() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE id=%s AND active", (username,)
        ).fetchone()
        # Perform the same expensive verification for unknown users too.
        encoded = user["password_hash"] if user else "missing$" + "0" * 64
        valid = verify_password(password, encoded)
        if not user or not valid:
            raise HTTPException(401, "Invalid username or password")
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=settings.session_seconds)
        session_id, csrf = str(uuid4()), secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO sessions (id,user_id,expires_at) VALUES (%s,%s,%s)",
            (session_id, user["id"], expires),
        )
        token = jwt.encode(
            {
                "sub": user["id"],
                "jti": session_id,
                "csrf": csrf,
                "iat": now,
                "exp": expires,
                "iss": "harbor-local",
                "aud": "harbor-api",
            },
            settings.secret,
            algorithm="HS256",
        )
        return token, {"user": public_user(user), "csrf_token": csrf}


def public_user(user):
    return {key: user[key] for key in ("id", "name", "role")}


def authenticate(db, settings, token):
    try:
        claims = jwt.decode(
            token or "",
            settings.secret,
            algorithms=["HS256"],
            issuer="harbor-local",
            audience="harbor-api",
            options={"require": ["sub", "jti", "csrf", "iat", "exp"]},
        )
        with db.connect() as connection:
            row = connection.execute(
                "SELECT u.id,u.name,u.role FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.id=%s AND u.id=%s AND u.active AND NOT s.revoked AND s.expires_at > now()",
                (claims["jti"], claims["sub"]),
            ).fetchone()
        if not row:
            raise ValueError("No active session")
        return row, claims
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Authentication required") from None
