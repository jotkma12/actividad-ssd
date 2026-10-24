"""Password, email, and bearer-token helpers for user accounts."""

from __future__ import annotations

import hashlib
import hmac
import secrets


INSTITUTIONAL_DOMAIN = "universidad.edu.co"
PASSWORD_MIN_LENGTH = 12
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def normalize_institutional_email(value: str) -> str:
    email = value.strip().lower()
    local_part, separator, domain = email.rpartition("@")
    if (
        email.count("@") != 1
        or not separator
        or not local_part
        or any(character.isspace() for character in email)
        or domain != INSTITUTIONAL_DOMAIN
    ):
        raise ValueError(f"El correo debe pertenecer a @{INSTITUTIONAL_DOMAIN}")
    return email


def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres"
        )


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected_digest = bytes.fromhex(digest_hex)
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError, MemoryError):
        return False
    return hmac.compare_digest(actual_digest, expected_digest)


def create_bearer_token() -> str:
    return secrets.token_urlsafe(32)


def hash_bearer_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
