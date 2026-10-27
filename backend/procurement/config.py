import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env", override=False)


def signing_key():
    configured = os.getenv("SESSION_SIGNING_KEY")
    if configured:
        if len(configured) < 32:
            raise ValueError("SESSION_SIGNING_KEY must contain at least 32 characters")
        return configured
    directory = BACKEND / ".local"
    directory.mkdir(exist_ok=True)
    path = directory / "session.key"
    try:
        with open(
            path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)
        ) as stream:
            stream.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    value = path.read_text().strip()
    if len(value) < 32:
        raise RuntimeError("Stored signing key is invalid")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://procurement:procurement-local-only@127.0.0.1:15432/procurement",
        )
    )
    schema: str = "procurement"
    secret: str = field(default_factory=signing_key)
    session_seconds: int = 3600
    secure_cookie: bool = False  # Loopback development; production requires HTTPS.
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    )
