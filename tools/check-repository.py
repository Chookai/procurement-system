"""Focused tracked-file check before commits and in CI; no credential values logged.

This catches common token formats and our local credential values when available.
It is a guard, not a comprehensive secret scanner or security certification.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "OpenRouter token": re.compile(rb"sk-or-v1-[a-fA-F0-9]{32,}"),
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "JWT": re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    known = []
    environment = ROOT / "backend/.env"
    if environment.is_file():
        for line in environment.read_text().splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key in ("OPENROUTER_API_KEY", "SESSION_SIGNING_KEY"):
                value = value.strip().strip("\"'")
                if len(value) >= 16:
                    known.append(value.encode())
    signing_key = ROOT / "backend/.local/session.key"
    if signing_key.is_file():
        known.append(signing_key.read_bytes().strip())
    errors = []
    for path in filter(None, paths):
        parts = Path(path).parts
        if any(part in ("node_modules", ".venv", "__pycache__", ".local") for part in parts) or (Path(path).name.startswith(".env") and Path(path).name != ".env.example") or Path(path).suffix in (".pem", ".p12", ".pfx", ".key"):
            errors.append(f"{path}: local credential/dependency file is tracked")
        # Inspect the staged/committed content, not only a possibly different worktree copy.
        source = subprocess.check_output(["git", "show", ":" + path], cwd=ROOT)
        for name, pattern in PATTERNS.items():
            if pattern.search(source):
                errors.append(f"{path}: possible {name} found")
        if any(value and value in source for value in known):
            errors.append(f"{path}: local credential value found")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Tracked-file hygiene passed: {len(list(filter(None, paths)))} files; no matching credentials")


if __name__ == "__main__":
    main()
