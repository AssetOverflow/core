"""Single-admin authentication for CORE Workbench.

Passwords are never hardcoded. Configure with environment variables:

- CORE_WORKBENCH_ADMIN_EMAIL
- CORE_WORKBENCH_ADMIN_PASSWORD_HASH
- CORE_WORKBENCH_SESSION_SECRET

Generate a password hash with:

    python -m workbench.auth hash-password
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 390_000
_SESSION_TTL_SECONDS = 60 * 60 * 8


@dataclass(frozen=True, slots=True)
class AuthConfig:
    admin_email: str
    password_hash: str
    session_secret: str

    @property
    def configured(self) -> bool:
        return bool(self.admin_email and self.password_hash and self.session_secret)


def load_auth_config() -> AuthConfig:
    return AuthConfig(
        admin_email=os.environ.get("CORE_WORKBENCH_ADMIN_EMAIL", ""),
        password_hash=os.environ.get("CORE_WORKBENCH_ADMIN_PASSWORD_HASH", ""),
        session_secret=os.environ.get("CORE_WORKBENCH_SESSION_SECRET", ""),
    )


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("password must not be empty")
    resolved_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt,
        _PBKDF2_ITERATIONS,
    )
    return "$".join(
        (
            _PBKDF2_ALGORITHM,
            str(_PBKDF2_ITERATIONS),
            base64.urlsafe_b64encode(resolved_salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_s, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != _PBKDF2_ALGORITHM:
            return False
        iterations = int(iterations_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def _b64_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _load_b64_json(data: str) -> dict[str, Any]:
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid token payload")
    return payload


def issue_session_token(email: str, secret: str, *, now: int | None = None) -> str:
    if not secret:
        raise ValueError("session secret is not configured")
    issued = int(time.time() if now is None else now)
    payload = {"email": email, "iat": issued, "exp": issued + _SESSION_TTL_SECONDS}
    body = _b64_json(payload)
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{body}.{sig_b64}"


def verify_session_token(token: str, secret: str, *, now: int | None = None) -> dict[str, Any] | None:
    if not token or not secret or "." not in token:
        return None
    body, sig_b64 = token.split(".", 1)
    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    padded = sig_b64 + "=" * (-len(sig_b64) % 4)
    try:
        actual = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = _load_b64_json(body)
    except Exception:
        return None
    if not hmac.compare_digest(actual, expected):
        return None
    current = int(time.time() if now is None else now)
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < current:
        return None
    return payload


def authenticate(email: str, password: str, config: AuthConfig | None = None) -> str | None:
    cfg = config or load_auth_config()
    if not cfg.configured:
        return None
    if not hmac.compare_digest(email, cfg.admin_email):
        return None
    if not verify_password(password, cfg.password_hash):
        return None
    return issue_session_token(email, cfg.session_secret)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORE Workbench auth utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    hash_cmd = sub.add_parser("hash-password", help="hash a password for CORE_WORKBENCH_ADMIN_PASSWORD_HASH")
    hash_cmd.add_argument("password", nargs="?", help="password; omit to prompt")
    args = parser.parse_args(argv)
    if args.command == "hash-password":
        password = args.password
        if password is None:
            import getpass

            password = getpass.getpass("Workbench admin password: ")
        print(hash_password(password))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
